# 03 · 外部数据源与 Source Registry

> 文档版本：v1.0.0  
> 文档状态：基线拆分稿（源：设计规范 v0.1 §8）  
> 更新日期：2026-08-28  
> 上游基线：《AI_Math_Problem_Draw_Agent_Design_Spec_v0.1 (1).md》（下称"设计规范"，只读；本文为其忠实拆分稿，不新增承诺、不改变任何决策）  
> 关联文档：《docs/04_INGESTION_AND_CURATION_SOP.md》（数据源注册 P0 与采集流水线）、《docs/02_DOMAIN_MODEL_AND_SCHEMA.md》（证据条目引用数据源分级与 `SRC-xxxx`）

---

## 1. 数据源分级（设计规范 §8.1）

| 等级 | 来源类型 | 示例 | 默认可信度 |
|---|---|---|---|
| A | 结构化、人工维护的问题库 | Formal Conjectures、Open Problem Garden | 高 |
| B | 专题问题集、专著、研讨会问题列表 | 专题 Problem List、学者主页 | 中高 |
| C | 论文正文中的猜想与开放问题 | arXiv、期刊论文 | 中 |
| D | 社区问答、博客、非正式讨论 | MathOverflow、研究博客 | 待核验 |

可参考的数据接口：

- OpenAlex API：<https://help.openalex.org/api/>
- arXiv API：<https://info.arxiv.org/help/api/user-manual.html>
- Stack Exchange API：<https://api.stackexchange.com/>
- Formal Conjectures：<https://github.com/google-deepmind/formal-conjectures>
- Open Problem Garden：<https://www.openproblemgarden.org/>

---

## 2. Source Registry（设计规范 §8.2）

每个数据源必须先注册，再允许采集。登记条目完整 YAML 示例（原样保留）：

```yaml
source_id: SRC-0001
name: Formal Conjectures
source_type: structured_repository
base_url: https://github.com/google-deepmind/formal-conjectures
access_method: git
license: Apache-2.0
attribution_required: true
refresh_policy: weekly
trust_tier: A
connector_version: 1.0.0
content_formats:
  - lean
  - markdown
allowed_usage:
  - metadata
  - statement
  - source_link
last_successful_sync:
owner:
notes:
```

字段与流水线的对应：`trust_tier` 取值对应 §1 分级；`refresh_policy` 服务于数据源同步安排；登记与启用的人工批准步骤见 P0（设计规范 §12，见《docs/04_INGESTION_AND_CURATION_SOP.md》§2）。

示例字段逐项说明（均为设计规范 §8.2 既有字段的注释，不含新决策）：

| 字段 | 说明 |
|---|---|
| `source_id` | 数据源稳定 ID，格式 `SRC-####` |
| `name` | 数据源名称 |
| `source_type` | 来源类型（结构化仓库、问题列表、社区问答等，见 §4.1） |
| `base_url` | 稳定基础 URL（P0 第 1 步确认） |
| `access_method` | Connector 访问方式（git / API / 网页 / PDF / 人工） |
| `license` / `attribution_required` | 许可与署名要求（P0 第 2 步确认；许可不允许为硬失败） |
| `refresh_policy` | 刷新策略 |
| `trust_tier` | 信任等级，对应 §1 分级 |
| `connector_version` | Connector 版本，便于追溯采集行为（§3 第 3 条） |
| `content_formats` | 该源产出的内容格式 |
| `allowed_usage` | 允许的使用范围（元数据、陈述、来源链接等） |
| `last_successful_sync` | 上次成功同步日期 |
| `owner` / `notes` | 负责人与备注 |

---

## 3. 采集要求（设计规范 §8.3，全部保留）

- 遵守 API 速率限制、许可与署名要求；
- 保存原始响应或内容指纹；
- 记录采集时间和 Connector 版本；
- 数据源删除内容时不得立即物理删除本地证据；
- 外部网页内容一律视为不可信输入；
- 外部文本不得改变 Agent 系统指令、工具权限或发布策略。

---

## 4. 本仓库落地

（本节为本仓库补充，只描述既有实现与基线的对应关系，不改变上方基线语义。）

### 4.1 存放位置与机器校验

