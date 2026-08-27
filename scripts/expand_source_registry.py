"""按用户 2026-08-28 批准的接入优先级清单扩充 Source Registry。

- 为既有 14 源回填 priority_tier；
- 新增 P0/P1/P2/observation 条目（覆盖用户清单九大类中近期能用的部分）；
- 启用 P0 免鉴权源（enabled=true，ADR-013 记录用户一揽子批准）；
- 输出对齐 source_registry Schema v1.1.0。

用法：python scripts/expand_source_registry.py
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "data" / "source_registry"

# 既有源的优先级回填（用户清单裁定）
EXISTING_TIERS = {
    "SRC-0001": ("P1", None),            # Clay：数量少难度高，名望池（用户表一 P1）
    "SRC-0002": ("P0", "ArxivConnector"),
    "SRC-0003": ("observation", None),    # Tao 博客：观察源
    "SRC-0004": ("P2", None),            # Polymath：状态分散
    "SRC-0005": ("P1", None),            # OEIS：第二批（用户表五 P1）
    "SRC-0006": ("observation", None),    # Wikipedia：背景与别名，不单独定状态（用户表八）
    "SRC-0007": ("P1", None),            # Zenodo：仅监测未核验声称
    "SRC-0008": ("P0", "FormalConjecturesConnector"),
    "SRC-0009": ("P0", "OpenProblemGardenConnector"),
    "SRC-0010": ("P0", "ErdosProblemsConnector"),
    "SRC-0011": ("P0", "OpenAlexConnector"),
    "SRC-0012": ("P0", None),            # MathOverflow：SE API，署名规则
    "SRC-0013": ("observation", None),    # Naukas：观察源
    "SRC-0014": ("P1", None),            # 学术期刊（经 Crossref/zbMATH 覆盖）
}

# 用户批准直接启用的 P0 源（全部免账号免 key）
P0_ENABLED = {
    "SRC-0002", "SRC-0008", "SRC-0009", "SRC-0010", "SRC-0011",
    "SRC-0012", "SRC-0015", "SRC-0016", "SRC-0019", "SRC-0020", "SRC-0021",
}

def entry(sid, name, stype, url, access, license_, tier, priority, refresh,
          formats, usage, enabled=False, notes="", rate="", connector=None,
          attribution=True):
    d = {
        "source_id": sid, "name": name, "source_type": stype, "base_url": url,
        "access_method": access, "license": license_,
        "attribution_required": attribution, "refresh_policy": refresh,
        "trust_tier": tier, "priority_tier": priority,
        "connector_version": "none" if connector is None else "0.1.0",
        "content_formats": formats, "allowed_usage": usage,
        "enabled": enabled, "notes": notes,
    }
    if rate:
        d["rate_limit_notes"] = rate
    if connector:
        d["connector_name"] = connector
    return d

NEW = [
    # --- 表一：直接提供开放问题的平台 ---
    entry("SRC-0015", "AIM Problem Lists", "problem_list",
          "https://aimath.org/aimnews/problemlists/", "web_page", "待核验（AIM 站点条款）",
          "B", "P0", "quarterly", ["html", "pdf"], ["statement", "source_link"],
          notes="跨代数/数论/分析/几何/组合的问题列表；不同列表格式不统一，逐列表核验。"),
    entry("SRC-0016", "AIM Workshop Problem Lists", "problem_list",
          "https://aimath.org/aimworkshops/", "web_page", "待核验（AIM 站点条款）",
          "B", "P0", "quarterly", ["html", "pdf"], ["statement", "source_link"],
          notes="AIM 专题研讨会问题集；状态更新频率不同。"),
    entry("SRC-0017", "FrontierMath: Open Problems", "problem_list",
          "https://frontiermath.org/", "web_page", "待核验（规模与许可需单独确认）",
          "B", "P1", "monthly", ["html"], ["statement", "source_link"],
          notes="面向 AI 数学发现的可验证开放问题；批量访问与开放许可需单独确认后启用。"),
    entry("SRC-0018", "AMR Problem Lists（Association for Mathematical Research）", "problem_list",
          "https://www.amermathres.org/", "web_page", "待核验", "B", "P1", "quarterly",
          ["html"], ["statement", "source_link"],
          notes="跨领域开放问题集索引；是索引不是最终权威来源，须追到原始出处。"),
    entry("SRC-0019", "GitHub（问题库/形式化仓库）", "structured_repository",
          "https://github.com/", "http_api", "平台条款+仓库各自许可（公共 REST/GraphQL）",
          "C", "P0", "weekly", ["json", "markdown", "lean"], ["metadata", "statement", "source_link"],
          rate="公共 API 60 req/h（未认证）；仅采集公共仓库。",
          connector="GitHubConnector"),
    # --- 表二：论文/引用/文献平台 ---
    entry("SRC-0020", "zbMATH Open", "scholarly_graph",
          "https://api.zbmath.org/v1/", "http_api", "zbMATH Open 使用条款（署名，限额）",
          "C", "P0", "weekly", ["json", "bibtex"], ["metadata", "citation_metrics"],
          rate="REST API；礼貌速率 ≤1 req/s，注明用途。", connector="ZbMathConnector"),
    entry("SRC-0021", "Crossref", "scholarly_graph",
          "https://api.crossref.org/", "http_api", "公共 API（礼貌池，mailto 参数）",
          "C", "P0", "weekly", ["json"], ["metadata", "citation_metrics"],
          rate="礼貌池需 mailto 参数；建议 ≤1 req/s。",
          connector="CrossrefConnector"),
    entry("SRC-0022", "Semantic Scholar", "scholarly_graph",
          "https://api.semanticscholar.org/", "http_api", "API 条款（建议申请免费 Key）",
          "C", "P1", "weekly", ["json"], ["metadata", "citation_metrics"],
          rate="未认证 100 req/5min；申请 Key 后启用。"),
    entry("SRC-0023", "CORE", "scholarly_graph",
          "https://api.core.ac.uk/v3/", "http_api", "需免费 API Key", "C", "P1", "monthly",
          ["json"], ["full_text_index"], rate="需 API Key。"),
    entry("SRC-0024", "HAL", "preprint_server",
          "https://api.archives-ouvertes.fr/", "http_api", "开放（Etalab）", "C", "P1",
          "monthly", ["json"], ["metadata", "full_text_index"]),
    entry("SRC-0025", "EuDML", "journal", "https://eudml.org/", "web_page",
          "各期刊许可不一", "C", "P1", "quarterly", ["html", "pdf"], ["source_link", "full_text_index"]),
    entry("SRC-0026", "Numdam", "journal", "https://numdam.org/", "web_page",
          "各期刊许可不一", "C", "P1", "quarterly", ["pdf"], ["source_link"]),
    # --- 表五：数学对象与计算数据库 ---
    entry("SRC-0027", "LMFDB", "structured_repository",
          "https://www.lmfdb.org/", "http_api", "CC BY-NC-SA 类（以站点为准）",
          "B", "P1", "monthly", ["json"], ["metadata", "source_link"],
          notes="L-函数/模形式/椭圆曲线等对象库；反例与对象核验。"),
    entry("SRC-0028", "House of Graphs", "structured_repository",
          "https://houseofgraphs.org/", "http_api", "学术用途（以站点条款为准）",
          "B", "P1", "quarterly", ["json"], ["metadata"],
          notes="极值图/反例图；图论反例搜索。"),
    # --- 表四：形式化 ---
    entry("SRC-0029", "mathlib（Lean 4）", "structured_repository",
          "https://github.com/leanprover-community/mathlib4", "git",
          "Apache-2.0", "B", "P1", "monthly", ["lean"], ["metadata", "source_link"],
          notes="作为 AI 友好性特征（形式化覆盖度），不直接产卡。"),
    # --- 表六：人物/奖项 ---
    entry("SRC-0030", "ORCID", "encyclopedia", "https://pub.orcid.org/v3.0/", "http_api",
          "CC BY 4.0（公共 API）", "C", "P1", "quarterly", ["json"], ["metadata"],
          notes="作者身份对齐。"),
    entry("SRC-0031", "IMU Fields Medal（官方）", "prize_problem_page",
          "https://www.mathunion.org/ims-prizes/fields-medal", "web_page", "官方网页引用",
          "B", "P1", "static", ["html"], ["metadata"],
          notes="奖项=谱系证据；荣誉不得直接转成重要性分（用户表六规则）。"),
    entry("SRC-0032", "Abel Prize（官方）", "prize_problem_page",
          "https://abelprize.no/", "web_page", "官方网页引用", "B", "P1", "static",
          ["html"], ["metadata"]),
    # --- 表三/观察源 ---
    entry("SRC-0033", "Gil Kalai 博客", "blog", "https://gilkalai.wordpress.com/", "web_page",
          "博客引用（署名）", "D", "observation", "weekly", ["html"], ["source_link"],
          notes="观察源：新问题/进展线索，不能单独作为状态依据。"),
    entry("SRC-0034", "Mathstodon", "community_qa", "https://mathstodon.xyz/", "http_api",
          "Mastodon 公共 API 条款", "D", "observation", "weekly", ["json"], ["source_link"],
          notes="观察源。"),
    entry("SRC-0035", "TOPP（The Open Problems Project, 计算几何）", "problem_list",
          "https://topp.openproblem.net/", "web_page", "待核验", "B", "P2", "quarterly",
          ["html", "pdf"], ["statement", "source_link"], notes="部分条目年代较早。"),
    entry("SRC-0036", "Kourovka Notebook（群论）", "problem_list",
          "https://kourovka-notebook.org/", "pdf", "按版本发布", "B", "P2", "quarterly",
          ["pdf"], ["statement", "source_link"]),
    entry("SRC-0037", "Scottish Book / Electronic Scottish Café", "problem_list",
          "https://kielich.amu.edu.pl/StefanBanach/e-scottish.html", "web_page", "历史资料引用",
          "B", "P2", "static", ["html", "pdf"], ["statement", "source_link"],
          notes="许多问题已有后续进展，状态须再核验。"),
    entry("SRC-0038", "Wikidata", "encyclopedia", "https://www.wikidata.org/", "http_api",
          "CC0", "C", "P2", "monthly", ["json"], ["metadata"],
          notes="人物/机构实体对齐。"),
    entry("SRC-0039", "Mathematics Genealogy Project", "encyclopedia",
          "https://www.genealogy.math.nd.edu/", "web_page", "站点条款（谨慎自动化）",
          "C", "P2", "static", ["html"], ["metadata"], notes="学术谱系辅助证据。"),
    entry("SRC-0040", "Lean Zulip", "community_qa", "https://leanprover.zulipchat.com/", "web_page",
          "公共存档可读；谨慎自动化", "D", "P2", "weekly", ["html"], ["source_link"]),
    entry("SRC-0041", "Oberwolfach/BIRS/ICERM/IPAM 报告", "problem_list",
          "https://www.mfo.de/", "pdf", "各中心条款", "B", "P2", "quarterly",
          ["pdf"], ["statement", "source_link"], notes="专题会议问题与研究方向。"),
    entry("SRC-0042", "Internet Archive", "structured_repository",
          "https://archive.org/advancedsearch.php", "http_api", "公共域+各条目许可",
          "C", "P2", "manual", ["json", "pdf"], ["full_text_index"],
          notes="历史专著/会议录/问题集。"),
]

def main() -> None:
    # 回填既有 14 源（幂等：新源已带 priority_tier，跳过）
    for path in sorted(REG.glob("SRC-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["source_id"] in EXISTING_TIERS:
            tier, connector = EXISTING_TIERS[data["source_id"]]
            data["priority_tier"] = tier
            if connector:
                data["connector_name"] = connector
                data["connector_version"] = "0.1.0"
        data["enabled"] = data["source_id"] in P0_ENABLED
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for e in NEW:
        if not (REG / f"{e['source_id']}.json").exists():
            e["enabled"] = e["source_id"] in P0_ENABLED
            (REG / f"{e['source_id']}.json").write_text(
                json.dumps(e, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    total = len(list(REG.glob("SRC-*.json")))
    enabled = [p.stem for p in REG.glob("SRC-*.json")
               if json.loads(p.read_text(encoding="utf-8"))["enabled"]]
    print(f"注册表共 {total} 源；启用 {len(enabled)}：{', '.join(sorted(enabled))}")

if __name__ == "__main__":
    main()
