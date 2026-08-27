"""来源注册表只读查询：直读 data/source_registry/*.json（Phase 1 不入库）。

ADR-011 红线：enabled=true 只能由 P0 人工批准流程修改；本端点只读，
不提供任何修改 enabled 的路径。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .. import cardjson
from ..schemas import SourceListResponse

router = APIRouter(prefix="/api", tags=["sources"])

ENABLED_FILTERS = ("true", "false", "all")
_TIER_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
    return (_TIER_ORDER.get(item["priority_tier"], 9), item["source_id"])


@router.get("/sources", response_model=SourceListResponse)
def list_sources(
    enabled: str = Query(default="all", description="true | false | all"),
) -> dict[str, Any]:
    if enabled not in ENABLED_FILTERS:
        raise HTTPException(
            status_code=422,
            detail={"message": "enabled 只接受 true / false / all", "actual": enabled},
        )

    items: list[dict[str, Any]] = []
    for path in sorted(cardjson.SOURCE_REGISTRY_DIR.glob("*.json")):
        try:
            src = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(src, dict) or not src.get("source_id"):
            continue
        items.append(
            {
                "source_id": str(src.get("source_id") or ""),
                "name": str(src.get("name") or ""),
                "priority_tier": str(src.get("priority_tier") or ""),
                "trust_tier": str(src.get("trust_tier") or ""),
                "enabled": bool(src.get("enabled") or False),
                "source_type": str(src.get("source_type") or ""),
                "base_url": str(src.get("base_url") or ""),
            }
        )

    if enabled == "true":
        items = [i for i in items if i["enabled"]]
    elif enabled == "false":
        items = [i for i in items if not i["enabled"]]

    items.sort(key=_sort_key)
    return {"total": len(items), "items": items}
