# 过夜标准化执行日志（Phase 0 + 仓库标准化 + Phase 1–3 第二夜）

- 执行开始：2026-08-28 00:43 (+08:00)
- 依据文档：《AI_Math_Problem_Draw_Agent_Design_Spec_v0.1（设计基线 / 可进入原型开发）》
- 执行模式：过夜自主执行，无人工介入；本日志即 §24.1 要求的任务说明与留痕。

## 任务说明（按 §24.1 模板）

- **需求背景**：设计基线 v0.1 已定稿，需按 §23 建议仓库结构完成标准化落地，并交付 Phase 0（设计与金标准样本）。
- **对应设计章节**：§9（Problem Card Schema）、§10（状态机）、§11（Agent 任务契约）、§12（P0–P10 SOP）、§13（评分排序）、§21.3（金标准数据集）、§23（仓库结构）、§24（开发 Agent 工作方式）、§25（ADR）、§26（首轮开放设计问题）。
- **输入**：设计规范全文（本仓库根目录 `AI_Math_Problem_Draw_Agent_Design_Spec_v0.1 (1).md`，作为不可变基线保留）。
- **允许修改的目录**：全仓库（新建为主）。
- **不得修改的边界**：设计基线文档本身只读；不实现 Phase 1–3 的生产系统（API/Frontend 仅放说明占位）；不自动发布任何问题卡（金标准卡全部停留 `scored` 且 `publishable=false`，发布门禁含 gate-p7 人工批准硬闸，见 ADR-009/ADR-012）。
- **验收标准**：见 goal 与《10_EVALUATION_PLAN》；核心是 30+ 张真实问题卡全部通过 Schema 校验、状态机与发布门禁单元测试全绿、文档十二份齐备。
- **需要运行的测试**：`scripts/validate_gold_set.py`、`pytest`。
- **风险与回滚**：git 全程小步提交；金标准卡的事实内容错误为主要风险，以 §P4 纪律（证据绑定、unknown 不补全、不因未检索到解答而断言开放）控制。
- **文档更新要求**：docs/00–11 + ADR-009~012 随代码同步产出。

## 执行时间线

| 时间 (+08:00) | 事件 |
|---|---|
| 2026-08-28 00:43 | 环境确认（Python 3.13.1 / pydantic 2.13.4 / jsonschema 4.26.0 / pytest 9.1.1），创建执行 goal |
| 2026-08-28 00:47 | 完成 P4 风格状态核验检索（4 轮 web 检索，覆盖 17 个高风险条目） |
| 2026-08-28 00:49 | 仓库脚手架（§23 结构，28 个目录）+ git init |
| 2026-08-28 03:10 | 六族 Schema、taxonomy（9 域）、14 源注册、11 契约、5 提示词、OP-000001 示范卡落盘；校验器 v1（commit 801a668+0b8e339） |
| 2026-08-28 04:30 | docs/00–11 十二份拆分文档完成（3 个子代理并行）；"待裁决问题"随 ADR-009~012 + BACKLOG 闭环 |
| 2026-08-28 05:20 | packages/domain（状态机 12 边 + 发布门禁含 gate-p7）与 packages/ranking（ranking-weights-v0.1）落盘；74 项测试绿；夹具 FIX-001/002/003 |
| 2026-08-28 06:40 | 卡片子代理 α（OP-2..8）/β（OP-9..14）完成，逐张 PASS；抽查 OP-000005/OP-000011 纪律合规（未核验声称未翻转状态） |
| 2026-08-28 07:30 | 全库校验 23/23 PASS（γ 批 OP-15..18、δ 批 OP-23..28 已落盘，余 OP-19..22/29..30 进行中） |
| 2026-08-28 07:45 | ADR-001..008（§25 转录）+ ADR-009..012 + BACKLOG.md；README/AGENTS.md/docker-compose/apps 占位（commit dcbc9f9） |
| 2026-08-28 08:20 | 卡片子代理 γ（OP-15..22）/δ（OP-23..30）完成，逐张 PASS；金标准集 30/30 齐备 |
| 2026-08-28 08:35 | 收尾终跑：build_manifest（30 卡六类样本）→ validate_gold_set **30/30 PASS** → pytest **81 passed**；docs/10 §8.1/8.2/8.3 + §9.4 如实回填 |

## 终跑结果（2026-08-28 08:35）

