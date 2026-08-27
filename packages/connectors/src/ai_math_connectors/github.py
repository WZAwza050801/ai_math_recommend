"""SRC-0019 · GitHub 连接器（公共仓库 REST API，无鉴权）。

通用能力：
- ``list_dir(owner, repo, path)`` -> ``[{name, download_url, type}]``；
- ``fetch_raw(url)`` -> 文件原文（raw.githubusercontent.com 等）。
只访问公共仓库；未认证公共 API 限 60 req/h，由 PoliteSession 每主机
≥1.2s 串行兜底，并把失败如实记入 errors。
"""

from __future__ import annotations

from .base import Connector, FetchOutcome, FetchReport, PoliteSession, RawDocument, utc_now_iso

GITHUB_API_BASE = "https://api.github.com"

#: fetch() 的默认采样目标：formal-conjectures 的 ErdosProblems 目录（公共）。
#: 注：仓库曾把 conjectures/ 重组为 FormalConjectures/<Topic>/（2026 实测）。
DEFAULT_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("google-deepmind", "formal-conjectures", "FormalConjectures/ErdosProblems"),
)


def parse_contents_listing(payload: object) -> list[dict[str, str]]:
    """GitHub /contents JSON -> 归一化条目列表（离线可测）。

    只保留 name/download_url/type 三字段；非列表或坏条目一律跳过。
    """
    if not isinstance(payload, list):
        return []
    entries: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "")
        download_url = str(item.get("download_url", "") or "")
        entry_type = str(item.get("type", "") or "")
        if not name:
            continue
        entries.append(
            {"name": name, "download_url": download_url, "type": entry_type}
        )
    return entries


class GithubConnector(Connector):
    source_id = "SRC-0019"
    source_name = "GitHub（问题库/形式化仓库）"
    base_url = "https://github.com/"

    def __init__(self, session: PoliteSession | None = None) -> None:
        super().__init__(session=session)

    # -- 通用工具（供其他连接器复用，如 FormalConjectures） -----------------

    def list_dir(self, owner: str, repo: str, path: str) -> tuple[list[dict[str, str]], str | None]:
        """列公共仓库目录。返回 (条目列表, 错误或 None)。"""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
        outcome = self.session.get_json(url)
        if not outcome.ok:
            return [], outcome.as_error()
        return parse_contents_listing(outcome.json_value), None

    def fetch_raw(self, url: str) -> tuple[str, str | None]:
        """抓取原始文件文本。返回 (text, 错误或 None)。"""
        outcome = self.session.get_text(url)
        if not outcome.ok:
            return "", outcome.as_error()
        return outcome.text, None

    # -- Connector 契约 ------------------------------------------------------

    def fetch(self, limit: int = 20, targets: tuple[tuple[str, str, str], ...] | None = None) -> FetchReport:
        """从默认目标目录抓取至多 limit 个原始文件作为 RawDocument。"""
        use_targets = targets if targets is not None else DEFAULT_TARGETS
        documents: list[RawDocument] = []
        errors: list[str] = []
        fetched_at = utc_now_iso()

        for owner, repo, path in use_targets:
            if len(documents) >= limit:
                break
            entries, listing_error = self.list_dir(owner, repo, path)
            if listing_error:
                errors.append(f"list_dir {owner}/{repo}/{path}: {listing_error}")
                continue
            for entry in entries:
                if len(documents) >= limit:
                    break
                if entry["type"] != "file" or not entry["download_url"]:
                    continue
                text, fetch_error = self.fetch_raw(entry["download_url"])
                if fetch_error:
                    errors.append(f"fetch_raw {entry['name']}: {fetch_error}")
                    continue
                documents.append(
                    RawDocument(
                        source_id=self.source_id,
                        external_id=entry["name"],
                        url=entry["download_url"],
                        title=entry["name"],
                        text=text,
                        fetched_at=fetched_at,
                        meta={
                            "owner": owner,
                            "repo": repo,
                            "path": f"{path.rstrip('/')}/{entry['name']}",
                        },
                    )
                )

        if not documents and not errors:
            errors.append("GitHub 目标目录无文件条目")
        return self._finish(self._truncate_to_limit(documents, limit), errors)
