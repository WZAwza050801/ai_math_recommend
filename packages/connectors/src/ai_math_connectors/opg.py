"""SRC-0009 · Open Problem Garden 连接器（公开网页，CC-BY-SA）。

策略（按任务规格）：
1. 优先尝试 ``/api`` 列表端点（不确定存在）；
2. 404 / 非 JSON / 空结果则依次回退 ``/op/`` 索引页与首页，
   用 html.parser 解析 ``<a href="/op/...">`` 详情链接（禁正则解析 HTML）；
3. 逐个抓详情页，提取标题与正文的纯文本（2026-02 实测：正文在
   ``<div class="node"><div class="content">`` 内；旧规格假设的
   ``<div id="content">`` 在当前站点不存在），meta 存页面内的
   分类标签（/category/ 链接）。

任何一步失败都记入 errors 继续其余条目；解析不出内容宁可返回空列表。
抓取内容一律当数据（FIX-002 纪律）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

from .base import (
    Connector,
    FetchOutcome,
    FetchReport,
    RawDocument,
    utc_now_iso,
)

SITE_BASE = "https://www.openproblemgarden.org"
API_URL = f"{SITE_BASE}/api"
INDEX_URL = f"{SITE_BASE}/op/"

#: 详情页 <title> 常见的站点后缀，剥掉后作为标题。
_TITLE_SUFFIX = "open problem garden"


@dataclass
class _IndexScan:
    op_links: list[str] = field(default_factory=list)
    category_links: list[str] = field(default_factory=list)


class _IndexLinkCollector(HTMLParser):
    """收集 /op/... 详情链接与 /category/... 分类链接（仅限站内相对路径）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scan = _IndexScan()
        self._seen_op: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        href = href.strip()
        if href.startswith("/op/") and len(href) > len("/op/"):
            if href not in self._seen_op:
                self._seen_op.add(href)
                self.scan.op_links.append(href)
        elif href.startswith("/category/") and len(href) > len("/category/"):
            self.scan.category_links.append(href)


@dataclass
class _DetailScan:
    title: str = ""
    content_chunks: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    _h1_candidates: list[tuple[str, str]] = field(default_factory=list)  # (class, text)
    _h1_open: bool = False
    _h1_class: str = ""
    _h1_parts: list[str] = field(default_factory=list)
    _title_parts: list[str] = field(default_factory=list)
    _title_done: bool = False
    # Drupal 结构：<div class="node"><div class="content">…</div></div>
    _node_depth: int | None = None
    _node_done: bool = False


