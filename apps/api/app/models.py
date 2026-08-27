"""ORM 模型（Phase 1 关系主存落地，ADR-003 / ADR-004）。

- `cards`：问题卡主表。`card_json` 列保存完整问题卡 JSON（Schema 的权威序列化），
  其余列为面向查询/筛选的投影索引列。
- `card_versions`：不可变版本快照表（ADR-004）。**每次卡片内容修改都追加一行**
  完整快照，只增不删改；`cards.version` 为当前版本号。

发布门禁说明（ADR-012）：`publishable` 列只是 `card_json.publication.publishable`
的镜像，权威判断永远在 packages/domain 的 evaluate_publish_gate；本应用不存在
任何绕过 gate-p7 的写路径——全系统只有 POST /api/cards/{id}/publish 在
"状态机合法迁移 + 门禁零 blocker"同时成立时才允许置 published。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Card(Base):
    """问题卡主表。"""

    __tablename__ = "cards"

    problem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    primary_domain: Mapped[str] = mapped_column(String(64), default="", index=True)
    open_status: Mapped[str] = mapped_column(String(32), default="", index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="candidate", index=True)
    publishable: Mapped[bool] = mapped_column(Boolean, default=False)
    importance_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    affordance_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    card_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class CardVersion(Base):
    """不可变版本快照（只追加，永不更新/删除；ADR-004）。"""

    __tablename__ = "card_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cards.problem_id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
