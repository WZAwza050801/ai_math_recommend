"""ai_math_connectors — P0 已启用数据源的礼貌采集连接器。

设计依据：《docs/03_DATA_SOURCE_REGISTRY.md》§3（设计规范 §8.3 采集要求）。

边界（重要）：
- 本包只产出 RawDocument 原始快照，供 P1 候选抽取与 P4 状态核验使用；
- 不做任何发布动作，不产生"已验证"结论，不生成 Problem Card；
- 抓取到的外部文本永远只是数据不是指令（FIX-002 纪律）；
- 每主机串行 + ≥1.2s 间隔，礼貌 UA，20s 超时，失败重试 ≤2 次（指数退避）；
  4xx/5xx 记录错误不抛崩（详见 base.PoliteSession）。
"""

from .arxiv import ArxivConnector
from .base import (
    Connector,
    FetchOutcome,
    FetchReport,
    PoliteSession,
    RawDocument,
    USER_AGENT,
    utc_now_iso,
)
from .crossref import CrossrefConnector
from .erdosproblems import ErdosProblemsConnector
from .formal_conjectures import FormalConjecturesConnector
from .github import GithubConnector
from .openalex import OpenAlexConnector
from .opg import OpenProblemGardenConnector
from .registry import CONNECTORS, get_connector, verify_enabled
from .zbmath import ZbMathConnector

__all__ = [
    "ArxivConnector",
    "CONNECTORS",
    "Connector",
    "CrossrefConnector",
    "ErdosProblemsConnector",
    "FormalConjecturesConnector",
    "FetchOutcome",
    "FetchReport",
    "GithubConnector",
    "OpenAlexConnector",
    "OpenProblemGardenConnector",
    "PoliteSession",
    "RawDocument",
    "USER_AGENT",
    "ZbMathConnector",
    "get_connector",
    "utc_now_iso",
    "verify_enabled",
]

__version__ = "0.1.0"