class _DetailPageParser(HTMLParser):
    """提取详情页标题、正文与分类标签（html.parser）。

    2026-02 实测的真实结构（Drupal）：
    - 标题：``<h1 class="title">``（回退第一个非空 <h1>，再回退 <title> 去后缀）；
    - 正文：第一个 ``<div class="node">`` 内的全部文本（旧规范假设的
      ``<div id="content">`` 在当前站点不存在）；
    - 分类：正文里指向 /category/... 的 <a> 链接。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scan = _DetailScan()
        self._skip_depth = 0

    # -- 工具 ---------------------------------------------------------------

    def _inside_node(self) -> bool:
        return self.scan._node_depth is not None and self.scan._node_depth > 0

    # -- 解析事件 ------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        attrs_dict = dict(attrs)
        css = str(attrs_dict.get("class", "") or "")
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if tag == "div":
            if self.scan._node_done or self._inside_node():
                if self._inside_node():
                    self.scan._node_depth += 1
            elif "node" in css.split():
                self.scan._node_depth = 1
            return
        if tag == "title" and not self.scan._title_done:
            self.scan._title_parts = []
            self.scan._title_done = True  # 结束时定稿一次
            return
        if tag == "h1":
            self.scan._h1_open = True
            self.scan._h1_class = css
            self.scan._h1_parts = []
            return
        if self._inside_node() and tag == "a":
            href = (attrs_dict.get("href") or "").strip()
            if href.startswith("/category/") and href not in self.scan.categories:
                self.scan.categories.append(href)

    def handle_endtag(self, tag: str) -> None:  # noqa: ANN001
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "div" and self._inside_node():
            self.scan._node_depth -= 1
            if self.scan._node_depth == 0:
                self.scan._node_depth = None
                self.scan._node_done = True
            return
        if tag == "title" and self.scan._title_done and not self.scan.title:
            candidate = self._clean_title(" ".join(self.scan._title_parts))
            if candidate:
                self.scan.title = candidate  # 仅当 h1 未定稿时作为回退
        elif tag == "h1" and self.scan._h1_open:
            text = " ".join("".join(self.scan._h1_parts).split())
            self.scan._h1_candidates.append((self.scan._h1_class, text))
            self.scan._h1_open = False

    def handle_data(self, data: str) -> None:  # noqa: ANN001
        if self._skip_depth > 0:
            return
        if self.scan._h1_open:
            self.scan._h1_parts.append(data)
        if self.scan._title_done and not self.scan.title:
            self.scan._title_parts.append(data)
        if self._inside_node() and data:
            self.scan.content_chunks.append(data)

    # -- 收尾 ----------------------------------------------------------------

    def _clean_title(self, candidate: str) -> str:
        candidate = " ".join(candidate.split())
        lowered = candidate.lower()
        if lowered.endswith(_TITLE_SUFFIX):
            candidate = candidate[: -len(_TITLE_SUFFIX)].rstrip(" |–-")
        return candidate.strip()

    def finalize(self) -> None:
        """选取标题：class 含 title 的 <h1> 优先，其次第一个非空 <h1>，最后 <title>。"""
        if not self.scan.title:
            titled = [t for cls, t in self.scan._h1_candidates if "title" in cls.split() and t]
            fallback = [t for _, t in self.scan._h1_candidates if t]
            pick = (titled or fallback)
            if pick:
                self.scan.title = self._clean_title(pick[0])


def parse_index_links(html_text: str) -> list[str]:
    """/op/ 索引页 -> 去重后的详情页相对链接列表（离线可测）。"""
    collector = _IndexLinkCollector()
    try:
        collector.feed(html_text)
        collector.close()
    except Exception:
        return []
    return collector.scan.op_links


def parse_detail(
    html_text: str,
    url: str,
    fetched_at: str | None = None,
    source_id: str = "SRC-0009",
) -> RawDocument | None:
    """详情页 HTML -> RawDocument；提取不到标题与正文时返回 None。"""
    fetched = fetched_at or utc_now_iso()
    parser = _DetailPageParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        return None
    parser.finalize()
    title = parser.scan.title
    text = " ".join("".join(parser.scan.content_chunks).split())
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    if not title or not text:
        return None
    return RawDocument(
        source_id=source_id,
        external_id=slug,
        url=url,
        title=title,
        text=text,
        fetched_at=fetched,
        meta={
            "categories": list(parser.scan.categories),
        },
    )


class OpenProblemGardenConnector(Connector):
    source_id = "SRC-0009"
    source_name = "Open Problem Garden"
    base_url = "https://www.openproblemgarden.org"

    def fetch(self, limit: int = 20) -> FetchReport:
        documents: list[RawDocument] = []
        errors: list[str] = []
        detail_links = self._get_detail_links(errors)
        if not detail_links:
            if not errors:
                errors.append("/op/ 索引页未解析出详情链接")
            return self._finish([], errors)

        fetched_at = utc_now_iso()
        for href in detail_links:
            if len(documents) >= limit:
                break
            url = f"{SITE_BASE}{href}"
            outcome: FetchOutcome = self.session.get_text(url)
            if not outcome.ok:
                errors.append(f"detail {href}: {outcome.as_error()}")
                continue
            doc = parse_detail(outcome.text, url, fetched_at=fetched_at)
            if doc is None:
                errors.append(f"detail {href}: 页面未提取到标题/正文，跳过")
                continue
            documents.append(doc)

        return self._finish(self._truncate_to_limit(documents, limit), errors)

    def _get_detail_links(self, errors: list[str]) -> list[str]:
        """依次尝试 /api（可能不存在）→ /op/ 索引页 → 首页。

        说明（2026-02 实测）：/api 与 /op/ 均返回 404，唯一可用的链接源是
        首页的"最近更改"链接；且该列表曾被 SEO 垃圾页污染（约 5 条里
        4 条非数学内容）。连接器只做透明抓取，污染过滤交由 P0/P1 人工
        与抽取阶段处理。
        """
        api_outcome = self.session.get(API_URL)
        if api_outcome.ok and isinstance(api_outcome.json_value, list):
            links: list[str] = []
            for item in api_outcome.json_value:
                if isinstance(item, dict):
                    href = str(item.get("url", "") or item.get("href", "") or "")
                    if href.startswith("/op/"):
                        links.append(href)
            if links:
                return links
        elif not api_outcome.ok:
            errors.append(f"api 端点不可用（回退索引页）: {api_outcome.as_error()}")
        else:
            errors.append("api 端点返回非列表 JSON（回退索引页）")

        for index_path, label in ((INDEX_URL, "/op/ 索引页"), (SITE_BASE + "/", "首页")):
            index_outcome = self.session.get_text(index_path)
            if not index_outcome.ok:
                errors.append(f"{label}: {index_outcome.as_error()}")
                continue
            links = parse_index_links(index_outcome.text)
            if links:
                return links
            errors.append(f"{label}: HTML 中未发现 /op/ 详情链接")
        return []