- `python scripts/validate_gold_set.py`：30 张卡全部 PASS，失败 0。
- `python -m pytest`：81 passed / 0 failed（unit + contract + gold_set；e2e 为 Phase 2 预留）。
- `python scripts/build_manifest.py`：MANIFEST.json 六类样本齐备（参照 10 / 界改进 9 / 未核验声称压力 8 / 高相似不同 7 / 等价网络 3 / 已解决对照 3）。
- 纪律抽检（ captain 复核）：OP-000005（abc，争议不翻转）、OP-000011（Singmaster，无 URL 未核验声称）、OP-000020（Lonely Runner，Zenodo 声称不翻转）、OP-000028（CH，resolved 必有 verified 证据）全部合规。

## 遗留给人工（P0/P7）的事项

1. 14 个种子源的 `enabled:true` 批准（ADR-011；P0 人工门禁）。
2. 30 张金标准卡的专家核验与发布裁决（全部 scored/publishable=false；gate-p7 拦截中）。
3. 各卡"待人工复核"注记（见子代理汇报与各卡 notes/unknowns）：如 OP-000015 的 EV-000015-2 tier 与 SRC-0014 注册等级不一致、OP-000016 Tao 结果覆盖界、OP-000023 的 44.65 型上界、OP-000030 Flyspeck 发表出处等。
4. ADR Backlog（docs/adr/BACKLOG.md）15 项进入 Phase 1 前逐项裁决。

## 第二夜：Phase 1–3 开发（2026-08-28 深夜起，用户授权"能批准的肯定批准"）

| 时间 (+08:00) | 事件 |
|---|---|
| 22:30 | 用户提供平台接入优先级清单（P0/P1/P2/观察源，九大类）+ 一揽子批准 |
| 22:40 | GitHub 私有仓库创建并推送（gh 已登录 WZAwza050801） |
| 23:10 | Source Registry 14→42 源；启用 11 个 P0 免鉴权源；schema v1.1.0（ADR-013） |
| 23:40 | 抽卡前端（apps/web/index.html 单文件）+ 规则式候选 Worker 落盘并提交 |
| 00:00+ | 派发 API 后端子代理 + Connectors 子代理并行开发（进行中） |

### 第二夜账号/凭据现实约束（如实记录）

- 用户提供邮箱 3230101115@zju.edu.cn / 3116809059@qq.com 并授权代办注册；但第三方注册需密码簿与邮箱验证码（Agent 不可读取），自动化注册亦受平台条款限制 → **未代办任何第三方注册**，Semantic Scholar/CORE Key 列入 MORNING_CHECKLIST.md。
- GitHub 仓库经本机既有 gh 凭据创建（私有），未触碰账号设置。

### 第二夜交付总览（最终）

| 阶段 | 交付 | 提交 |
|---|---|---|
| 注册表 | 14→42 源，11 个 P0 启用，schema v1.1.0 | 5a18e13 |
| Phase 3 前端 | apps/web/index.html（抽卡/库/源三视图，三层阅读） | 8cd7023 |
| Phase 2 worker | 规则式候选流水线（不猜领域，Schema 强校验） | 8cd7023 |
| Phase 1 后端 | apps/api（13 文件，22 项 API 测试，发布门禁端到端） | a25ea9b |
| Phase 2 连接器 | 8 个 P0 源礼貌采集（54 项测试，35 条真实快照） | f4a8802 |
| 文档 | ADR-013/014、README、docs/02/03 同步、MORNING_CHECKLIST | 本提交 |

**终验（2026-08-29）**：`python -m pytest` **161 passed**；`validate_gold_set.py` **30/30 PASS**；
端到端：uvicorn 8902/8903 实测 health→import 30→前端托管（draw 按钮+三层标记）→
draw balanced/adventurous 比例正确（weights ranking-weights-v0.1）→ publish OP-000003 **422**（gate-p7 拦截）。

**采集现场情报（如实记录，供人工裁决）**：
- OPG（SRC-0009）：/api 与 /op/ 均 404；索引被 SEO 垃圾污染（抽样 5 条中 4 条游戏攻略）；
- erdosproblems（SRC-0010）：纯 SPA 不可采集（诚实失败 0/5）；
- formal-conjectures（SRC-0008）：仓库已重组（conjectures/→FormalConjectures/ErdosProblems），连接器已自适应；
- worker 规则式候选因"领域未映射即跳过"纪律，本夜 0 产出（正确行为；LLM 抽取接入后解锁）。

