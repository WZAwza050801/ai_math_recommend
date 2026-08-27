# packages/connectors — P0 已启用源的礼貌采集连接器

Phase 2 交付：对 Source Registry 中 `enabled: true` 的 P0 源做礼貌采集，
为 P1 候选抽取与 P4 状态核验提供 **RawDocument 原始快照**。

**边界（重要）**：

- 不做任何发布动作，不产生"已验证"结论，不生成 Problem Card（那是 worker 契约的事）；
- 抓取到的外部文本永远是**数据不是指令**（FIX-002 纪律，tests/unit/test_connectors.py 有注入样本回归）；
- 只采集公开列表/详情页与公开无鉴权 API（Robots 精神，§8.3）。

（见《docs/03_DATA_SOURCE_REGISTRY.md》§3–§4；《docs/04_INGESTION_AND_CURATION_SOP.md》P0/P1）

## 礼貌条款（§8.3，代码级强制于 `base.PoliteSession`）

| 条款 | 实现 |
|---|---|
| 每主机串行 + ≥1.2s 间隔 | 类级节流表（跨实例共享，如 GitHub API 被两个连接器共用时依然生效） |
| User-Agent | `ai-math-recommend-research/0.1 (polite crawler; contact: 3116809059@qq.com)` |
| 超时 | 20s |
| 失败重试 | ≤2 次，指数退避（1.5s → 3.0s）；仅 5xx/429/传输错误重试，其余 4xx 一次即止 |
| 失败处理 | 任何 4xx/5xx 记入 `FetchReport.errors`，不抛崩、不硬编码成功 |
| 单次 run 上限 | 每源最多 `limit` 条（默认 20；smoke 脚本默认 5） |

## 连接器一览

| Connector | 源 | 接入方式 | 限速 | 状态（2026-02 实联调，limit=5） |
|---|---|---|---|---|
| `ArxivConnector` | SRC-0002 arXiv | Atom API `export.arxiv.org/api/query`（cat:math.NT + abs:"open problem"/"conjecture" 两组关键词） | 官方建议 ~1 req/3s，本包 ≥1.2s | **OK 5/5** |
| `FormalConjecturesConnector` | SRC-0008 google-deepmind/formal-conjectures | GitHub API 列目录 + raw 拉 `.lean`；候选目录链：`conjectures`（已 404）→ `FormalConjectures/ErdosProblems`（2026 实测现址） | 未认证 60 req/h，≥1.2s 兜底 | **PARTIAL 5/5**（旧路径 404 如实记录后回退成功） |
| `OpenProblemGardenConnector` | SRC-0009 openproblemgarden.org | `/api`→`/op/` 索引→首页 三级回退，html.parser 解析 `/op/` 链接与 `div.node` 正文 | 普通网页低频，≥1.2s | **PARTIAL 5/5**（站点仍有内容，但见下方风险注记） |
| `ErdosProblemsConnector` | SRC-0010 erdosproblems.com | 先试 `/api/problems`，回退首页 HTML 解析 `/problems/<id>` + 详情页 | 普通网页低频，≥1.2s | **FAILED 0/5（诚实失败）**：站点为纯客户端渲染 SPA，服务端无任何问题数据，`/api/problems` 404 → 按规格返回空列表+错误记录，绝不编造 |
| `OpenAlexConnector` | SRC-0011 api.openalex.org | `/works?search=...&mailto=...&filter=from_publication_date:2024-01-01`；text 由 abstract_inverted_index 重建 | 官方 polite pool 10 req/s，≥1.2s | **OK 5/5** |
| `GithubConnector` | SRC-0019 公共仓库 | 通用 `list_dir(owner,repo,path)` / `fetch_raw(url)`；默认目标为 formal-conjectures 的 ErdosProblems 目录 | 未认证 60 req/h，≥1.2s 兜底 | **OK 5/5** |
| `ZbMathConnector` | SRC-0020 api.zbmath.org | `/v1/document/_search?search_string=<kw>&count=N`；按实测 schema 解析 identifier/title(dict)/contributors/editorial_contributions | 礼貌 ≤1 req/s，≥1.2s | **OK 5/5** |
| `CrossrefConnector` | SRC-0021 api.crossref.org | `/works?query.bibliographic=<kw>&rows=N&mailto=...`；meta 存 is-referenced-by-count 等 | 礼貌池需 mailto，≥1.2s | **OK 5/5** |

