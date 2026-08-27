"""SRC-0002 · arXiv 连接器（Atom API，公开无鉴权）。

接入方式：GET http://export.arxiv.org/api/query（官方 Atom API）。
默认扫两组摘要关键词：``open problem`` / ``conjecture``，分类默认 ``math.NT``，
均可参数化。text = Atom <summary>；external_id = 去版本号的 arXiv id。

礼貌条款（registry rate_limit_notes + §8.3）：官方建议 ~1 请求/3 秒，
本连接器经 PoliteSession 每主机 ≥1.2s 串行；单次 run 每源最多 limit 条。
抓取内容一律当数据（FIX-002 纪律），预印本声称证明一律 unverified——
本包不产生任何状态结论。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import Connector, FetchOutcome, FetchReport, RawDocument, utc_now_iso

ARXIV_API_URL = "http://export.arxiv.org/api/query"

ATOM_NS = "http://www.w3.org/2005/Atom"

#: 默认扫描的摘要关键词组。
DEFAULT_KEYWORDS: tuple[str, ...] = ("open problem", "conjecture")

#: 默认 arXiv 分类。
DEFAULT_CATEGORY = "math.NT"


def _strip_version(arxiv_id: str) -> str:
    """``2401.12345v2`` -> ``2401.12345``（external_id 稳定化）。"""
    base = arxiv_id.rsplit("v", 1)
    if len(base) == 2 and base[1].isdigit():
        return base[0]
    return arxiv_id


def parse_atom(
    xml_text: str,
    fetched_at: str | None = None,
    source_id: str = "SRC-0002",
) -> list[RawDocument]:
    """把 arXiv Atom 响应解析为 RawDocument 列表（离线可测，无网络）。"""
    fetched = fetched_at or utc_now_iso()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    documents: list[RawDocument] = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        entry_id = (entry.findtext(f"{{{ATOM_NS}}}id") or "").strip()
        if not entry_id:
            continue
        raw_id = entry_id.rsplit("/abs/", 1)[-1]
        external_id = _strip_version(raw_id)
        title = " ".join((entry.findtext(f"{{{ATOM_NS}}}title") or "").split())
        summary = " ".join((entry.findtext(f"{{{ATOM_NS}}}summary") or "").split())
        authors = [
            (a.findtext(f"{{{ATOM_NS}}}name") or "").strip()
            for a in entry.findall(f"{{{ATOM_NS}}}author")
        ]
        authors = [a for a in authors if a]
        published = (entry.findtext(f"{{{ATOM_NS}}}published") or "").strip()
        categories = [
            c.get("term", "")
            for c in entry.findall(f"{{{ATOM_NS}}}category")
            if c.get("term")
        ]
        documents.append(
            RawDocument(
                source_id=source_id,
                external_id=external_id,
                url=f"https://arxiv.org/abs/{external_id}",
                title=title,
                text=summary,
                fetched_at=fetched,
                meta={
                    "authors": authors,
                    "published": published,
                    "categories": categories,
                },
            )
        )
    return documents


class ArxivConnector(Connector):
    source_id = "SRC-0002"
    source_name = "arXiv"
    base_url = "https://arxiv.org"

    def __init__(self, session=None, category: str = DEFAULT_CATEGORY,
                 keywords: tuple[str, ...] = DEFAULT_KEYWORDS) -> None:
        super().__init__(session=session)
        self.category = category
        self.keywords = tuple(keywords) or DEFAULT_KEYWORDS

    def fetch(self, limit: int = 20) -> FetchReport:
        documents: list[RawDocument] = []
        errors: list[str] = []
        seen: set[str] = set()

        per_query = max(limit, 1)
        for keyword in self.keywords:
            if len(documents) >= limit:
                break
            params = {
                "search_query": f'cat:{self.category} AND abs:"{keyword}"',
                "max_results": per_query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            outcome: FetchOutcome = self.session.get(ARXIV_API_URL, params=params)
            if not outcome.ok:
                errors.append(f"[{keyword}] {outcome.as_error()}")
                continue
            parsed = parse_atom(outcome.text, fetched_at=utc_now_iso())
            if not parsed:
                errors.append(f"[{keyword}] Atom 响应为空或解析失败（HTTP {outcome.status}）")
                continue
            for doc in parsed:
                if doc.external_id in seen:
                    continue
                seen.add(doc.external_id)
                doc.meta["matched_keyword"] = keyword
                documents.append(doc)
                if len(documents) >= limit:
                    break

        return self._finish(documents, errors)