- 数据源登记条目以 JSON 存放于 `data/source_registry/`，每条须符合 `schemas/source_registry/schema.json`（`$id: https://ai-math-recommend.dev/schemas/source_registry/v1.0.0/schema.json`）。
- 该 Schema 与本仓库其余五族 Schema 同构：均为 JSON Schema draft 2020-12，`$id` 均采用 `https://ai-math-recommend.dev/schemas/<族名>/v1.0.0/schema.json` 形式（六族清单见《docs/02_DOMAIN_MODEL_AND_SCHEMA.md》§3.2）。
- 条目必填字段：`source_id`（格式 `SRC-####`）、`name`、`source_type`、`base_url`、`access_method`（`git / http_api / web_page / pdf / manual`）、`license`、`attribution_required`、`refresh_policy`（`weekly / monthly / quarterly / manual / static`）、`trust_tier`（`A / B / C / D / internal`）、`connector_version`（无 Connector 时为 `none`）、`content_formats`（`json / yaml / html / latex / markdown / pdf / lean / bibtex`）、`allowed_usage`（`metadata / statement / source_link / full_text_index / citation_metrics`）、`enabled`。
- `enabled: true` 表示该源已通过人工批准启用（P0 第 8 步）；未启用来源不得采集。
- Schema 明确约束：未登记来源的内容不得进入任何问题卡证据。
- `source_type` 枚举：`structured_repository / problem_list / prize_problem_page / preprint_server / journal / scholarly_graph / community_qa / blog / encyclopedia / internal_material`。与 §1 分级表的对应：A 级示例多为 `structured_repository`，B 级对应 `problem_list` 等，C 级对应 `preprint_server / journal`，D 级对应 `community_qa / blog`；具体归类由 P0 第 4 步指定信任等级时一并确定。
- `last_successful_sync` 为 `null` 表示从未同步；`rate_limit_notes` 承载 §3 的速率限制与礼貌采集要求。
- Connector 实现位置为 `packages/connectors/`（当前为空目录骨架）。

登记条目在证据链中的位置：证据条目通过 `tier` 字段携带来源分级、通过 `source_id` 字段引用登记条目 `SRC-xxxx`（见《docs/02_DOMAIN_MODEL_AND_SCHEMA.md》§3.3）；结合 Schema"未登记来源的内容不得进入任何问题卡证据"的约束，登记是采集与用证的前置条件，对应 §2"先注册，再采集"。

### 4.2 Phase 0 登记现状（2026-08-28 过夜执行后更新）

`data/source_registry/` 已登记 **42 个源**（SRC-0001..SRC-0042，逐条符合 source_registry Schema v1.1.0）。其中 **11 个 P0 免鉴权源已启用**（2026-08-28 用户一揽子批准，ADR-013）：arXiv、formal-conjectures、Open Problem Garden、erdosproblems.com、OpenAlex、MathOverflow、AIM Problem Lists、AIM Workshop、GitHub 公共 API、zbMATH Open、Crossref。2026-08-28 实测注记：OPG 索引被 SEO 垃圾污染（待人工裁决去留）；erdosproblems.com 为纯 SPA 暂不可采集（诚实失败，详见注册表 notes 与 `data/raw/_smoke_summary.json`）。原 14 源种子格局（ADR-011 时期）如下表留存：

| 分级 | 已登记条目 |
|---|---|
| A | SRC-0001 Clay 千禧问题 · SRC-0008 formal-conjectures 仓库 · SRC-0009 Open Problem Garden |
| B | SRC-0010 erdosproblems.com · SRC-0011 OpenAlex · SRC-0014 学术期刊 |
| C | SRC-0002 arXiv · SRC-0005 OEIS |
| D | SRC-0003 Tao 博客 · SRC-0004 Polymath wiki · SRC-0006 Wikipedia · SRC-0007 Zenodo（限定"仅监测未核验声称"）· SRC-0012 MathOverflow · SRC-0013 Naukas |

登记决策与理由见 `docs/adr/ADR-011-first-14-seed-sources.md`。**全部条目 `enabled: false`**：登记≠启用，启用须 P0 人工逐源批准（第 8 步）。因此当前仍无任何来源被授权采集；金标准卡对上述来源的引用属于"登记源引用"，不触发采集。

---

## 5. 待裁决问题

以下问题在拆分时发现；其中第 1 项已由 ADR-011 裁决，第 2/3 项转 ADR Backlog（`docs/adr/BACKLOG.md` B-11）：

1. ~~种子数据源尚未登记~~ → **已裁决（ADR-011）**：14 个种子源登记完毕；~~~~ **P0 批准已裁决（ADR-013，2026-08-28）**：用户按优先级清单一揽子批准，11 个 P0 免鉴权源 `enabled:true`，需 Key 的源（Semantic Scholar、CORE）保持禁用待凭据；其余 P1/P2/观察源待第二批；批准流程（顺序/负责人/批准人）留待人工执行。
2. `internal` 信任等级空白：仓库 Schema 的 `trust_tier` 允许 `internal`（课题组内部材料，与 evidence 条目 `tier` 枚举一致），而设计规范 §8.1 分级表仅定义 A–D 四级。**Phase 0 裁定**（并入 ADR-011 后果）：`internal` 仅用于系统内部派生数据（computed_metric 类），不用于外部来源；本批 14 源未使用。
3. "仅用于监测"如何表达：Zenodo 的"仅监测未核验声称"限制暂以条目 `notes` + `usage_restrictions` 文本承载；`allowed_usage` 枚举扩展（如 `unverified_claim_monitoring`）记入 Backlog B-11，Phase 1 裁决。
