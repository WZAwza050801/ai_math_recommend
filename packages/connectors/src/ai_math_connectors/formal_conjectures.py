"""SRC-0008 · DeepMind formal-conjectures 连接器（GitHub raw，无鉴权）。

流程：先经 GitHub API 列候选目录的文件清单（仓库已从 ``conjectures/``
重组为 ``FormalConjectures/<Topic>/``，fetch 按候选链依次尝试），再逐个经
raw.githubusercontent.com 拉 ``.lean`` 文本；external_id = 文件名；
meta 存从源文本解析出的状态字符串（``@[category research open, …]`` 属性
或旧式 ``Status:`` 注释）——仅记录原文，不构成任何"已验证"结论。
"""

from __future__ import annotations

from .base import Connector, FetchReport, PoliteSession, RawDocument, utc_now_iso
from .github import GithubConnector

OWNER = "google-deepmind"
REPO = "formal-conjectures"

#: 清单路径候选：仓库曾重组（旧 conjectures/ 已不存在，现为
#: FormalConjectures/<Topic>/ 下的 .lean 文件）。fetch 依次尝试，
#: 取第一个能列出 .lean 文件的路径，并如实记录失败候选。
LISTING_PATH_CANDIDATES: tuple[str, ...] = (
    "conjectures",
    "FormalConjectures/ErdosProblems",
)


def parse_lean_status(lean_text: str) -> str:
    """从 .lean 文本提取状态字符串（只抄原文，不下结论）。

    当前仓库格式：定理上方的 ``@[category research open, AMS 5 11]``
    属性行 -> 返回 "research open"。
    兼容旧格式：注释行 ``Status: open`` / ``status : proven``。
    都找不到返回空串（缺失即缺失，不猜测状态）。
    """
    for line in (lean_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("@[category") and "," in stripped:
            # 形如 "@[category research open, AMS 5 11]" -> "research open"
            inner = stripped[len("@[category"):].split(",", 1)[0].strip()
            if inner:
                return inner
    for line in (lean_text or "").splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("status") or "/-- status" in lowered or "-- status" in lowered:
            after = stripped.split(":", 1)
            if len(after) == 2:
                value = after[1].strip().strip("-/").strip()
                if value:
                    return value
    return ""


def select_lean_files(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """从目录清单中筛出 type=file 且 .lean 结尾的条目（保持顺序）。"""
    return [
        e
        for e in entries
        if e.get("type") == "file" and e.get("name", "").lower().endswith(".lean")
    ]


def lean_filename_to_title(filename: str) -> str:
    """``erdos_probability_one_events.lean`` -> ``erdos probability one events``。"""
    return filename.removesuffix(".lean").replace("_", " ").strip()


class FormalConjecturesConnector(Connector):
    source_id = "SRC-0008"
    source_name = "DeepMind formal-conjectures"
    base_url = "https://github.com/google-deepmind/formal-conjectures"

    def __init__(self, session: PoliteSession | None = None,
                 owner: str = OWNER, repo: str = REPO,
                 path_candidates: tuple[str, ...] = LISTING_PATH_CANDIDATES) -> None:
        super().__init__(session=session)
        self.owner = owner
        self.repo = repo
        self.path_candidates = path_candidates
        self._github = GithubConnector(session=session)

    def fetch(self, limit: int = 20) -> FetchReport:
        documents: list[RawDocument] = []
        errors: list[str] = []
        fetched_at = utc_now_iso()

        entries: list[dict[str, str]] = []
        used_path: str | None = None
        for candidate in self.path_candidates:
            candidate_entries, listing_error = self._github.list_dir(
                self.owner, self.repo, candidate
            )
            lean_entries = select_lean_files(candidate_entries)
            if listing_error:
                errors.append(f"list_dir {candidate}: {listing_error}")
                continue
            if not lean_entries:
                errors.append(f"list_dir {candidate}: 未列出 .lean 文件，尝试下一候选路径")
                continue
            entries, used_path = lean_entries, candidate
            break

        if entries == [] or used_path is None:
            return self._finish([], errors or ["所有候选目录均未解析出 .lean 文件"])

        for entry in entries:
            if len(documents) >= limit:
                break
            download_url = entry.get("download_url", "")
            if not download_url:
                errors.append(f"missing download_url: {entry.get('name')}")
                continue
            text, fetch_error = self._github.fetch_raw(download_url)
            if fetch_error:
                errors.append(f"fetch_raw {entry['name']}: {fetch_error}")
                continue
            documents.append(
                RawDocument(
                    source_id=self.source_id,
                    external_id=entry["name"],
                    url=download_url,
                    title=lean_filename_to_title(entry["name"]),
                    text=text,
                    fetched_at=fetched_at,
                    meta={
                        "owner": self.owner,
                        "repo": self.repo,
                        "path": f"{used_path.rstrip('/')}/{entry['name']}",
                        "lean_status": parse_lean_status(text),
                    },
                )
            )

        if not documents and not errors:
            errors.append("未抓到任何 .lean 文件")
        return self._finish(self._truncate_to_limit(documents, limit), errors)
