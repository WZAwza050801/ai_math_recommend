"""SRC-0010 · Erdős Problems（erdosproblems.com）连接器（公开网页）。

策略（按任务规格）：
1. 优先尝试 JSON 端点 ``/api/problems``（若存在）；
2. 否则回退首页 HTML 列表解析 ``/problems/<id>`` 链接（html.parser），
   并逐个抓详情页取问题陈述文本与状态徽章文本；
3. **站点结构解析不稳时：宁可返回空列表 + error 记录，绝不编造。**

text = 问题陈述原文；meta 只放页面上真实存在的字段
（如 status 徽章文本）。抓取内容一律当数据（FIX-002 纪律）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from .base import (
    Connector,
    FetchOutcome,
    FetchReport,
    RawDocument,
    strip_markup,
    utc_now_iso,
)

SITE_BASE = "https://www.erdosproblems.com"
API_URL = f"{SITE_BASE}/api/problems"
INDEX_URL = f"{SITE_BASE}/"


# ---------------------------------------------------------------------------
# API JSON 解析
# ---------------------------------------------------------------------------


def parse_api_problems(
    payload: Any,
    fetched_at: str | None = None,
    source_id: str = "SRC-0010",
) -> list[RawDocument]:
    """``/api/problems`` JSON -> RawDocument 列表（离线可测，防御式）。

    只映射真实存在的字段：id / statement / title / status 等；
    无 id 或无任何文本的条目直接跳过（不编造）。
    """
    fetched = fetched_at or utc_now_iso()
    problems: Any = payload
    if isinstance(payload, dict):
        for key in ("problems", "data", "results"):
            if isinstance(payload.get(key), list):
                problems = payload[key]
                break
    if not isinstance(problems, list):
        return []

    documents: list[RawDocument] = []
    for item in problems:
        if not isinstance(item, dict):
            continue
        problem_id = item.get("id", item.get("problem_id", item.get("number")))
        if problem_id is None:
            continue
        statement = str(item.get("statement", "") or item.get("text", "") or "").strip()
        title = str(item.get("title", "") or item.get("name", "") or "").strip()
        if not statement and not title:
            continue
        documents.append(
            RawDocument(
                source_id=source_id,
                external_id=str(problem_id),
                url=f"{SITE_BASE}/problems/{problem_id}",
                title=title,
                text=statement,
                fetched_at=fetched,
                meta={
                    "origin": "api",
                    "status": str(item.get("status", "") or item.get("state", "") or ""),
                    "solver_count": item.get("solver_count"),
                },
            )
        )
    return documents


# ---------------------------------------------------------------------------
# HTML 列表/详情解析（html.parser，禁正则解析 HTML）
# ---------------------------------------------------------------------------


@dataclass
class _ProblemLink:
    problem_id: str
    title: str = ""


class _IndexLinkParser(HTMLParser):
    """收集 ``/problems/<digits>`` 链接与其锚文本（作为标题线索）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[_ProblemLink] = []
        self._seen: set[str] = set()
        self._current: _ProblemLink | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag != "a":
            return
        href = (dict(attrs).get("href") or "").strip()
        if href.startswith("/problems/"):
            problem_id = href[len("/problems/"):].strip("/")
            if problem_id.isdigit() and problem_id not in self._seen:
                self._seen.add(problem_id)
                self._current = _ProblemLink(problem_id=problem_id)
                self._text_parts = []

    def handle_endtag(self, tag: str) -> None:  # noqa: ANN001
        if tag == "a" and self._current is not None:
            title = " ".join("".join(self._text_parts).split())
            self._current.title = title
            self.links.append(self._current)
            self._current = None
            self._text_parts = []

    def handle_data(self, data: str) -> None:  # noqa: ANN001
        if self._current is not None:
            self._text_parts.append(data)


def parse_index_problems(html_text: str) -> list[_ProblemLink]:
    """首页 HTML -> [{problem_id, title}]（离线可测）。"""
    parser = _IndexLinkParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        return []
    return parser.links


@dataclass
class _DetailScan:
    h1_title: str = ""
    title_tag: str = ""
    paragraphs: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    _title_tag_parts: list[str] = field(default_factory=list)
    _h1_parts: list[str] = field(default_factory=list)
    _badge_depth: int = 0
    _badge_parts: list[str] = field(default_factory=list)


