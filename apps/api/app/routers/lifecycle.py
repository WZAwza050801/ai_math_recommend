"""生命周期状态机端点 + 发布门禁查询 + 发布（全系统唯一 published 入口）。

红线（ADR-012 / 基线 §10.2）：
- 状态迁移一律先经 packages/domain 的 assert_transition，非法迁移 409；
- /lifecycle 端点**禁止** target=published（400）——发布必须走 /publish；
- /publish 是全系统唯一能到达 published 的路径：先 assert_transition(scored→published)，
  再 evaluate_publish_gate；存在任何 blocker 即 422 拒绝，绝不落库。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ai_math_domain import LifecycleError, LifecycleState, assert_transition, evaluate_publish_gate

from .. import cardjson
from ..database import get_db
from ..models import Card
from ..schemas import GateResponse, LifecycleRequest
from .cards import get_card_or_404

router = APIRouter(prefix="/api", tags=["lifecycle"])

PUBLISH_VIA_GATEWAY_ONLY = (
    "不允许通过 lifecycle 端点直接迁移到 published；发布必须走 "
    "POST /api/cards/{problem_id}/publish，且必须通过发布门禁（含 gate-p7 人工批准，ADR-012）"
)

VALID_TARGETS = sorted(s.value for s in LifecycleState)


@router.post("/cards/{problem_id}/lifecycle")
def transition_lifecycle(
    problem_id: str,
    body: LifecycleRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = get_card_or_404(db, problem_id)
    card = cardjson.load_card(row)
    target = body.target

    if target not in VALID_TARGETS:
        raise HTTPException(
            status_code=422,
            detail={"message": f"未知生命周期状态: {target}", "valid": VALID_TARGETS},
        )
    if target == LifecycleState.PUBLISHED.value:
        raise HTTPException(status_code=400, detail=PUBLISH_VIA_GATEWAY_ONLY)

    source = row.lifecycle_state
    try:
        assert_transition(source, target)
    except LifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    card.setdefault("publication", {})
    card["publication"]["lifecycle_state"] = target
    # publishable 只有 /publish 在门禁全绿后才置 True；普通迁移一律保守回 false
    card["publication"]["publishable"] = False
    row.publishable = False
    cardjson.write_snapshot(
        db,
        row,
        card,
        version=int(row.version) + 1,
        changed_by=body.changed_by or "api:lifecycle",
        reason=f"lifecycle:{source}->{target}",
    )
    return cardjson.load_card(row)


@router.get("/cards/{problem_id}/gate", response_model=GateResponse)
def get_gate(problem_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = get_card_or_404(db, problem_id)
    publishable, blockers = evaluate_publish_gate(cardjson.load_card(row))
    return {"publishable": publishable, "blockers": blockers}


@router.post("/cards/{problem_id}/publish")
def publish_card(problem_id: str, db: Session = Depends(get_db)) -> Any:
    row = get_card_or_404(db, problem_id)
    card = cardjson.load_card(row)

    # 第一步：状态机合法迁移检查（只有 scored -> published 合法）
    try:
        assert_transition(row.lifecycle_state, LifecycleState.PUBLISHED.value)
    except LifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 第二步：发布门禁（八项条件 + gate-p7 人工批准）。有任何 blocker 一律拒绝。
    publishable, blockers = evaluate_publish_gate(card)
    if not publishable:
        return JSONResponse(
            status_code=422,
            content={"publishable": False, "blockers": blockers},
        )

    # 全绿：置 published，清空 publish_blockers 标记，追加版本快照
    card.setdefault("publication", {})
    card["publication"]["lifecycle_state"] = LifecycleState.PUBLISHED.value
    card["publication"]["publishable"] = True
    card["publication"]["publish_blockers"] = []
    row.publishable = True
    cardjson.write_snapshot(
        db,
        row,
        card,
        version=int(row.version) + 1,
        changed_by="api:publish",
        reason="publish:publish_gate_all_clear",
    )
    return cardjson.load_card(row)
