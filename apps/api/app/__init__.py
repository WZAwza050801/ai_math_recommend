"""ai_math_recommend 管理后端（Phase 1）。

FastAPI 应用包。启动入口：apps/api 目录下 `uvicorn app.main:app`。

包导入即执行 _bootstrap.ensure_paths()，保证无论从哪个入口
（uvicorn / pytest / 脚本）加载，packages/domain 与 packages/ranking 都可用。
"""

from ._bootstrap import ensure_paths

ensure_paths()
