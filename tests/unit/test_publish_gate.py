"""发布门禁单元测试（设计规范 §10.2 八项条件 + 严禁自动发布）。"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from ai_math_domain import evaluate_publish_gate

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
EXEMPLAR = ROOT / "data" / "gold_set" / "OP-000001.json"


@pytest.fixture()
def card() -> dict:
    """以真实金标准卡（人工核验通过后的模拟态）为基底。

    OP-000001 当前 human_verified=false 且无 human_reviews（Phase 0 纪律），
    测试通过注入人工审核记录模拟 P7 完成后的状态。
    """
    base = json.loads(EXEMPLAR.read_text(encoding="utf-8"))
    base["audit"]["human_reviews"] = [
        {
            "reviewer": "human:reviewer-001",
            "decision": "approved",
            "reviewed_at": "2026-08-28T10:00:00Z",
            "notes": "测试注入：模拟 P7 完成",
        }
    ]
    return base


def blockers_of(card: dict) -> list[str]:
    ok, blockers = evaluate_publish_gate(card)
    assert ok == (not blockers)
    return blockers


class TestGatePass:
    def test_reviewed_card_passes(self, card):
        assert blockers_of(card) == []


class TestGateConditions:
    def test_gate1_missing_original_statement(self, card):
        card["statements"]["original"]["text"] = ""
        card["statements"]["original"]["latex"] = None
        assert any(b.startswith("gate-1") for b in blockers_of(card))

    def test_gate1_missing_source(self, card):
        card["statements"]["original"]["source_id"] = ""
        assert any(b.startswith("gate-1") for b in blockers_of(card))

    def test_gate2_missing_normalized(self, card):
        card["statements"]["normalized"]["text"] = ""
        assert any(b.startswith("gate-2") for b in blockers_of(card))

    def test_gate3_no_dedup_run(self, card):
        card["audit"]["model_runs"] = [
            r for r in card["audit"]["model_runs"]
            if r["task_name"] != "TASK-301_dedup_and_relation"
        ]
        assert any(b.startswith("gate-3") for b in blockers_of(card))

    def test_gate4_resolved_status(self, card):
        card["open_status"]["status"] = "resolved"
        assert any(b.startswith("gate-4") for b in blockers_of(card))

    def test_gate5_no_importance_evidence(self, card):
        card["importance_assessment"]["evidence"] = []
        assert any(b.startswith("gate-5") for b in blockers_of(card))

    def test_gate6_missing_rubric(self, card):
        card["ai_affordance_assessment"]["rubric_version"] = ""
        assert any(b.startswith("gate-6") for b in blockers_of(card))

    def test_gate7_unreviewed_must_be_marked(self, card):
        raw = json.loads(EXEMPLAR.read_text(encoding="utf-8"))
        # 原始金标准卡：human_reviews=[]，但 publish_blockers 非空 → gate-7 通过但整体仍不可发布
        assert not any(b.startswith("gate-7") for b in blockers_of(raw))
        raw["publication"]["publish_blockers"] = []
        assert any(b.startswith("gate-7") for b in blockers_of(raw))

    def test_gate8_p0_blocker(self, card):
        card["publication"]["publish_blockers"] = ["P0: 测试阻塞项"]
        assert any(b.startswith("gate-8") for b in blockers_of(card))

    def test_gate_p7_requires_approved_human_review(self, card):
        """P7 人工批准是发布的硬性前置（ADR-012：自动发布禁令的程序化闸门）。"""
        card["audit"]["human_reviews"] = [
            {"reviewer": "human:reviewer-001", "decision": "needs_changes",
             "reviewed_at": "2026-08-28T10:00:00Z"}
        ]
        assert any(b.startswith("gate-p7") for b in blockers_of(card))
        card["audit"]["human_reviews"] = []
        assert any(b.startswith("gate-p7") for b in blockers_of(card))

    def test_gate0_wrong_lifecycle(self, card):
        card["publication"]["lifecycle_state"] = "candidate"
        assert any(b.startswith("gate-0") for b in blockers_of(card))


class TestNoSilentPublish:
    def test_gold_set_cards_not_publishable(self):
        """全部金标准卡必须被门禁拦下（P7 未完成）。"""
        for path in sorted((ROOT / "data" / "gold_set").glob("OP-*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            ok, blockers = evaluate_publish_gate(data)
            assert not ok, f"{path.stem} 不应通过发布门禁"
            assert blockers, f"{path.stem} 应有阻塞项"
