"""数据库引擎与会话（ADR-014：开发 SQLite / 生产 PostgreSQL 双模）。

连接串来源（优先级从高到低）：
1. 环境变量 DATABASE_URL（生产/CI 使用，例如
   `postgresql+psycopg://user:pass@host:5432/aimath`）；
2. 缺省 `sqlite:///./aimath.db`（本机开发，Docker 不可用场景）。

全部模型经 SQLAlchemy 2.x 编写，SQL 方言差异由 ORM 吸收；换库不改业务代码。
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./aimath.db"


def database_url() -> str:
    """读取 DATABASE_URL，缺省回退到本地 SQLite 开发库。"""
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def make_engine(url: str) -> Engine:
    """按连接串构造引擎。SQLite 需要 check_same_thread=False 以支持多线程请求。"""
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


DATABASE_URL: str = database_url()
engine: Engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """全部 ORM 模型的声明基类。"""


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：每请求一个会话，用完即关。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
