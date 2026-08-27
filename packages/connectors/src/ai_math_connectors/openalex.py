"""SRC-0011 · OpenAlex 连接器（公开 API，CC0，无鉴权）。

接入方式：GET https://api.openalex.org/works（polite pool：带 mailto 参数）。
meta 存 cited_by_count / publication_year / doi；text 由
abstract_inverted_index 重建（无摘要则空串，绝不编造）。
"""

from __future__ import annotations

from .base import Connector, FetchOutcome, FetchReport, RawDocument, utc_now_iso

OPENALEX_API_URL = "https://api.openalex.org/works"
CONTACT_EMAIL = "3116809059@qq.com"

#: registry 允许用途是 metadata / citation_metrics；抓取默认限定近年文献。
DEFAULT_FILTER = "from_publication_date:2024-01-01"
DEFAULT_SEARCH = '"open problem" conjecture'


def rebuild_abstract_from_inverted_index(inverted: dict[str, list[int]] | None) -> str:
    """OpenAlex abstract_inverted_index -> 摘要文本。

    结构是 {词: [出现位置...]}；按位置回填后用单空格连接。
    无输入/空输入返回空串（缺失即缺失，不编造）。
    """
    if not isinstance(inverted, dict) or not inverted:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                positioned.append((pos, word))
    positioned.sort()
    return " ".join(word for _, word in positioned)


def _openalex_id_from_url(id_url: str) -> str:
    """``https://openalex.org/W2100837269`` -> ``W2100837269``。"""
    return (id_url or "").rstrip("/").rsplit("/", 1)[-1]


def parse_work_list(
    payload: dict,
    fetched_at: str | None = None,
    source_id: str = "SRC-0011",
) -> list[RawDocument]:
    """OpenAlex /works JSON 响应 -> RawDocument 列表（离线可测）。"""
    fetched = fetched_at or utc_now_iso()
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []

    documents: list[RawDocument] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        oa_id = _openalex_id_from_url(str(item.get("id", "")))
        if not oa_id:
            continue
        doi = str(item.get("doi", "") or "")
        title = str(item.get("display_name", "") or "")
        text = rebuild_abstract_from_inverted_index(item.get("abstract_inverted_index"))
        documents.append(
            RawDocument(
                source_id=source_id,
                external_id=oa_id,
                url=doi or str(item.get("id", "")),
                title=title,
                text=text,
                fetched_at=fetched,
                meta={
                    "openalex_id": oa_id,
                    "doi": doi,
                    "publication_year": item.get("publication_year"),
                    "cited_by_count": item.get("cited_by_count"),
                },
            )
        )
    return documents


class OpenAlexConnector(Connector):
    source_id = "SRC-0011"
    source_name = "OpenAlex API"
    base_url = "https://api.openalex.org"

    def __init__(self, session=None, search: str = DEFAULT_SEARCH,
                 filter_expr: str = DEFAULT_FILTER) -> None:
        super().__init__(session=session)
        self.search = search
        self.filter_expr = filter_expr

    def fetch(self, limit: int = 20) -> FetchReport:
        params = {
            "search": self.search,
            "per_page": max(limit, 1),
            "mailto": CONTACT_EMAIL,
            "filter": self.filter_expr,
        }
        outcome: FetchOutcome = self.session.get_json(OPENALEX_API_URL, params=params)
        if not outcome.ok:
            return self._finish([], [outcome.as_error()])
        documents = parse_work_list(outcome.json_value or {}, fetched_at=utc_now_iso())
        errors: list[str] = []
        if not documents:
            errors.append(f"OpenAlex 响应无可用 results（HTTP {outcome.status}）")
        return self._finish(self._truncate_to_limit(documents, limit), errors)
