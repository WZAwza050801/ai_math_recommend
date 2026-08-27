"""SRC-0021 · Crossref 连接器（公开 API，无鉴权，礼貌池靠 mailto）。

接入方式：GET https://api.crossref.org/works?query.bibliographic=<kw>&rows=N。
meta 存 DOI / is-referenced-by-count / container-title / type；
text = abstract（JATS 片段转纯文本；无则空串，绝不编造）。
"""

from __future__ import annotations

from .base import (
    Connector,
    FetchOutcome,
    FetchReport,
    RawDocument,
    strip_markup,
    utc_now_iso,
)

CROSSREF_API_URL = "https://api.crossref.org/works"
CONTACT_EMAIL = "3116809059@qq.com"
DEFAULT_KEYWORD = "open problem conjecture"


def _first_str(value: object) -> str:
    """``["x"]``/``"x"`` -> ``"x"``；其余 -> 空串。"""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""
    if isinstance(value, str):
        return value.strip()
    return ""


def parse_work_items(
    payload: dict,
    fetched_at: str | None = None,
    source_id: str = "SRC-0021",
) -> list[RawDocument]:
    """Crossref /works JSON -> RawDocument 列表（离线可测）。"""
    fetched = fetched_at or utc_now_iso()
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        return []

    documents: list[RawDocument] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = str(item.get("DOI", "") or "").strip()
        if not doi:
            continue  # 无 DOI 的条目放弃：external_id 必须真实存在
        title = _first_str(item.get("title"))
        container = _first_str(item.get("container-title"))
        abstract = strip_markup(str(item.get("abstract", "") or ""))
        issued_raw = item.get("issued") or {}
        issued_parts = (
            issued_raw.get("date-parts", [[]])[0] if isinstance(issued_raw, dict) else []
        )
        issued_year = issued_parts[0] if isinstance(issued_parts, list) and issued_parts else None
        documents.append(
            RawDocument(
                source_id=source_id,
                external_id=doi,
                url=str(item.get("URL", "") or f"https://doi.org/{doi}"),
                title=title,
                text=abstract,
                fetched_at=fetched,
                meta={
                    "doi": doi,
                    "is_referenced_by_count": item.get("is-referenced-by-count"),
                    "container_title": container,
                    "type": str(item.get("type", "") or ""),
                    "issued_year": issued_year,
                },
            )
        )
    return documents


class CrossrefConnector(Connector):
    source_id = "SRC-0021"
    source_name = "Crossref"
    base_url = "https://api.crossref.org"

    def __init__(self, session=None, keyword: str = DEFAULT_KEYWORD) -> None:
        super().__init__(session=session)
        self.keyword = keyword or DEFAULT_KEYWORD

    def fetch(self, limit: int = 20) -> FetchReport:
        params = {
            "query.bibliographic": self.keyword,
            "rows": max(limit, 1),
            "mailto": CONTACT_EMAIL,
        }
        outcome: FetchOutcome = self.session.get_json(CROSSREF_API_URL, params=params)
        if not outcome.ok:
            return self._finish([], [outcome.as_error()])
        documents = parse_work_items(outcome.json_value or {}, fetched_at=utc_now_iso())
        errors: list[str] = []
        if not documents:
            errors.append(f"Crossref 响应无可用 items（HTTP {outcome.status}）")
        return self._finish(self._truncate_to_limit(documents, limit), errors)
