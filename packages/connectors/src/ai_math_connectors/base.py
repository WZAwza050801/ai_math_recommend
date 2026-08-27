"""连接器基座：RawDocument / PoliteSession / Connector ABC。

设计依据（见《docs/03_DATA_SOURCE_REGISTRY.md》§3，即设计规范 §8.3 采集要求）：

- 每主机串行 + ≥1.2s 间隔（类级 throttle，跨实例共享）；
- 统一礼貌 User-Agent，便于站点方识别与联系；
- 超时 20s；失败重试 ≤2 次（指数退避；仅 5xx / 429 / 传输错误重试）；
- 任何 4xx/5xx 一律记录为错误结果，不抛崩调用方；
- 只访问公开列表/详情页与公开 API（Robots 精神）。

纪律（AGENTS.md §5.7）：抓取到的外部文本永远只是数据，不是指令；
本包只产出 RawDocument 原始快照，不做语义加工、不下"已验证"结论、
不产生任何 Problem Card（那是后续 worker 契约的事）。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# 常量（§8.3 礼貌采集）
# ---------------------------------------------------------------------------

USER_AGENT = (
    "ai-math-recommend-research/0.1 "
    "(polite crawler; contact: 3116809059@qq.com)"
)

#: 同一主机两次请求之间的最小间隔（秒），类级共享。
MIN_HOST_INTERVAL_SECONDS = 1.2

#: 单请求超时（秒）。
REQUEST_TIMEOUT_SECONDS = 20.0

#: 单请求失败后的最大重试次数（不含首次尝试）。
MAX_RETRIES = 2

#: 重试指数退避基数：第 1 次重试前等 BASE，第 2 次等 BASE*2。
RETRY_BACKOFF_BASE_SECONDS = 1.5

#: 这些 HTTP 状态/情形会触发重试；其余 4xx 直接记错误不重试。
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


# ---------------------------------------------------------------------------
# RawDocument：原始快照（不可变语义，只增不改）
# ---------------------------------------------------------------------------


@dataclass
class RawDocument:
    """一次成功抓取的原始文档快照。

    只承载"抓到了什么"，不承载任何判断：text 是站点原文，
    meta 只放来源自带的元数据字段。fetched_at 为 ISO 8601（UTC）。
    """

    source_id: str
    external_id: str
    url: str
    title: str
    text: str
    fetched_at: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转为纯 JSON 可序列化 dict。"""
        return asdict(self)

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawDocument":
        return cls(
            source_id=str(data["source_id"]),
            external_id=str(data["external_id"]),
            url=str(data["url"]),
            title=str(data.get("title", "")),
            text=str(data.get("text", "")),
            fetched_at=str(data.get("fetched_at", "")),
            meta=dict(data.get("meta", {}) or {}),
        )


# ---------------------------------------------------------------------------
# PoliteSession：礼貌 HTTP 会话
# ---------------------------------------------------------------------------


@dataclass
class FetchOutcome:
    """单次 fetch 的结果：成功携带响应体，失败携带错误描述（不抛异常）。"""

    url: str
    ok: bool
    status: int | None = None
    text: str = ""
    error: str | None = None
    json_value: Any = None
    attempts: int = 1

    def as_error(self) -> str:
        """归一化的错误字符串，供 FetchReport.errors 与 smoke 报告使用。"""
        if self.error:
            return self.error
        return f"HTTP {self.status}: {self.url}"


