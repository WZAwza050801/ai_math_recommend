"""Pydantic 请求/响应模型（对外契约，字段名与前端约定逐字对齐）。

注意：POST /api/cards 与 /lifecycle /publish 的请求体是**完整问题卡 JSON**，
其权威校验在 schemas/problem_card/v1.0.0（JSON Schema，见 cardjson.py），
此处只定义轻量包装与响应结构。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# 审核决定取值（端点契约）。与 Schema audit.human_reviews.decision 的差异
# （Schema 暂无 "rejected"）在 apps/api/README.md 中记录，Phase 2 升 Schema 对齐。
ReviewDecision = Literal["approved", "needs_changes", "rejected"]

DrawRadius = Literal["relevance", "adjacent_exploration", "distant_serendipity"]


class HealthResponse(BaseModel):
    status: str
    db: bool
    cards: int


class ImportResult(BaseModel):
    imported: int
    skipped: int


class CardListItem(BaseModel):
    problem_id: str
    title: str
    primary_domain: str
    open_status: str
    lifecycle_state: str
    importance_band: str | None = None
    affordance_band: str | None = None
    publishable: bool


class CardListResponse(BaseModel):
    total: int
    items: list[CardListItem]


class LifecycleRequest(BaseModel):
    target: str = Field(..., description="目标生命周期状态，如 normalized / dedup_review")
    changed_by: str | None = Field(
        default=None, description="操作者标识（human:xxx / agent:xxx）；缺省记为 api:lifecycle"
    )


class ReviewRequest(BaseModel):
    reviewer: str = Field(..., description='审核人，必须为 "human:<名字>"（ADR-012）')
    decision: ReviewDecision
    notes: str = ""


class ReviewResponse(BaseModel):
    problem_id: str
    version: int
    review: dict[str, Any]
    human_reviews: list[dict[str, Any]]


class GateResponse(BaseModel):
    publishable: bool
    blockers: list[str]


class VersionMeta(BaseModel):
    version: int
    changed_by: str | None = None
    reason: str | None = None
    created_at: datetime


class VersionListResponse(BaseModel):
    problem_id: str
    total: int
    items: list[VersionMeta]


class DrawItem(BaseModel):
    problem_id: str
    title: str
    one_sentence: str
    primary_domain: str
    open_status: str
    importance_band: str | None = None
    affordance_band: str | None = None
    radius: DrawRadius
    score: float = Field(..., description="仅供排序调试（ranking-weights-v0.1），前端只显示等级")
    score_band: str


class DrawResponse(BaseModel):
    mode: str
    weights_version: str
    draws: list[DrawItem]


class SourceItem(BaseModel):
    source_id: str
    name: str
    priority_tier: str
    trust_tier: str
    enabled: bool
    source_type: str
    base_url: str


class SourceListResponse(BaseModel):
    total: int
    items: list[SourceItem]
