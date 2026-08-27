"""夹具测试：FIX-001 必须被 Schema 拒绝；FIX-003 必须通过 Schema 且保留为独立实体。"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_gold_set import build_registry  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402

FIXTURES = ROOT / "data" / "fixtures"


def _validator():
    registry, _ = build_registry()
    return Draft202012Validator(
        json.loads((ROOT / "schemas" / "problem_card" / "schema.json").read_text(encoding="utf-8")),
        registry=registry,
    )


class TestMalformedFixture:
    def test_fix001_fails_schema(self):
        data = json.loads((FIXTURES / "FIX-001_malformed_goldbach.json").read_text(encoding="utf-8"))
        assert data["expected_validation"] == "fail"
        errors = list(_validator().iter_errors(data["card"]))
        assert errors, "FIX-001 应触发 Schema 校验失败"
        # 主要失败点：缺 source_id
        assert any("source_id" in str(e.path) or "required" in e.message.lower() for e in errors)

    def test_fix001_never_enters_gold_set(self):
        """残缺卡不得出现在 gold_set 目录（校验器只认 OP-xxxxxx.json）。"""
        bad = list((ROOT / "data" / "gold_set").glob("OP-9000*.json"))
        assert not bad


class TestDedupFixture:
    def test_fix003_valid_but_stays_candidate(self):
        data = json.loads((FIXTURES / "FIX-003_robin_equivalence_dedup.json").read_text(encoding="utf-8"))
        errors = list(_validator().iter_errors(data["card"]))
        assert not errors, f"FIX-003 应通过 Schema: {[e.message for e in errors[:3]]}"
        assert data["card"]["publication"]["lifecycle_state"] == "candidate"
        assert data["card"]["publication"]["publishable"] is False

    def test_fix003_links_not_merges(self):
        """等价关系必须以 equivalent_to 出现，且 OP-000001 本体未被改写。"""
        data = json.loads((FIXTURES / "FIX-003_robin_equivalence_dedup.json").read_text(encoding="utf-8"))
        rel = data["card"]["relationships"]["equivalent_to"]
        assert any(r["target"] == "OP-000001" for r in rel)
        rh = json.loads((ROOT / "data" / "gold_set" / "OP-000001.json").read_text(encoding="utf-8"))
        # RH 卡不得因为等价卡的存在而改变自身实体性（仍是独立 OP-000001）
        assert rh["problem_id"] == "OP-000001"
        assert "Robin" not in json.dumps(rh["identity"]["title"])


class TestInjectionFixture:
    def test_fix002_payloads_present(self):
        data = json.loads((FIXTURES / "FIX-002_prompt_injection_sample.json").read_text(encoding="utf-8"))
        text = data["document_text"]
        for marker in ("Ignore all previous instructions", "SYSTEM OVERRIDE", "publishable=true"):
            assert marker in text
        assert data["tier"] == "D"
