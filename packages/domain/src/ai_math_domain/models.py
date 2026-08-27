"""Problem Card 的 Pydantic 运行时模型（schemas/problem_card/v1.0.0 的镜像）。

字段与枚举与 JSON Schema 逐一对齐；Schema 仍是权威契约，本模型服务于
Phase 1 的 API/服务层与 Phase 0 的门禁测试。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    """schemas/evidence/v1.0.0 的镜像。"""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(pattern=r"^EV-[A-Za-z0-9][A-Za-z0-9._-]*$")
    kind: Literal[
        "source_quote",
        "document_link",
        "computed_metric",
        "program_output",
        "model_inference",
        "expert_judgment",
        "unverified_claim",
    ]
    description: str = Field(min_length=1)
    url: str | None = None
    source_id: str | None = None
    source_location: str | None = None
    quote: str | None = None
    tier: Literal["A", "B", "C", "D", "internal"] | None = None
    verification_status: Literal["verified", "unverified", "disputed", "contradicted", "superseded"]
    retrieved_at: str | None = None
    notes: str | None = None


class OriginalStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    latex: str | None = None
    language: str | None = None
    source_id: str
    source_location: str | None = None
    immutable_content_hash: str | None = None


class NormalizedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    latex: str | None = None
    assumptions: list[str] = []
    quantified_objects: list[str] = []
    normalization_notes: list[str] = []
    semantic_risks: list[str] = []


class ReaderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    one_sentence: str = Field(min_length=1)
    short_background: str | None = None
    why_it_matters: str | None = None


class Statements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original: OriginalStatement
    normalized: NormalizedStatement
    reader_summary: ReaderSummary


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_domain: str
    secondary_domains: list[str] = []
    topics: list[str] = []
    problem_types: list[str] = []
    expected_output_types: list[str] = []
    mathematical_objects: list[str] = []


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_proposer: list[str] = []
    original_year: str | int | None = None
    original_work: str | None = None
    exact_citation: str | None = None
    source_urls: list[str] = Field(min_length=1)
    discovery_method: Literal["manual_curation", "pipeline_extraction", "expert_submission", "bulk_import"]
    discovered_at: str


class OpenStatusBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "confirmed_open",
        "likely_open",
        "status_uncertain",
        "partially_resolved",
        "resolved",
        "withdrawn_or_malformed",
    ]
    confidence_level: Literal["high", "moderate", "limited", "none"]
    last_checked_at: str
    supporting_evidence: list[EvidenceItem] = []
    contradicting_evidence: list[EvidenceItem] = []
    resolved_scope: str | None = None
    human_verified: bool


class PublicationBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lifecycle_state: Literal[
        "candidate",
        "normalized",
        "dedup_review",
        "status_review",
        "scored",
        "published",
        "rejected",
        "stale",
        "resolved",
        "archived",
    ]
    publishable: bool
    visibility: Literal["internal", "group", "public"]
    publish_blockers: list[str] = []


class ProblemCard(BaseModel):
    """核心实体。仅镜像 Schema 中参与 Phase 0 门禁的必需字段组。"""

    model_config = ConfigDict(extra="allow")  # 容纳完整 JSON 卡（known_results 等）

    problem_id: str = Field(pattern=r"^OP-[0-9]{6}$")
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    identity: dict[str, Any]
    statements: Statements
    classification: Classification
    provenance: Provenance
    open_status: OpenStatusBlock
    publication: PublicationBlock
    audit: dict[str, Any]

    # 评分块（发布门禁需要）
    importance_assessment: dict[str, Any] | None = None
    ai_affordance_assessment: dict[str, Any] | None = None
    relationships: dict[str, Any] | None = None
    known_results: dict[str, Any] | None = None