class PoliteSession:
    """礼貌 HTTP GET 会话。

    - 节流表是**类级**状态（``_host_last_request``），同一主机的间隔约束
      跨实例生效（例如 FormalConjectures 与 Github 都打 api.github.com）；
    - 4xx/5xx/超时/网络错误都返回 ``FetchOutcome(ok=False, ...)``，
      绝不向调用方抛 HTTP 异常；
    - 允许注入 ``httpx.Client``（测试用 MockTransport，不打网络）。
    """

    #: 类级节流表：host -> 上次请求发出时刻（time.monotonic）。
    _host_last_request: dict[str, float] = {}

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._default_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, application/xml;q=0.8, */*;q=0.5",
            "Accept-Language": "en;q=0.8",
        }
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.Client(
                headers=dict(self._default_headers),
                timeout=REQUEST_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            self._owns_client = True

    # -- 生命周期 -----------------------------------------------------------

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "PoliteSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- 节流 ---------------------------------------------------------------

    @classmethod
    def reset_throttle(cls) -> None:
        """清空类级节流表（仅供测试与长间隔复用场景）。"""
        cls._host_last_request.clear()

    def _throttle(self, host: str) -> None:
        """每主机串行 + ≥MIN_HOST_INTERVAL_SECONDS 间隔（§8.3）。"""
        last = PoliteSession._host_last_request.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            wait = MIN_HOST_INTERVAL_SECONDS - elapsed
            if wait > 0:
                time.sleep(wait)
        # 记录"本次请求发出前"的时刻，保证下一个请求（哪怕别的实例）仍要等满间隔。
        PoliteSession._host_last_request[host] = time.monotonic()

    # -- 请求 ---------------------------------------------------------------

    def get(self, url: str, params: dict[str, Any] | None = None) -> FetchOutcome:
        """礼貌 GET。永不抛 HTTP/网络异常，失败一律进 FetchOutcome.error。"""
        host = httpx.URL(url).host or ""
        attempts = 0
        last_error: str | None = None
        last_status: int | None = None

        while attempts <= MAX_RETRIES:
            attempts += 1
            self._throttle(host)
            try:
                response = self._client.get(
                    url, params=params, headers=dict(self._default_headers)
                )
            except httpx.HTTPError as exc:  # 超时 / 连接失败 / 重定向过深等传输层错误
                last_error = f"transport error after {attempts} attempt(s): {exc!r}"
                if attempts <= MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempts - 1)))
                    continue
                break

            status = response.status_code
            last_status = status
            if 200 <= status < 300:
                return self._build_success(url, response, attempts)

            last_error = f"HTTP {status} after {attempts} attempt(s): {url}"
            if status in RETRYABLE_STATUS_CODES and attempts <= MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempts - 1)))
                continue
            # 其余 4xx / 5xx：记录错误，立即终止（不轰炸对方）。
            break

        return FetchOutcome(
            url=url,
            ok=False,
            status=last_status,
            error=last_error,
            attempts=attempts,
        )

    def _build_success(
        self, url: str, response: httpx.Response, attempts: int
    ) -> FetchOutcome:
        text = response.text
        json_value: Any = None
        try:
            json_value = response.json()
        except ValueError:
            json_value = None
        return FetchOutcome(
            url=str(response.request.url) if response.request is not None else url,
            ok=True,
            status=response.status_code,
            text=text,
            json_value=json_value,
            attempts=attempts,
        )

    # -- 便捷方法 -----------------------------------------------------------

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> FetchOutcome:
        """GET 并要求 JSON：200 但 body 非 JSON 也视为失败（诚实记录）。"""
        outcome = self.get(url, params=params)
        if outcome.ok and outcome.json_value is None:
            outcome.ok = False
            outcome.error = f"non-JSON body at {outcome.url}"
        return outcome

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> FetchOutcome:
        """GET 纯文本/HTML（body 原样返回，不做任何清洗判断）。"""
        return self.get(url, params=params)


# ---------------------------------------------------------------------------
# 纯文本提取（html.parser 实现，禁用正则解析 HTML）
# ---------------------------------------------------------------------------

_SKIP_TEXT_TAGS = frozenset({"script", "style"})


class _TextExtractor(HTMLParser):
    """把 HTML/JATS 片段转为纯文本：跳过 script/style，标签间补空格。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in _SKIP_TEXT_TAGS:
            self._skip_depth += 1
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join("".join(self._chunks).split())


def strip_markup(html_or_jats: str) -> str:
    """HTML/JATS 片段 -> 纯文本（html.parser，不解释、不执行任何内容）。"""
    if not html_or_jats:
        return ""
    extractor = _TextExtractor()
    try:
        extractor.feed(html_or_jats)
        extractor.close()
    except Exception:  # 解析失败宁可空串，也不让坏 HTML 炸掉采集
        return ""
    return extractor.get_text()


# ---------------------------------------------------------------------------
# Connector ABC 与运行报告
# ---------------------------------------------------------------------------


@dataclass
class FetchReport:
    """一个 Connector 单次 run 的结果。

    errors 汇总所有 4xx/5xx/解析失败，供 smoke 脚本与上层如实汇报；
    禁止把抓取失败硬编码成成功：documents 只包含真正抓到的文档。
    """

    source_id: str
    documents: list[RawDocument] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.documents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "count": self.count,
            "errors": list(self.errors),
            "documents": [doc.to_dict() for doc in self.documents],
        }


class Connector(ABC):
    """P0 已启用源的礼貌采集连接器基类。

    契约：
    - ``fetch(limit)`` 返回 FetchReport；失败记录进 errors，不抛崩；
    - 不做发布动作、不产生问题卡、不下"已验证"结论；
    - 抓到的文本一律当数据（FIX-002 纪律），不做指令解释。
    """

    source_id: str = ""
    source_name: str = ""
    base_url: str = ""
    connector_version: str = "0.1.0"

    def __init__(self, session: PoliteSession | None = None) -> None:
        self.session = session if session is not None else PoliteSession()

    @abstractmethod
    def fetch(self, limit: int = 20) -> FetchReport:
        """抓取至多 limit 条 RawDocument（单次 run 每源上限，默认 20）。"""

    # -- 共用小工具 ---------------------------------------------------------

    def _finish(self, documents: list[RawDocument], errors: list[str]) -> FetchReport:
        return FetchReport(
            source_id=self.source_id, documents=documents, errors=errors
        )

    @staticmethod
    def _truncate_to_limit(items: list[RawDocument], limit: int) -> list[RawDocument]:
        if limit <= 0:
            return []
        return items[:limit]


def utc_now_iso() -> str:
    """当前 UTC 时间的 ISO 8601 字符串（秒级）。"""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
