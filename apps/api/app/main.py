"""FastAPI 应用入口（Phase 1：数据库与管理后台）。

启动（开发模式，workdir=apps/api）：
    python -m uvicorn app.main:app --port 8901

数据库：缺省 sqlite:///./aimath.db；生产用环境变量 DATABASE_URL 切 PostgreSQL
（ADR-014）。发布红线（ADR-012）：本应用唯一的 published 写路径是
POST /api/cards/{problem_id}/publish，且必须同时通过状态机与发布门禁。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from . import cardjson, database
from .database import Base, get_db
from .models import Card
from .routers import admin, cards, draw, lifecycle, reviews, sources

PLACEHOLDER_HTML = """<!doctype html>
<html lang="zh">
<head><meta charset="utf-8"><title>AI Math Recommend API</title></head>
<body style="font-family: system-ui; max-width: 40rem; margin: 4rem auto;">
  <h1>AI Math Recommend — 管理后端 API 已启动</h1>
  <p>apps/web/index.html 尚未挂载：抽卡前端将在 Phase 3 交付。</p>
  <p>可先访问 <a href="/docs">/docs</a> 查看接口文档，或 <a href="/api/health">/api/health</a> 检查服务状态。</p>
</body>
</html>"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 开发/单机模式直接建表（无迁移框架；生产 PostgreSQL 的迁移策略见 ADR-014）
    Base.metadata.create_all(bind=database.engine)
    yield


app = FastAPI(
    title="AI Math Recommend API",
    description=(
        "AI 数学开放问题抽卡推荐系统 — Phase 1 管理后端。"
        "发布门禁 gate-p7（ADR-012）不可绕过：published 只能经 /publish 获得。"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(admin.router)
app.include_router(cards.router)
app.include_router(lifecycle.router)
app.include_router(reviews.router)
app.include_router(draw.router)
app.include_router(sources.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    db_ok = True
    cards = 0
    try:
        db.execute(text("SELECT 1"))
        cards = int(db.query(func.count(Card.problem_id)).scalar() or 0)
    except Exception:  # noqa: BLE001 - 健康检查必须吞掉异常并以 db:false 表达
        db_ok = False
    return {"status": "ok", "db": db_ok, "cards": cards}


@app.get("/", include_in_schema=False)
def index() -> Any:
    """返回 apps/web/index.html（前端尚未挂载时给占位说明）。"""
    if cardjson.WEB_INDEX_PATH.exists():
        return FileResponse(cardjson.WEB_INDEX_PATH)
    return HTMLResponse(PLACEHOLDER_HTML)