class _DetailPageParser(HTMLParser):
    """详情页解析：<title>、<h1> 标题、<p> 段落、状态徽章（class 含 badge/label）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scan = _DetailScan()
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        attrs_dict = dict(attrs)
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if tag == "title":
            self.scan._title_tag_parts = []
            return
        if tag == "h1" and not self.scan.h1_title:
            self.scan._h1_parts = []
            return
        css = str(attrs_dict.get("class", "") or "").lower()
        if tag in ("span", "div") and ("badge" in css or "label" in css):
            self.scan._badge_depth += 1
            return

    def handle_endtag(self, tag: str) -> None:  # noqa: ANN001
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "title":
            candidate = " ".join("".join(self.scan._title_tag_parts).split())
            if candidate and not self.scan.title_tag:
                self.scan.title_tag = candidate
            return
        if tag == "h1":
            candidate = " ".join("".join(self.scan._h1_parts).split())
            if candidate and not self.scan.h1_title:
                self.scan.h1_title = candidate
            return
        if tag in ("span", "div") and self.scan._badge_depth > 0:
            self.scan._badge_depth -= 1
            badge = " ".join("".join(self.scan._badge_parts).split())
            if badge and badge not in self.scan.badges:
                self.scan.badges.append(badge)
            self.scan._badge_parts = []

    def handle_data(self, data: str) -> None:  # noqa: ANN001
        if self._skip_depth > 0:
            return
        if self.scan._badge_depth > 0:
            self.scan._badge_parts.append(data)
            return
        # <title> 与 <h1> 的文本都持续收集，由对应的 endtag 决定何时定稿。
        self.scan._title_tag_parts.append(data)
        self.scan._h1_parts.append(data)


def parse_detail(html_text: str) -> tuple[str, str, list[str]]:
    """详情页 HTML -> (标题, 正文纯文本, 徽章文本列表)（离线可测）。

    正文复用 base.strip_markup（html.parser）；提取不到正文返回空串。
    """
    parser = _DetailPageParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        return "", "", []
    title = parser.scan.h1_title or parser.scan.title_tag
    # 正文：剥标签取纯文本（整页快照；P1 抽取阶段再做结构化清洗）
    body = strip_markup(html_text)
    return title, body, list(parser.scan.badges)


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class ErdosProblemsConnector(Connector):
    source_id = "SRC-0010"
    source_name = "Erdős Problems"
    base_url = "https://www.erdosproblems.com"

    def fetch(self, limit: int = 20) -> FetchReport:
        errors: list[str] = []
        api_report = self._fetch_via_api(limit, errors)
        if api_report is not None:
            return api_report
        return self._fetch_via_html(limit, errors)

    # -- 路径 1：JSON 端点 ---------------------------------------------------

    def _fetch_via_api(self, limit: int, errors: list[str]) -> FetchReport | None:
        outcome: FetchOutcome = self.session.get(API_URL)
        if not outcome.ok:
            errors.append(f"api 端点不可用（回退 HTML）: {outcome.as_error()}")
            return None
        documents = parse_api_problems(outcome.json_value, fetched_at=utc_now_iso())
        if not documents:
            errors.append("api 端点返回内容未解析出问题条目（回退 HTML）")
            return None
        return self._finish(self._truncate_to_limit(documents, limit), errors)

    # -- 路径 2：HTML 列表 + 详情页 ------------------------------------------

    def _fetch_via_html(self, limit: int, errors: list[str]) -> FetchReport:
        index_outcome = self.session.get_text(INDEX_URL)
        if not index_outcome.ok:
            errors.append(f"index: {index_outcome.as_error()}")
            return self._finish([], errors)
        links = parse_index_problems(index_outcome.text)
        if not links:
            # 站点结构不稳：宁空不编造
            errors.append("index: HTML 未解析出 /problems/<id> 链接，返回空列表")
            return self._finish([], errors)

        documents: list[RawDocument] = []
        fetched_at = utc_now_iso()
        for link in links:
            if len(documents) >= limit:
                break
            url = f"{SITE_BASE}/problems/{link.problem_id}"
            detail_outcome = self.session.get_text(url)
            if not detail_outcome.ok:
                errors.append(f"detail {link.problem_id}: {detail_outcome.as_error()}")
                continue
            title, body, badges = parse_detail(detail_outcome.text)
            if not body:
                errors.append(f"detail {link.problem_id}: 未提取到陈述文本，跳过")
                continue
            documents.append(
                RawDocument(
                    source_id=self.source_id,
                    external_id=link.problem_id,
                    url=url,
                    title=title or link.title,
                    text=body,
                    fetched_at=fetched_at,
                    meta={
                        "origin": "html",
                        "listing_title": link.title,
                        "status_badges": badges,
                    },
                )
            )
        return self._finish(self._truncate_to_limit(documents, limit), errors)
