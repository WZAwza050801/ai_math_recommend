"""问题卡 CRUD：列表筛选、详情、新建 candidate 卡、版本轨迹查询。

新建卡的唯一入口（POST /api/cards）强制 lifecycle_state="candidate"：
生命周期推进只能走 /lifecycle 与 /publish 端点（状态机 + 发布门禁，ADR-012）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import cardjson
from ..database import get_db
from ..models import Card, CardVersion
from ..schemas import CardListItem, CardListResponse, VersionListResponse

router = APIRouter(prefix="/api", tags=["cards"])

DEFAULT_CHANGED_BY = "api:create"


def get_card_or_404(db: Session, problem_id: str) -> Card:
    row = db.get(Card, problem_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"问题卡不存在: {problem_id}")
    return row


def card_list_item(row: Card) -> dict[str, Any]:
    return {
        "problem_id": row.problem_id,
        "title": row.title,
        "primary_domain": row.primary_domain,
        "open_status": row.open_status,
        "lifecycle_state": row.lifecycle_state,
        "importance_band": row.importance_band,
        "affordance_band": row.affordance_band,
        "publishable": bool(row.publishable),
    }


@router.get("/cards", response_model=CardListResponse)
def list_cards(
    status: str | None = Query(default=None, description="open_status.status 精确匹配"),
    domain: str | None = Query(default=None, description="primary_domain 精确匹配"),
    lifecycle: str | None = Query(default=None, description="lifecycle_state 精确匹配"),
    q: str | None = Query(default=None, description="匹配 title 或卡内 JSON（LIKE）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(Card)
    if status:
        query = query.filter(Card.open_status == status)
    if domain:
        query = query.filter(Card.primary_domain == domain)
    if lifecycle:
        query = query.filter(Card.lifecycle_state == lifecycle)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Card.title.ilike(like), Card.card_json.ilike(like)))
    total = query.count()
    rows = (
        query.order_by(Card.problem_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "items": [card_list_item(r) for r in rows]}


@router.get("/cards/{problem_id}")
def get_card(problem_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = get_card_or_404(db, problem_id)
    return cardjson.load_card(row)


@router.post("/cards", status_code=201)
def create_card(
    payload: dict[str, Any] = Body(..., description="完整问题卡 JSON"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    errors = cardjson.schema_errors(payload)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "问题卡未通过 problem_card Schema 校验", "errors": errors},
        )

    publication = payload.get("publication") or {}
    if publication.get("lifecycle_state") != "candidate":
        raise HTTPException(
            status_code=422,
            detail={
                "message": '新卡 lifecycle_state 必须为 "candidate"（后续迁移走 /lifecycle，发布走 /publish）',
                "actual": publication.get("lifecycle_state"),
            },
        )

    problem_id = str(payload.get("problem_id") or "")
    if not problem_id:
        raise HTTPException(status_code=422, detail="problem_id 缺失")
    if db.get(Card, problem_id) is not None:
        raise HTTPException(status_code=409, detail=f"problem_id 已存在: {problem_id}")

    row = Card(problem_id=problem_id, version=0, card_json="")
    db.add(row)
    audit = payload.get("audit") or {}
    changed_by = str(audit.get("created_by") or DEFAULT_CHANGED_BY)
    cardjson.write_snapshot(
        db, row, payload, version=1, changed_by=changed_by, reason="create:candidate"
    )
    return cardjson.load_card(row)


@router.get("/cards/{problem_id}/versions", response_model=VersionListResponse)
def list_versions(problem_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    get_card_or_404(db, problem_id)
    rows = (
        db.query(CardVersion)
        .filter(CardVersion.problem_id == problem_id)
        .order_by(CardVersion.version.asc())
        .all()
    )
    return {
        "problem_id": problem_id,
        "total": len(rows),
        "items": [
            {
                "version": r.version,
                "changed_by": r.changed_by,
                "reason": r.reason,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
