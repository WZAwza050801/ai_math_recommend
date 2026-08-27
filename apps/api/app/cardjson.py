"""问题卡 JSON 的校验与操作工具。

- Schema 校验：复用 schemas/*/schema.json（draft 2020-12，跨文件 $ref 注册表），
  构造方式与 scripts/validate_gold_set.py 的 build_registry 一致。
- 投影列提取：把卡 JSON 投影为 cards 表索引列。
- 版本快照：所有内容修改统一经 write_snapshot 落 card_versions（ADR-004）。
- 排序取值：复用 packages/ranking 的 user_score（ranking-weights-v0.1）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from sqlalchemy.orm import Session

from ._bootstrap import REPO_ROOT  # 必须先于 ai_math_* 导入，负责注入 sys.path

from ai_math_ranking import user_score as ranking_user_score  # noqa: E402

from .models import Card, CardVersion

SCHEMA_DIR = REPO_ROOT / "schemas"
GOLD_SET_DIR = REPO_ROOT / "data" / "gold_set"
SOURCE_REGISTRY_DIR = REPO_ROOT / "data" / "source_registry"
WEB_INDEX_PATH = REPO_ROOT / "apps" / "web" / "index.html"
PROBLEM_CARD_SCHEMA_PATH = SCHEMA_DIR / "problem_card" / "schema.json"

# 抽卡个性化默认值（端点契约：P=50, C=75；I/A 从卡内 feature 均值或缺省 50）
DEFAULT_PROFILE_MATCH = 50.0
DEFAULT_EVIDENCE_CONFIDENCE = 75.0
DEFAULT_FEATURE_VALUE = 50


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def _problem_card_validator() -> Draft202012Validator:
    """构造带跨文件 $ref 注册表的 problem_card 校验器（进程内缓存一次）。"""
    registry: Registry = Registry()
    for f in sorted(SCHEMA_DIR.glob("*/schema.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(doc)
        registry = registry.with_resource(
            doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012)
        )
    schema = json.loads(PROBLEM_CARD_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry)


def schema_errors(card: dict[str, Any]) -> list[str]:
    """返回 Schema 校验错误明细（人类可读路径+消息）；空列表即通过。"""
    validator = _problem_card_validator()
    return [
        f"/{'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in sorted(validator.iter_errors(card), key=lambda e: list(e.absolute_path))
    ]


def dump_card(card: dict[str, Any]) -> str:
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def load_card(row: Card) -> dict[str, Any]:
    return json.loads(row.card_json)


def index_fields(card: dict[str, Any]) -> dict[str, Any]:
    """从卡 JSON 提取 cards 表投影列。"""
    identity = card.get("identity") or {}
    classification = card.get("classification") or {}
    open_status = card.get("open_status") or {}
    publication = card.get("publication") or {}
    importance = card.get("importance_assessment") or {}
    affordance = card.get("ai_affordance_assessment") or {}
    return {
        "title": str(identity.get("title") or ""),
        "primary_domain": str(classification.get("primary_domain") or ""),
        "open_status": str(open_status.get("status") or ""),
        "lifecycle_state": str(publication.get("lifecycle_state") or "candidate"),
        "publishable": bool(publication.get("publishable") or False),
        "importance_band": importance.get("score_band"),
        "affordance_band": affordance.get("score_band"),
    }


def apply_index_fields(row: Card, card: dict[str, Any]) -> None:
    for key, value in index_fields(card).items():
        setattr(row, key, value)


def feature_mean(card: dict[str, Any], section: str, default: int = DEFAULT_FEATURE_VALUE) -> int:
    """取评估段 feature_values 的均值并取整；缺失或缺省时回退 default。"""
    node = card.get(section)
    if not isinstance(node, dict):
        return default
    values = node.get("feature_values")
    if isinstance(values, dict):
        nums = [v for v in values.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            return int(round(sum(nums) / len(nums)))
    return default


def user_score_for_card(card: dict[str, Any]) -> float:
    """S_user（ranking-weights-v0.1）：I/A 取卡内 feature 均值，P/C 用契约默认值。"""
    i = feature_mean(card, "importance_assessment")
    a = feature_mean(card, "ai_affordance_assessment")
    return ranking_user_score(i, a, DEFAULT_PROFILE_MATCH, DEFAULT_EVIDENCE_CONFIDENCE)


def one_sentence(card: dict[str, Any]) -> str:
    statements = card.get("statements") or {}
    reader = statements.get("reader_summary") or {}
    return str(reader.get("one_sentence") or "")


def sync_audit_version(card: dict[str, Any], version: int) -> None:
    """保持卡内 audit.current_version / updated_at 与版本轨迹一致。"""
    audit = card.get("audit")
    if not isinstance(audit, dict):
        audit = {}
        card["audit"] = audit
    audit["current_version"] = version
    audit["updated_at"] = utcnow_iso()


def write_snapshot(
    db: Session,
    row: Card,
    card: dict[str, Any],
    *,
    version: int,
    changed_by: str,
    reason: str,
) -> int:
    """统一落库：同步投影列、写卡 JSON、追加不可变版本快照并提交。

    这是本应用所有内容变更的唯一写出口，保证"每次修改必有一行快照"（ADR-004）。
    """
    sync_audit_version(card, version)
    apply_index_fields(row, card)
    row.version = version
    row.card_json = dump_card(card)
    row.updated_at = utcnow()
    db.add(
        CardVersion(
            problem_id=row.problem_id,
            version=version,
            snapshot_json=row.card_json,
            changed_by=changed_by[:128],
            reason=reason[:256],
        )
    )
    db.commit()
    db.refresh(row)
    return version
