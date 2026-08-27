#!/usr/bin/env python3
"""金标准问题卡校验器（Phase 0）。

用法:
    python scripts/validate_gold_set.py                 # 校验 data/gold_set/OP-*.json 全部
    python scripts/validate_gold_set.py <card.json> ... # 校验指定卡片

检查项:
  1. JSON Schema 校验（problem_card v1.0.0，跨文件 $ref 注册表解析）
  2. classification.primary_domain 必须在 data/taxonomies/domains.json 登记
  3. statements.original.source_id 与所有 evidence.source_id 必须在 Source Registry 登记
  4. evidence_id 卡内唯一
  5. 金标准纪律: lifecycle_state 必须为 scored；human_verified=false 时 publishable 必须为 false
  6. 状态纪律: 存在 unverified_claim 证据时，status 不得为 resolved / confirmed_open 由该声称单独支撑
     (弱检查: resolved 状态必须伴随 verified 证据)

退出码: 0=全部通过, 1=存在错误。
"""
from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas"
GOLD_DIR = ROOT / "data" / "gold_set"
TAXONOMY = ROOT / "data" / "taxonomies" / "domains.json"
REGISTRY_DIR = ROOT / "data" / "source_registry"

PATTERN_CARD = "https://ai-math-recommend.dev/schemas/problem_card/v1.0.0/schema.json"


def build_registry() -> tuple[Registry, dict]:
    registry: Registry = Registry()
    docs: dict = {}
    for f in sorted(SCHEMA_DIR.glob("*/schema.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(doc)
        registry = registry.with_resource(doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012))
        docs[f.parent.name] = doc
    return registry, docs


def load_registry_ids() -> set[str]:
    ids: set[str] = set()
    for f in REGISTRY_DIR.glob("SRC-*.json"):
        try:
            ids.append if False else ids.add(json.loads(f.read_text(encoding="utf-8"))["source_id"])
        except Exception:
            continue
    return ids


def load_domain_ids() -> set[str]:
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    return {d["id"] for d in tax["primary_domains"]}


def iter_evidence(node):
    """递归找出卡片内所有 evidence 对象（含嵌套于 known_results / assessments 等）。"""
    if isinstance(node, dict):
        if "evidence_id" in node and "kind" in node and "verification_status" in node:
            yield node
        for v in node.values():
            yield from iter_evidence(v)
    elif isinstance(node, list):
        for item in node:
            yield from iter_evidence(item)


def check_card(path: pathlib.Path, validator: Draft202012Validator, domain_ids: set[str], src_ids: set[str]) -> list[str]:
    errors: list[str] = []
    card = json.loads(path.read_text(encoding="utf-8"))

    for e in sorted(validator.iter_errors(card), key=lambda e: list(e.path)):
        errors.append(f"schema: /{'/'.join(map(str, e.path))}: {e.message[:200]}")

    pid = card.get("problem_id", path.stem)

    # taxonomy 交叉检查
    pd = card.get("classification", {}).get("primary_domain")
    if pd and pd not in domain_ids:
        errors.append(f"taxonomy: primary_domain '{pd}' 未在 domains.json 登记")

    # source registry 交叉检查
    orig_sid = card.get("statements", {}).get("original", {}).get("source_id")
    if orig_sid and orig_sid not in src_ids:
        errors.append(f"registry: statements.original.source_id '{orig_sid}' 未登记")
    for ev in iter_evidence(card):
        sid = ev.get("source_id")
        if sid and sid not in src_ids:
            errors.append(f"registry: {ev.get('evidence_id')} source_id '{sid}' 未登记")

    # evidence_id 唯一性
    ev_ids = [ev.get("evidence_id") for ev in iter_evidence(card)]
    dup = {i for i in ev_ids if ev_ids.count(i) > 1}
    if dup:
        errors.append(f"evidence: 重复 evidence_id: {sorted(dup)}")
    bad_ids = [i for i in ev_ids if not isinstance(i, str)]
    if bad_ids:
        errors.append(f"evidence: 非法 evidence_id: {bad_ids}")

    # 金标准纪律
    pub = card.get("publication", {})
    if pub.get("lifecycle_state") != "scored":
        errors.append(f"lifecycle: 金标准卡必须为 scored，实际 '{pub.get('lifecycle_state')}'")
    os_ = card.get("open_status", {})
    if os_.get("human_verified") is False and pub.get("publishable") is True:
        errors.append("gate: human_verified=false 但 publishable=true（违反发布门禁）")

    # 状态纪律
    if os_.get("status") == "resolved":
        has_verified = any(
            ev.get("verification_status") == "verified"
            for ev in iter_evidence(os_.get("supporting_evidence", []))
        )
        if not has_verified:
            errors.append("status: resolved 状态缺少 verified 证据")

    return errors


def main(argv: list[str]) -> int:
    registry, _ = build_registry()
    validator = Draft202012Validator(
        json.loads((SCHEMA_DIR / "problem_card" / "schema.json").read_text(encoding="utf-8")),
        registry=registry,
    )
    domain_ids = load_domain_ids()
    src_ids = load_registry_ids()

    if argv:
        targets = [pathlib.Path(a) for a in argv]
    else:
        targets = sorted(GOLD_DIR.glob("OP-*.json"))

    if not targets:
        print("没有待校验卡片")
        return 1

    failed = 0
    print(f"{'卡片':<16} 结果")
    print("-" * 72)
    for path in targets:
        try:
            errors = check_card(path, validator, domain_ids, src_ids)
        except json.JSONDecodeError as e:
            errors = [f"json: {e}"]
        if errors:
            failed += 1
            print(f"{path.stem:<16} FAIL ({len(errors)} 项)")
            for msg in errors[:12]:
                print(f"    - {msg}")
        else:
            print(f"{path.stem:<16} PASS")
    print("-" * 72)
    print(f"合计 {len(targets)} 张，通过 {len(targets) - failed}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
