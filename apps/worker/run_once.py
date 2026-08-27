"""apps/worker — 最小采集流水线（Phase 2 第一刀）。

职责（契约对齐 packages/agent_contracts/TASK-101_candidate_extraction.yaml 的
保守子集；本实现为规则式抽取，LLM 抽取留待 model_client 接入后替换）：

1. 扫描 data/raw/<SRC-xxxx>/*.json（Connector 写出的 RawDocument 快照）；
2. 问题列表类源（OPG / formal-conjectures / erdosproblems）→ 生成 candidate 卡：
   - 严格遵守 problem_card Schema v1.0.0（过校验才落盘）；
   - lifecycle=candidate、human_verified=false、publishable=false；
   - 评分带一律 insufficient_evidence（无证据不评分——AGENTS.md 红线 9）；
   - 领域映射不上的条目直接跳过并记录（不猜测领域）；
3. 文献类源（arXiv/OpenAlex/Crossref/zbMATH）→ 只更新 data/raw/_catalog.json
   索引（供 P4 状态核验检索用），不生成卡；
4. 全程零发布动作。

用法（项目根）：
    python apps/worker/run_once.py [--candidates-only]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "domain" / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_gold_set import build_registry  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402

RAW = ROOT / "data" / "raw"
CAND = ROOT / "data" / "candidates"

PROBLEM_SOURCES = {"SRC-0008", "SRC-0009", "SRC-0010"}
LITERATURE_SOURCES = {"SRC-0002", "SRC-0011", "SRC-0020", "SRC-0021"}

# OPG 分类 → 本仓库 taxonomy primary_domain（映射不上的跳过，不猜）
OPG_DOMAIN = {
    "number theory": "number-theory",
    "analysis": "analysis",
    "algebra": "algebra",
    "algebraic geometry": "algebraic-geometry",
    "combinatorics": "combinatorics-and-graph-theory",
    "graph theory": "combinatorics-and-graph-theory",
    "geometry": "geometry",
    "topology": "topology",
    "probability": "analysis",
}

NOW = "2026-08-28T12:00:00Z"
NEXT_CAND = 800001  # 约定：8xxxxx=流水线候选，9xxxxx=测试夹具


def slugify(text: str) -> str:
    keep = [c for c in text.lower() if c.isalnum() or c == " "]
    return "-".join("".join(keep).split())[:48] or "unnamed"


def make_candidate(doc: dict, domain: str) -> dict:
    title = (doc.get("title") or "").strip()[:120] or "未命名候选"
    url = doc.get("url") or ""
    text = (doc.get("text") or "").strip()
    sid = doc["source_id"]
    return {
        "problem_id": None,  # 分配时填
        "schema_version": "1.0.0",
        "identity": {"title": title, "aliases": [], "slug": slugify(title)},
        "statements": {
            "original": {
                "text": text[:2000] or title,
                "language": "en",
                "source_id": sid,
                "source_location": url or (doc.get("meta") or {}).get("source_location"),
                "immutable_content_hash": None,
            },
            "normalized": {
                "text": (text[:2000] or title),  # 规则式直通：不擅自翻译/改写
                "assumptions": [],
                "quantified_objects": [],
                "normalization_notes": [
                    "规则式直通（extraction-rules-v0.1）：未经 TASK-201 LLM 规范化，量词与假设未显式化",
                ],
                "semantic_risks": ["候选阶段：陈述可能不完整或与来源页面排版混杂"],
            },
            "reader_summary": {
                "one_sentence": f"【自动候选·待核验】{title}"
            },
        },
        "classification": {
            "primary_domain": domain,
            "secondary_domains": [],
            "topics": [],
            "problem_types": [],
            "expected_output_types": [],
            "mathematical_objects": [],
        },
        "provenance": {
            "original_proposer": [],
            "source_urls": [url] if url else [],
            "discovery_method": "pipeline_extraction",
            "discovered_at": "2026-08-28",
        },
        "open_status": {
            "status": "status_uncertain",
            "confidence_level": "none",
            "last_checked_at": "2026-08-28",
            "supporting_evidence": [
                {
                    "evidence_id": "EV-PENDING-1",
                    "kind": "document_link",
                    "description": f"来源页面存在（{sid}）；内容未人工核验",
                    "url": url or None,
                    "source_id": sid,
                    "tier": "A" if sid in ("SRC-0008", "SRC-0009") else "B",
                    "verification_status": "verified",
                    "retrieved_at": doc.get("fetched_at", "2026-08-28"),
                    "notes": "仅证明链接存在；问题陈述与开放状态均未核验",
                }
            ],
            "contradicting_evidence": [],
            "resolved_scope": None,
            "human_verified": False,
        },
        "known_results": {
            "special_cases": [],
            "best_known_bounds": [],
            "known_equivalences": [],
            "attempted_methods": [],
            "blocking_obstacles": [],
        },
        "relationships": {
            "equivalent_to": [],
            "generalizes": [],
            "special_case_of": [],
            "implies": [],
            "implied_by": [],
            "related_to": [],
        },
        "importance_assessment": {
            "evidence": [],
            "feature_values": {},
            "score_band": "insufficient_evidence",
            "uncertainty": "自动候选：未评估",
            "rubric_version": "importance-rubric-v0.1",
        },
        "ai_affordance_assessment": {
            "evidence_for": [],
            "evidence_against": [],
            "unknowns": ["自动候选：未评估"],
            "feature_values": {},
            "score_band": "insufficient_evidence",
            "uncertainty": "自动候选：未评估",
            "rubric_version": "ai-affordance-rubric-v0.1",
        },
        "publication": {
            "lifecycle_state": "candidate",
            "publishable": False,
            "visibility": "internal",
            "publish_blockers": [
                "自动候选：P1–P7 全流程未执行",
                "发布门禁要求人工确认（§10.2 / ADR-012）",
            ],
        },
        "audit": {
            "created_by": "agent:pipeline-rule-based-v0",
            "created_at": NOW,
            "updated_at": NOW,
            "current_version": 1,
            "model_runs": [
                {
                    "task_name": "TASK-101_candidate_extraction",
                    "prompt_version": "extraction-rules-v0.1",
                    "model": "rule-based (no LLM)",
                    "executed_at": NOW,
                    "notes": "规则式抽取：仅从已登记来源快照生成候选，未做语义加工",
                }
            ],
            "human_reviews": [],
        },
    }


def domain_for(doc: dict) -> str | None:
    meta = doc.get("meta") or {}
    if doc["source_id"] == "SRC-0009":
        cats = [str(c).lower().strip() for c in meta.get("categories", [])]
        for c in cats:
            if c in OPG_DOMAIN:
                return OPG_DOMAIN[c]
        return None  # 映射不上→跳过，不猜
    if doc["source_id"] == "SRC-0008":
        return "algebra" if "algebra" in (doc.get("title") or "").lower() else None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates-only", action="store_true")
    args = ap.parse_args()

    registry, _ = build_registry()
    validator = Draft202012Validator(
        json.loads((ROOT / "schemas" / "problem_card" / "schema.json").read_text(encoding="utf-8")),
        registry=registry,
    )

    CAND.mkdir(parents=True, exist_ok=True)
    report = {"candidates_written": 0, "skipped": [], "catalogued": 0, "errors": []}
    existing = {p.stem for p in CAND.glob("OP-8*.json")}
    next_id = max([int(s[3:]) for s in existing], default=NEXT_CAND - 1) + 1

    for src_dir in sorted(RAW.glob("SRC-*")):
        if not src_dir.is_dir():
            continue
        sid = src_dir.name
        for doc_path in sorted(src_dir.glob("*.json")):
            try:
                doc = json.loads(doc_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                report["errors"].append(f"{doc_path}: {e}")
                continue

            if sid in PROBLEM_SOURCES and not args.candidates_only:
                domain = domain_for(doc)
                if domain is None:
                    report["skipped"].append(f"{doc_path.name}: 领域未映射（不猜测，跳过）")
                    continue
                card = make_candidate(doc, domain)
                card["problem_id"] = f"OP-{next_id:06d}"
                card["open_status"]["supporting_evidence"][0]["evidence_id"] = (
                    f"EV-{next_id:06d}-1"
                )
                errs = sorted(validator.iter_errors(card), key=lambda e: e.path)
                if errs:
                    report["skipped"].append(
                        f"{doc_path.name}: Schema 拒绝 ({errs[0].message[:90]})"
                    )
                    continue
                out = CAND / f"{card['problem_id']}.json"
                out.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                next_id += 1
                report["candidates_written"] += 1
            elif sid in LITERATURE_SOURCES:
                report["catalogued"] += 1  # 索引留待 P4；不生成卡

    # 文献索引
    if not args.candidates_only:
        catalog = []
        for sid in LITERATURE_SOURCES:
            d = RAW / sid
            if d.is_dir():
                for p in sorted(d.glob("*.json")):
                    try:
                        doc = json.loads(p.read_text(encoding="utf-8"))
                        catalog.append({
                            "source_id": sid,
                            "external_id": doc.get("external_id"),
                            "title": (doc.get("title") or "")[:160],
                            "url": doc.get("url"),
                            "fetched_at": doc.get("fetched_at"),
                            "cited_by": (doc.get("meta") or {}).get("cited_by_count"),
                        })
                    except json.JSONDecodeError:
                        pass
        (RAW / "_catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
