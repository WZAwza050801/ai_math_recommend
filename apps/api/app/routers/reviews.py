"""人工审核队列：向 card_json.audit.human_reviews 追加审核记录（只增不删）。

审核人格式强制 "human:<名字>"（ADR-012：自动流水线永远不能独自把卡片送入
published；agent: 前缀或其他格式一律 422 拒绝）。每次追加都落一条版本快照。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import cardjson
from ..database import get_db
from ..schemas import ReviewRequest, ReviewResponse
from .cards import get_card_or_404

router = APIRouter(prefix="/api", tags=["reviews"])

HUMAN_PREFIX = "human:"


@router.post("/cards/{problem_id}/reviews", response_model=ReviewResponse)
def add_review(
    problem_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = get_card_or_404(db, problem_id)
    if not body.reviewer.startswith(HUMAN_PREFIX) or len(body.reviewer) <= len(HUMAN_PREFIX):
        raise HTTPException(
            status_code=422,
            detail={
                "message": f'审核人必须为人工账号，格式 "{HUMAN_PREFIX}<名字>"（ADR-012：自动流水线不得审批）',
                "actual": body.reviewer,
            },
        )

    card = cardjson.load_card(row)
    audit = card.get("audit")
    if not isinstance(audit, dict):
        audit = {}
        card["audit"] = audit
    human_reviews = audit.setdefault("human_reviews", [])
    if not isinstance(human_reviews, list):  # pragma: no cover - Schema 已保证
        raise HTTPException(status_code=422, detail="audit.human_reviews 结构非法，拒绝追加")

    review = {
        "reviewer": body.reviewer,
        "decision": body.decision,
        "reviewed_at": cardjson.utcnow_iso(),
        "notes": body.notes,
    }
    human_reviews.append(review)

    new_version = cardjson.write_snapshot(
        db,
        row,
        card,
        version=int(row.version) + 1,
        changed_by=body.reviewer,
        reason=f"review:{body.decision}",
    )
    return {
        "problem_id": problem_id,
        "version": new_version,
        "review": review,
        "human_reviews": human_reviews,
    }
