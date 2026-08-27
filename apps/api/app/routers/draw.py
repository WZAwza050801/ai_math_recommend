"""抽卡端点：受控探索抽样（ADR-007；基线 §13.6）。

池子 = lifecycle_state ∈ {scored, published} 的卡。按 pool_mix_for_mode(mode)
把 n 拆成 relevance / adjacent_exploration / distant_serendipity 三段：

- relevance：按 user_score 降序取前 n_rel（I/A 取卡内 feature 均值或缺省 50，
  P=50、C=75 为契约默认值；ranking-weights-v0.1）；
- adjacent_exploration：与 top1 卡同 primary_domain 的随机（邻近探索）;
- distant_serendipity：其余域的随机（远距离偶遇）。

score 仅供排序调试（保留 1 位小数）；面向用户只应展示 score_band 等级（§13.2）。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ai_math_ranking import WEIGHTS_VERSION, RankingInputError, band_from_score, pool_mix_for_mode

from .. import cardjson
from ..database import get_db
from ..models import Card
from ..schemas import DrawResponse

router = APIRouter(prefix="/api", tags=["draw"])

DRAWABLE_STATES = ("scored", "published")


@dataclass
class _Entry:
    row: Card
    card: dict[str, Any]
    score: float


def _to_item(entry: _Entry, radius: str) -> dict[str, Any]:
    card = entry.card
    return {
        "problem_id": entry.row.problem_id,
        "title": entry.row.title,
        "one_sentence": cardjson.one_sentence(card),
        "primary_domain": entry.row.primary_domain,
        "open_status": entry.row.open_status,
        "importance_band": entry.row.importance_band,
        "affordance_band": entry.row.affordance_band,
        "radius": radius,
        "score": round(entry.score, 1),
        "score_band": band_from_score(entry.score),
    }


@router.get("/draw", response_model=DrawResponse)
def draw(
    mode: str = Query(default="balanced", description="balanced | steady | adventurous"),
    n: int = Query(default=10, ge=1, le=50, description="抽取总数"),
    domain: str | None = Query(default=None, description="限定 primary_domain"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        mix = pool_mix_for_mode(mode)
    except RankingInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    n_adjacent = round(n * mix.adjacent_exploration)
    n_distant = round(n * mix.distant_serendipity)
    n_relevance = max(n - n_adjacent - n_distant, 0)

    query = db.query(Card).filter(Card.lifecycle_state.in_(DRAWABLE_STATES))
    if domain:
        query = query.filter(Card.primary_domain == domain)

    entries: list[_Entry] = []
    for row in query.all():
        card = cardjson.load_card(row)
        entries.append(_Entry(row=row, card=card, score=cardjson.user_score_for_card(card)))
    entries.sort(key=lambda e: (-e.score, e.row.problem_id))

    top_domain = entries[0].row.primary_domain if entries else None
    relevance = entries[:n_relevance]
    taken = {e.row.problem_id for e in relevance}
    adjacent_pool = [
        e
        for e in entries
        if e.row.problem_id not in taken and top_domain is not None and e.row.primary_domain == top_domain
    ]
    distant_pool = [
        e for e in entries if e.row.problem_id not in taken and e.row.primary_domain != top_domain
    ]

    adjacent = random.sample(adjacent_pool, min(n_adjacent, len(adjacent_pool)))
    distant = random.sample(distant_pool, min(n_distant, len(distant_pool)))

    draws = (
        [_to_item(e, "relevance") for e in relevance]
        + [_to_item(e, "adjacent_exploration") for e in adjacent]
        + [_to_item(e, "distant_serendipity") for e in distant]
    )
    return {"mode": mode, "weights_version": WEIGHTS_VERSION, "draws": draws}
