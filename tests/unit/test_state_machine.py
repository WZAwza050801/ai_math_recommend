"""生命周期状态机单元测试（设计规范 §10 mermaid 逐边覆盖）。"""

from __future__ import annotations

import pytest

from ai_math_domain import (
    TERMINAL_STATES,
    TRANSITIONS,
    LifecycleError,
    LifecycleState,
    assert_transition,
    can_transition,
)

LEGAL_EDGES = [
    ("candidate", "normalized"),
    ("normalized", "dedup_review"),
    ("dedup_review", "status_review"),
    ("status_review", "scored"),
    ("scored", "published"),
    ("candidate", "rejected"),
    ("dedup_review", "rejected"),
    ("status_review", "rejected"),
    ("published", "stale"),
    ("stale", "status_review"),
    ("published", "resolved"),
    ("resolved", "archived"),
]


class TestLegalEdges:
    @pytest.mark.parametrize("src,dst", LEGAL_EDGES)
    def test_edge_allowed(self, src, dst):
        assert can_transition(src, dst)
        assert_transition(src, dst)  # 不抛异常

    def test_transition_table_matches_edges(self):
        """TRANSITIONS 展开后的边集合与规范 mermaid 的 12 条边完全一致。"""
        flattened = {
            (src.value, dst.value)
            for src, dsts in TRANSITIONS.items()
            for dst in dsts
        }
        assert flattened == set(LEGAL_EDGES)


class TestIllegalEdges:
    @pytest.mark.parametrize(
        "src,dst",
        [
            ("candidate", "published"),   # 跳过中间阶段（§24.3 禁止绕过状态机）
            ("candidate", "scored"),
            ("normalized", "scored"),
            ("scored", "stale"),
            ("stale", "published"),
            ("rejected", "candidate"),    # 终态不可逆
            ("archived", "published"),
            ("resolved", "published"),
            ("published", "candidate"),
        ],
    )
    def test_edge_rejected(self, src, dst):
        assert not can_transition(src, dst)
        with pytest.raises(LifecycleError):
            assert_transition(src, dst)


class TestTerminals:
    def test_terminal_states(self):
        assert TERMINAL_STATES == {LifecycleState.REJECTED, LifecycleState.ARCHIVED}

    def test_termals_have_no_successors(self):
        for s in TERMINAL_STATES:
            assert TRANSITIONS[s] == frozenset()


class TestEnumStrings:
    def test_string_coercion(self):
        assert can_transition("scored", "published")
        with pytest.raises(ValueError):
            can_transition("bogus", "published")
