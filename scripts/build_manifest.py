"""构建 data/gold_set/MANIFEST.json（设计规范 §21.3 金标准类别标注）。

类别判定规则（可复现、非人工）：
- resolved_misjudge_trap      ：open_status=resolved（易被大众列表误标为开放）
- unverified_claim_stress     ：存在 unverified/disputed 声称证据（状态必须停在核验档位）
- equivalence_network         ：有 equivalent_to/known_equivalences 或被 FIX-003 指向
- high_similarity_distinct    ：设计上成对出现但语义不同的几何/组合近邻对
- special_case_only           ：best_known_bounds/special_cases 丰富的界改进型问题
- confirmed_open_reference    ：旗舰开放问题参照

用法：python scripts/build_manifest.py
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold_set"

# 高相似但不同的设计配对（§21.3 第五类：去重器必须判 related_but_distinct）
HIGH_SIMILAR_PAIRS = {
    "OP-000013": "π 正规性 vs π+e 无理性（同为常数超越/正规性族，命题不同）",
    "OP-000012": "π+e 无理性 vs π 正规性（同上）",
    "OP-000023": "五维接吻数 vs 开普勒猜想（同为球堆积族，维度不同）",
    "OP-000030": "开普勒猜想 vs 五维接吻数（同上；本卡另属 resolved 类）",
    "OP-000009": "Brocard 问题 vs Erdős–Straus（同为丢番图方程小解搜索族）",
    "OP-000006": "Erdős–Straus vs Brocard 问题（同上）",
    "OP-000018": "平面色数 vs Lonely Runner（同为距离/速度染色离散几何族）",
    "OP-000020": "Lonely Runner vs 平面色数（同上）",
}

# 等价网络节点（等价关系测试锚点）
EQUIVALENCE_NODES = {
    "OP-000001": "黎曼假设（Robin 判据等价，FIX-003 指向）",
    "OP-000012": "π+e 无理性（Schanuel 蕴含族）",
    "OP-000014": "Schanuel 猜想（蕴含 π+e / Lindemann–Weierstrass 推广族）",
}

# 界改进型（special_case_only 类）
BOUND_PROBLEMS = {
    "OP-000006", "OP-000008", "OP-000009", "OP-000010", "OP-000016",
    "OP-000018", "OP-000020", "OP-000023", "OP-000024",
}


def categories_for(card: dict) -> list[str]:
    pid = card["problem_id"]
    cats: list[str] = []
    status = card["open_status"]["status"]
    if status == "resolved":
        cats.append("resolved_misjudge_trap")
    claims = card["open_status"].get("contradicting_evidence", []) + card["open_status"].get(
        "supporting_evidence", []
    )
    if any(e.get("verification_status") in ("unverified", "disputed") for e in claims):
        cats.append("unverified_claim_stress")
    if pid in EQUIVALENCE_NODES:
        cats.append("equivalence_network")
    if pid in HIGH_SIMILAR_PAIRS and "resolved_misjudge_trap" not in cats:
        cats.append("high_similarity_distinct")
    if pid in BOUND_PROBLEMS:
        cats.append("special_case_only")
    if not cats:
        cats.append("confirmed_open_reference")
    return cats


def main() -> int:
    entries = []
    for path in sorted(GOLD.glob("OP-*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        pid = card["problem_id"]
        cats = categories_for(card)
        note = HIGH_SIMILAR_PAIRS.get(pid) or EQUIVALENCE_NODES.get(pid)
        entries.append(
            {
                "problem_id": pid,
                "title": card["identity"]["title"],
                "primary_domain": card["classification"]["primary_domain"],
                "open_status": card["open_status"]["status"],
                "lifecycle_state": card["publication"]["lifecycle_state"],
                "gold_categories": cats,
                **({"category_note": note} if note else {}),
            }
        )

    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": "2026-08-28",
        "total_cards": len(entries),
        "discipline": {
            "lifecycle_state": "全部为 scored（Phase 0 纪律，禁止发布）",
            "human_verified": "全部 false",
            "publishable": "全部 false",
        },
        "category_counts": {
            c: sum(1 for e in entries if c in e["gold_categories"])
            for c in (
                "confirmed_open_reference",
                "resolved_misjudge_trap",
                "special_case_only",
                "equivalence_network",
                "high_similarity_distinct",
                "unverified_claim_stress",
            )
        },
        "fixtures": {
            "FIX-001": "data/fixtures/FIX-001_malformed_goldbach.json（Schema 必须拒绝）",
            "FIX-002": "data/fixtures/FIX-002_prompt_injection_sample.json（注入抵抗样本）",
            "FIX-003": "data/fixtures/FIX-003_robin_equivalence_dedup.json（等价去重样本，指向 OP-000001）",
        },
        "cards": entries,
    }

    out = GOLD / "MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST.json 写入 {len(entries)} 张卡；类别分布 {manifest['category_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
