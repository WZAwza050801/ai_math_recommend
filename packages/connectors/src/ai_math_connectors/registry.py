"""连接器注册表：source_id -> Connector 类。

只包含 data/source_registry 中 ``enabled: true`` 且已指定 connector_name 的
P0 源（ADR-011：未启用来源不得采集）。若上游 registry 调整 enabled 状态，
必须同步增删此处并在 docs/03 记录。

提供 ``verify_enabled(registry_dir)`` 做离线交叉校验：
确认 CONNECTORS 中每个 source_id 在登记条目里确实 enabled=true，
防止"代码里悄悄多接了未批准源"。
"""

from __future__ import annotations

import json
import pathlib

from .arxiv import ArxivConnector
from .base import Connector
from .crossref import CrossrefConnector
from .erdosproblems import ErdosProblemsConnector
from .formal_conjectures import FormalConjecturesConnector
from .github import GithubConnector
from .openalex import OpenAlexConnector
from .opg import OpenProblemGardenConnector
from .zbmath import ZbMathConnector

#: source_id -> Connector 类。只含 P0 已启用（enabled=true）源。
CONNECTORS: dict[str, type[Connector]] = {
    ArxivConnector.source_id: ArxivConnector,                      # SRC-0002 arXiv
    FormalConjecturesConnector.source_id: FormalConjecturesConnector,  # SRC-0008 formal-conjectures
    OpenProblemGardenConnector.source_id: OpenProblemGardenConnector,  # SRC-0009 Open Problem Garden
    ErdosProblemsConnector.source_id: ErdosProblemsConnector,      # SRC-0010 erdosproblems.com
    OpenAlexConnector.source_id: OpenAlexConnector,                # SRC-0011 OpenAlex
    GithubConnector.source_id: GithubConnector,                    # SRC-0019 GitHub 公共仓库
    ZbMathConnector.source_id: ZbMathConnector,                    # SRC-0020 zbMATH Open
    CrossrefConnector.source_id: CrossrefConnector,                # SRC-0021 Crossref
}


def get_connector(source_id: str) -> type[Connector] | None:
    """按 source_id 取连接器类；未注册（含未启用）源返回 None。"""
    return CONNECTORS.get(source_id)


def default_registry_dir() -> pathlib.Path:
    """仓库内 data/source_registry 目录（按本文件位置回溯）。"""
    return pathlib.Path(__file__).resolve().parents[4] / "data" / "source_registry"


def verify_enabled(registry_dir: str | pathlib.Path | None = None) -> dict[str, bool]:
    """交叉校验 CONNECTORS 的每个 source_id 在登记条目中 enabled=true。

    返回 {source_id: 是否通过}；登记文件缺失视为不通过（诚实报告，
    由调用方决定是否继续）。smoke 脚本在采集前调用本函数。
    """
    directory = pathlib.Path(registry_dir) if registry_dir else default_registry_dir()
    results: dict[str, bool] = {}
    for source_id in CONNECTORS:
        entry_path = directory / f"{source_id}.json"
        ok = False
        if entry_path.exists():
            try:
                entry = json.loads(entry_path.read_text(encoding="utf-8"))
                ok = bool(entry.get("enabled")) is True
            except (OSError, ValueError):
                ok = False
        results[source_id] = ok
    return results
