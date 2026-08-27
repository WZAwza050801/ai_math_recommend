"""管理端点：金标准集导入（幂等 upsert）。

红线：导入后卡片 lifecycle 保持文件中的 scored 状态，**绝不自动发布**；
publishable 保持 false。发布仍只能走 /api/cards/{id}/publish 的门禁路径。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import cardjson
from ..database import get_db
from ..models import Card
from ..schemas import ImportResult

router = APIRouter(prefix="/api/admin", tags=["admin"])

IMPORT_CHANGED_BY = "api:import_gold_set"


def _parse_gold_set() -> list[dict[str, Any]]:
    if not cardjson.GOLD_SET_DIR.exists():
        raise HTTPException(status_code=404, detail=f"金标准目录不存在: {cardjson.GOLD_SET_DIR}")
    files = sorted(cardjson.GOLD_SET_DIR.glob("OP-*.json"))
    if not files:
        raise HTTPException(status_code=404, detail="data/gold_set 下没有 OP-*.json")

    parsed: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in files:
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: JSON 解析失败 {exc}")
            continue
        card_errors = cardjson.schema_errors(card)
        if card_errors:
            errors.append(f"{path.name}: " + "; ".join(card_errors[:5]))
            continue
        parsed.append(card)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "金标准集未通过 problem_card Schema 校验，拒绝导入", "errors": errors},
        )
    return parsed


@router.post("/import_gold_set", response_model=ImportResult)
def import_gold_set(
    force: bool = Query(default=False, description="已存在的卡是否强制覆盖重导"),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    cards = _parse_gold_set()
    imported = 0
    skipped = 0
    for card in cards:
        problem_id = str(card.get("problem_id") or "")
        if not problem_id:  # pragma: no cover - Schema required 已保证
            skipped += 1
            continue
        row = db.get(Card, problem_id)
        if row is not None and not force:
            skipped += 1
            continue
        if row is None:
            row = Card(problem_id=problem_id, version=0, card_json="")
            db.add(row)
        cardjson.write_snapshot(
            db,
            row,
            card,
            version=int(row.version) + 1,
            changed_by=IMPORT_CHANGED_BY,
            reason="import_gold_set" + ("(force)" if force else ""),
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}