## 状态核验摘记（证据详见各卡 `open_status.supporting_evidence`）

- abc 猜想：Mochizuki IUT 证明仍存争议；2026-07 形式化项目 LANA 失败（naukas.com 报道）→ `status_uncertain`。
- Casas–Alvero 猜想：arXiv:2501.09272 声称证明（v2），无期刊接受或社群核验证据 → `status_uncertain`（未验证声称不翻转状态）。
- Singmaster 猜想：Zenodo 存在声称解决的预印本（2025），未经核验 → 保持开放，`likely_open`。
- Rota 基猜想：Montgomery–Sauermann 2025-08 重大进展（arXiv:2508.05601 等），未完全解决 → 开放。
- 孪生素数：最佳无条件间隙界仍为 246（Polymath8）→ 开放。
- 黎曼假设 / Goldbach / 3x+1 / Navier–Stokes / P vs NP / Schanuel：截至 2026-08 无可信解决证据（Zenodo 上多处声称均为未核验预印本）→ 开放。
- 已解决对照卡：Erdős 偏差问题（Tao 2015）、开普勒猜想（Hales 1998/Flyspeck 2014）、连续统假设（ZFC 独立性，Gödel 1940 / Cohen 1963）。

## 第三工作日（2026-08-29 白天）：方向定调 + 标准化扩展

### 主人定调（关键决策输入）
1. 主人身份定位：数据科学家；研究重点 = ①排序算法科学性 ②数据库技术；
2. 明确质疑当前排序"不太科学"（有效质疑：当前 I/A 为单标注员 LLM 先验、9 维等权无依据、
   √(I·A) 无验证、P/C 硬编码常数、引用数据未入管道）——Wave B 数据科学主线由此立题；
3. 求解系统不做，但"AI 上手做"（attempt 记录）要做（Wave E）；
4. 商业数据库（MathSciNet/Scopus）主人去问学院老师（人工轨道，不阻塞主线）；
5. 未来一切开放数据集统一走标准化接入，不做一次性脚本。

### 本日产出
| 产出 | 提交 | 说明 |
|---|---|---|
| ROADMAP_PHASE1_PLUS.md | f9d99de | 五波次工程规划（A 智能核心→B 数据科学→C 数据库深化→D agent 编队→E attempt）+ 速赢清单 + 研究空白 9 项 |
| SRC-0010 起死回生 | f9d99de | erdosproblems.com 为 SPA，但数据真身 = teorth/erdosproblems 开源仓库（Tao 维护，Apache-2.0，data/problems.yaml，1217 题带状态/悬赏/Lean 形式化标签）→ 注册表升级 git/A 级 |
| DATASET_INGESTION_SOP.md + TASK-002 契约 | a72957a | 数据集批量接入标准化：八步流水线、全局状态映射保守表（proved≠直接 resolved，人工把关）、D1–D15 四梯队积压清单、实例模板、四道准入检查；契约测试同步（161 passed） |

### 系统当前排名方法记录（供审查）
公式 S_core=√(I·A)、S_user=S_core×(0.7+0.3P)×(0.6+0.4C)，P=50/C=75 常数；
I/A 各 9 子维等权均值，金标准卡上为 LLM 量表先验（已知局限 = Wave B 重构目标）。
当前 Top5：哥德巴赫 59.1、平面色数 56.7、孪生素数 56.5、Frankl 并闭集 55.0、黎曼 52.6。
分歧记录：按"机器可攻性"重排，五维接吻数/平面色数/Erdős–Straus 应居首——
构念（价值 vs 可攻性）未分离的直接证据，亦是 B4 排序 v0.2 的动机。

### 新 session / 审查入口
- 工程全景：README.md → docs/ROADMAP_PHASE1_PLUS.md → docs/DATASET_INGESTION_SOP.md
- 决策链：docs/adr/（ADR-001..014 + BACKLOG）；纪律：AGENTS.md（硬边界 + 红线 + 验证命令）
- 人工待办：MORNING_CHECKLIST.md；完整时间线：本文件
- 下一步施工首选：速赢 Q1（erdős YAML 导入 = SOP D1 实例，首验整条流水线）
- 验证基线：`python -m pytest` 161 passed；`python scripts/validate_gold_set.py` 30/30 PASS
