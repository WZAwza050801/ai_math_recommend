"""启动引导：把 packages/domain 与 packages/ranking 加入 sys.path。

对齐 tests/conftest.py 的做法：本仓库的 packages 未安装为发行包，
统一用源码路径直连（packages/*/src），保证 API 进程复用与测试完全一致的
状态机（assert_transition/can_transition）、发布门禁（evaluate_publish_gate）
与排序基线（user_score/pool_mix_for_mode，ranking-weights-v0.1）。

同时导出 REPO_ROOT：data/gold_set、data/source_registry、schemas、apps/web
均相对仓库根定位，不依赖进程工作目录。
"""

from __future__ import annotations

import pathlib
import sys

APP_DIR = pathlib.Path(__file__).resolve().parent  # apps/api/app
API_DIR = APP_DIR.parent  # apps/api
REPO_ROOT = API_DIR.parent.parent  # 仓库根


def ensure_paths() -> pathlib.Path:
    for rel in ("packages/domain/src", "packages/ranking/src"):
        p = str(REPO_ROOT / rel)
        if p not in sys.path:
            sys.path.insert(0, p)
    return REPO_ROOT


REPO_ROOT = ensure_paths()
