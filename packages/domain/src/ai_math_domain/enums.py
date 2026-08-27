"""枚举定义：与 schemas/problem_card/v1.0.0 的枚举一一对应。"""

from __future__ import annotations

from enum import Enum


class OpenStatus(str, Enum):
    """§10.1 允许的开放状态。"""

    CONFIRMED_OPEN = "confirmed_open"
    LIKELY_OPEN = "likely_open"
    STATUS_UNCERTAIN = "status_uncertain"
    PARTIALLY_RESOLVED = "partially_resolved"
    RESOLVED = "resolved"
    WITHDRAWN_OR_MALFORMED = "withdrawn_or_malformed"


class LifecycleState(str, Enum):
    """§10 生命周期状态机状态（Schema 层为小写下划线，对应规范 mermaid 图的 PascalCase）。"""

    CANDIDATE = "candidate"
    NORMALIZED = "normalized"
    DEDUP_REVIEW = "dedup_review"
    STATUS_REVIEW = "status_review"
    SCORED = "scored"
    PUBLISHED = "published"
    REJECTED = "rejected"
    STALE = "stale"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"
    NONE = "none"


class ScoreBand(str, Enum):
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    MEDIUM_LOW = "medium_low"
    LOW = "low"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceKind(str, Enum):
    SOURCE_QUOTE = "source_quote"
    DOCUMENT_LINK = "document_link"
    COMPUTED_METRIC = "computed_metric"
    PROGRAM_OUTPUT = "program_output"
    MODEL_INFERENCE = "model_inference"
    EXPERT_JUDGMENT = "expert_judgment"
    UNVERIFIED_CLAIM = "unverified_claim"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"


# 状态命名映射（规范 mermaid PascalCase ↔ Schema 小写下划线），见 docs/02 待裁决问题的处理约定：
PASCAL_TO_LOWER = {
    state.name.capitalize().replace("_", ""): state.value
    for state in LifecycleState
}
