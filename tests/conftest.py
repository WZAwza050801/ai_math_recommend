"""pytest 共享配置：将本地包加入 sys.path。"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for pkg in ("packages/domain/src", "packages/ranking/src"):
    p = str(ROOT / pkg)
    if p not in sys.path:
        sys.path.insert(0, p)
