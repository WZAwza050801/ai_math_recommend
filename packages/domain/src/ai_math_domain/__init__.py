"""ai_math_domain — Problem Card 领域模型（Phase 0）。

对应设计规范：
- §9  Problem Card 数据模型（schemas/problem_card/v1.0.0 的 Pydantic 镜像）
- §10 生命周期状态机（本包 TRANSITIONS 强制执行）
- §10.2 发布门禁（publish_gate.evaluate_publish_gate）

JSON Schema 是机器可校验的权威契约；本包提供运行时类型、状态机与门禁逻辑。
"""

from .enums import (
    ConfidenceLevel,
    EvidenceKind,
    LifecycleState,
    OpenStatus,
    ScoreBand,
    VerificationStatus,
)
from .state_machine import TRANSITIONS, LifecycleError, can_transition, assert_transition, TERMINAL_STATES
from .models import EvidenceItem, ProblemCard
from .publish_gate import evaluate_publish_gate

__all__ = [
    "ConfidenceLevel",
    "EvidenceKind",
    "LifecycleState",
    "OpenStatus",
    "ScoreBand",
    "VerificationStatus",
    "TRANSITIONS",
    "TERMINAL_STATES",
    "LifecycleError",
    "can_transition",
    "assert_transition",
    "EvidenceItem",
    "ProblemCard",
    "evaluate_publish_gate",
]
