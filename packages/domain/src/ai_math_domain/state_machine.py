"""生命周期状态机（设计规范 §10）。

合法迁移（源自规范 mermaid 图，逐边转录）：

    [*] --> Candidate
    Candidate --> Normalized
    Normalized --> DedupReview
    DedupReview --> StatusReview
    StatusReview --> Scored
    Scored --> Published
    Candidate --> Rejected
    DedupReview --> Rejected
    StatusReview --> Rejected
    Published --> Stale
    Stale --> StatusReview
    Published --> Resolved
    Resolved --> Archived

Rejected 与 Archived 为终态（无出边）。对"Scored 及更早阶段发现已解决"的流转空白
（docs/02 待裁决问题），本实现采取保守策略：任何非 Published 状态不得直接进入
Resolved；此类情况应先完成审核（P7）后由管理员裁决，见 ADR-009。
"""

from __future__ import annotations

from .enums import LifecycleState

# 每个状态的合法后继（None 值的键为终态，列出仅为可读性）
TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.CANDIDATE: frozenset({LifecycleState.NORMALIZED, LifecycleState.REJECTED}),
    LifecycleState.NORMALIZED: frozenset({LifecycleState.DEDUP_REVIEW}),
    LifecycleState.DEDUP_REVIEW: frozenset({LifecycleState.STATUS_REVIEW, LifecycleState.REJECTED}),
    LifecycleState.STATUS_REVIEW: frozenset({LifecycleState.SCORED, LifecycleState.REJECTED}),
    LifecycleState.SCORED: frozenset({LifecycleState.PUBLISHED}),
    LifecycleState.PUBLISHED: frozenset({LifecycleState.STALE, LifecycleState.RESOLVED}),
    LifecycleState.STALE: frozenset({LifecycleState.STATUS_REVIEW}),
    LifecycleState.RESOLVED: frozenset({LifecycleState.ARCHIVED}),
    LifecycleState.REJECTED: frozenset(),
    LifecycleState.ARCHIVED: frozenset(),
}

TERMINAL_STATES: frozenset[LifecycleState] = frozenset(
    {s for s, nxt in TRANSITIONS.items() if not nxt}
)


class LifecycleError(Exception):
    """非法生命周期迁移。"""


def can_transition(source: LifecycleState | str, target: LifecycleState | str) -> bool:
    src = LifecycleState(source)
    dst = LifecycleState(target)
    return dst in TRANSITIONS[src]


def assert_transition(source: LifecycleState | str, target: LifecycleState | str) -> None:
    src = LifecycleState(source)
    dst = LifecycleState(target)
    if dst not in TRANSITIONS[src]:
        raise LifecycleError(
            f"非法生命周期迁移: {src.value} -> {dst.value}；"
            f"{src.value} 的合法后继: {sorted(s.value for s in TRANSITIONS[src]) or ['（终态）']}"
        )
