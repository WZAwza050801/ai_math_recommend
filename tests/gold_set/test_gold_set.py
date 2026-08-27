"""金标准集整体校验测试：Schema + taxonomy + registry + 状态纪律 + MANIFEST 一致性。"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_gold_set import (  # noqa: E402
    build_registry,
    check_card,
    load_domain_ids,
    load_registry_ids,
)

GOLD = ROOT / "data" / "gold_set"


def _validate_all():
    registry, _ = build_registry()
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(
        json.loads((ROOT / "schemas" / "problem_card" / "schema.json").read_text(encoding="utf-8")),
        registry=registry,
    )
    domain_ids = load_domain_ids()
    src_ids = load_registry_ids()
    results = {}
    for path in sorted(GOLD.glob("OP-*.json")):
        results[path.stem] = check_card(path, validator, domain_ids, src_ids)
    return results


class TestSchemaCompliance:
    def test_all_cards_pass(self):
        results = _validate_all()
        failures = {k: v for k, v in results.items() if v}
        assert not failures, f"未通过卡片: {failies_key_detail(failures)}"

    def test_card_count(self):
        cards = sorted(GOLD.glob("OP-*.json"))
        assert len(cards) >= 30, f"金标准集应 ≥30 张，实际 {len(cards)}"

    def test_at_least_five_domains(self):
        domains = set()
        for path in GOLD.glob("OP-*.json"):
            card = json.loads(path.read_text(encoding="utf-8"))
            domains.add(card["classification"]["primary_domain"])
        assert len(domains) >= 5, f"应覆盖 ≥5 个数学大类，实际 {sorted(domains)}"


class TestStatusDiscipline:
    def test_resolved_cards_have_verified_evidence(self):
        for path in sorted(GOLD.glob("OP-*.json")):
            card = json.loads(path.read_text(encoding="utf-8"))
            if card["open_status"]["status"] == "resolved":
                statuses = [
                    ev.get("verification_status")
                    for ev in card["open_status"]["supporting_evidence"]
                ]
                assert "verified" in statuses, f"{path.stem} resolved 但无 verified 证据"

    def test_unverified_claims_never_decide_status(self):
        """存在 unverified/disputed 声称的卡，状态必须停在接受核验的档位。"""
        for path in sorted(GOLD.glob("OP-*.json")):
            card = json.loads(path.read_text(encoding="utf-8"))
            claims = card["open_status"].get("contradicting_evidence", [])
            has_unverified = any(
                ev.get("verification_status") in ("unverified", "disputed") for ev in claims
            )
            if has_unverified:
                assert card["open_status"]["status"] != "resolved", (
                    f"{path.stem}: 存在未核验声称但状态为 resolved，违反 §11.2"
                )

    def test_no_card_claiming_human_verified(self):
        for path in sorted(GOLD.glob("OP-*.json")):
            card = json.loads(path.read_text(encoding="utf-8"))
            assert card["open_status"]["human_verified"] is False, (
                f"{path.stem}: Phase 0 卡不得标记 human_verified=true"
            )


class TestManifest:
    def test_manifest_lists_all_cards(self):
        manifest_path = GOLD / "MANIFEST.json"
        assert manifest_path.exists(), "缺少 data/gold_set/MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cards = {p.stem for p in GOLD.glob("OP-*.json")}
        listed = {entry["problem_id"] for entry in manifest["cards"]}
        assert listed == cards, f"MANIFEST 与卡片文件不一致: {sorted(cards ^ listed)}"

    def test_gold_categories_covered(self):
        manifest = json.loads((GOLD / "MANIFEST.json").read_text(encoding="utf-8"))
        categories = {c for entry in manifest["cards"] for c in entry.get("gold_categories", [])}
        required = {
            "confirmed_open_reference",
            "resolved_misjudge_trap",
            "special_case_only",
            "equivalence_network",
            "high_similarity_distinct",
            "unverified_claim_stress",
        }
        missing = required - categories
        assert not missing, f"金标准类别缺失: {missing}"


def failies_key_detail(failures: dict) -> str:
    return "; ".join(f"{k}: {v[:2]}" for k, v in failures.items())