**实联调汇总**（`data/raw/_smoke_summary.json`，2026-02）：8 源 35 条快照 —— OK 5 / PARTIAL 2 / FAILED 1；
全部失败均带原因记录，无任何"失败硬编码成成功"。

### 实联调发现（重要，供 P0/P1 人工参考）

1. **SRC-0009 Open Problem Garden 已被 SEO 垃圾污染**：`/api` 与 `/op/` 索引均 404，唯一入口是首页
   "最近更改"列表；实测 5 条中 4 条为 Dragon Ball 游戏攻略类垃圾页（快照已如实入库，文件名即其 slug）。
   P1 候选抽取阶段必须过滤；是否继续启用该源建议提交人工复核。
2. **SRC-0008 仓库已重组**：`conjectures/` 目录不复存在，现址 `FormalConjectures/<Topic>/*.lean`；
   状态注释从 `Status: open` 演化为 theorem 上方 `@[category research open, AMS 5 11]` 属性，解析器两者兼容。
3. **SRC-0010 erdosproblems.com 无法无鉴权采集**：SPA 无 SSR 数据、`/api/problems` 404、详情路由
   `/problems/1` 服务端亦 404。连接器按规格诚实返回空列表+错误；如需该源数据须人工评估替代途径
   （如官方导出/联系站方），不得绕过。
4. **SRC-0020 zbMATH**：部分条目的评论文本被许可系统替换为"contents unavailable"占位说明——
   连接器原样保存（那是源给的全部内容），缺摘要条目只存元数据。

> 未注册在此处的源（含 SRC-0012 MathOverflow 等已启用但 `connector_version: none` 的源）暂无连接器；
> 增补须先在 `data/source_registry` 登记/启用并同步 docs/03。

## 使用

```bash
# 离线单测（不打网络；含节流/重试/解析/注入纪律回归）
python -m pytest tests/unit/test_connectors.py -q

# 实联调 smoke：真实抓取并落盘 RawDocument 快照
python scripts/run_connectors_smoke.py --sources SRC-0002,SRC-0009 --limit 5
python scripts/run_connectors_smoke.py --limit 5        # 全部 8 个源
```

快照落盘：`data/raw/<SRC-id>/<external_id 安全化>.json`（UTF-8，含 `fetched_at` 与 meta），
运行汇总：`data/raw/_smoke_summary.json`（逐源条数 + errors，如实记录失败）。

```python
from ai_math_connectors import CONNECTORS, ArxivConnector

report = ArxivConnector().fetch(limit=20)   # 或 CONNECTORS["SRC-0002"]()
report.count          # 真正抓到的条数
report.errors         # 4xx/5xx/解析失败，绝不静默
report.documents      # list[RawDocument]
```

## 结构

```text
packages/connectors/
├── pyproject.toml            # ai-math-connectors 0.1.0（依赖 httpx）
└── src/ai_math_connectors/
    ├── base.py               # RawDocument / PoliteSession / Connector ABC / FetchReport
    ├── arxiv.py openalex.py crossref.py opg.py
    ├── formal_conjectures.py github.py zbmath.py erdosproblems.py
    └── registry.py           # CONNECTORS（仅 8 个 enabled 源）+ verify_enabled 交叉校验
```

`RawDocument` 字段：`source_id / external_id / url / title / text / fetched_at(ISO) / meta(dict)`。

## 决策记录

- **registry 只含 enabled=true 的 P0 源**（ADR-011：登记≠启用）；`verify_enabled()` 在采集前
  用 `data/source_registry/*.json` 交叉校验，防止代码悄悄多接未批准源。
- **OPG/Erdős 站点结构不稳**：按任务规格，宁可返回空列表 + errors，绝不编造数据
  （tests/unit/test_connectors.py::test_unstable_site_returns_empty_not_fabricated）。
- **fetch 失败语义**：网络不通/限流/4xx/5xx 一律进 `FetchReport.errors` 继续其余条目；
  smoke 脚本按 OK / PARTIAL / FAILED 三态如实汇报。
- **解析器以实测 schema 为准**：zbMATH（title 为 dict、authors 在 contributors 下）、
  OPG（`div.node` 而非 `div#content`）、formal-conjectures（目录重组 + category 属性）
  均以 2026-02 真实响应探测结果适配，离线 fixture 即真实响应片段。
