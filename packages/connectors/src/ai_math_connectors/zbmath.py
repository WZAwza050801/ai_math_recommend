"""SRC-0020 · zbMATH Open 连接器（公开 REST API，无鉴权）。

接入方式：GET https://api.zbmath.org/v1/document/_search?search_string=<kw>&count=N。
2026-02 实测响应 schema：identifier="1262.42012" / id=6149149 /
title={"title":…} / contributors.authors[].name /
editorial_contributions[type=summary].text（评论正文，受许可限制时源返回
占位说明文字，原样保存）/ msc / zbmath_url 等。

text = 摘要/评论文本（源未给或被许可屏蔽时只存元数据——不编造）。
"""

from __future__ import annotations

from typing import Any

from .base import Connector, FetchOutcome, FetchReport, RawDocument, utc_now_iso

ZBMATH_SEARCH_URL = "https://api.zbmath.org/v1/document/_search"
DEFAULT_KEYWORD = "open problem conjecture"


def _as_plain_str(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(v).strip() for v in value if isinstance(v, (str, int, float))]
        return " ".join(p for p in parts if p)
    if isinstance(value, str):
        return value.strip()
    return ""


def _title_text(value: Any) -> str:
    """title 字段兼容 {title: …, subtitle: …} 与 str/list[str] 三种形态。"""
    if isinstance(value, dict):
        for key in ("title", "original", "subtitle"):
            text = _as_plain_str(value.get(key))
            if text:
                return text
        return ""
    return _as_plain_str(value)


def _authors(value: Any) -> list[str]:
    """contributors.authors 兼容 [{name}] / list[str] / str。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        value = value.get("authors")
    names: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name", "") or "").strip()
                if name:
                    names.append(name)
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
    return names


def _links(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                url = str(item.get("url", "") or "").strip()
                if url:
                    urls.append(url)
            elif isinstance(item, str) and item.strip():
                urls.append(item.strip())
    return urls


def _summary_text(value: Any) -> str:
    """editorial_contributions 里 type=summary 的评论文本（许可屏蔽时是占位说明，原样保留）。"""
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for item in value:
        if isinstance(item, dict) and item.get("contribution_type") in (None, "", "summary"):
            text = str(item.get("text", "") or "").strip()
            if text:
                parts.append(text)
    return " ".join(parts)


def _external_id(result: dict[str, Any]) -> str:
    """优先 zbMATH 号（identifier，如 "1262.42012"），其次数字 id，再次首个链接。

    都没有返回空串（由调用方跳过该条目：宁缺不编造）。
    """
    identifier = result.get("identifier")
    if isinstance(identifier, dict):
        identifier = identifier.get("identifier")
    ident = str(identifier or "").strip()
    if ident:
        return ident
    numeric_id = result.get("id")
    if numeric_id is not None:
        return str(numeric_id)
    links = _links(result.get("links"))
    if links:
        return links[0]
    return ""


def parse_search_results(
    payload: dict,
    fetched_at: str | None = None,
    source_id: str = "SRC-0020",
) -> list[RawDocument]:
    """zbMATH _search JSON -> RawDocument 列表（离线可测，防御式解析）。"""
    fetched = fetched_at or utc_now_iso()
    results = payload.get("result") if isinstance(payload, dict) else None
    if results is None and isinstance(payload, dict):
        results = payload.get("results")
    if not isinstance(results, list):
        return []

    documents: list[RawDocument] = []
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        external_id = _external_id(item)
        if not external_id:
            # 无任何真实标识符的条目：宁跳过不编造
            continue
        links = _links(item.get("links"))
        msc_codes = [
            str(m.get("code", "")).strip()
            for m in (item.get("msc") or [])
            if isinstance(m, dict) and m.get("code")
        ]
        documents.append(
            RawDocument(
                source_id=source_id,
                external_id=external_id,
                url=str(item.get("zbmath_url", "") or "") or (links[0] if links else ""),
                title=_title_text(item.get("title")),
                text=_summary_text(item.get("editorial_contributions")),
                fetched_at=fetched,
                meta={
                    "authors": _authors(item.get("contributors")),
                    "links": links,
                    "source": _as_plain_str(
                        (item.get("source") or {}).get("source")
                        if isinstance(item.get("source"), dict)
                        else item.get("source")
                    ),
                    "year": item.get("year"),
                    "document_type": _as_plain_str(
                        (item.get("document_type") or {}).get("description")
                        if isinstance(item.get("document_type"), dict)
                        else None
                    ),
                    "msc_codes": msc_codes,
                    "document_index": index,
                },
            )
        )
    return documents


class ZbMathConnector(Connector):
    source_id = "SRC-0020"
    source_name = "zbMATH Open"
    base_url = "https://api.zbmath.org/v1/"

    def __init__(self, session=None, keyword: str = DEFAULT_KEYWORD) -> None:
        super().__init__(session=session)
        self.keyword = keyword or DEFAULT_KEYWORD

    def fetch(self, limit: int = 20) -> FetchReport:
        params = {
            "search_string": self.keyword,
            "count": max(limit, 1),
        }
        outcome: FetchOutcome = self.session.get_json(ZBMATH_SEARCH_URL, params=params)
        if not outcome.ok:
            return self._finish([], [outcome.as_error()])
        documents = parse_search_results(
            outcome.json_value or {}, fetched_at=utc_now_iso()
        )
        errors: list[str] = []
        if not documents:
            errors.append(f"zbMATH 响应无可解析条目（HTTP {outcome.status}）")
        return self._finish(self._truncate_to_limit(documents, limit), errors)
