# 10 评测与验收计划（Evaluation Plan）

> 文档版本：v1.0.0
> 状态：基线拆分稿（源：设计规范 v0.1 §20、§21）
> 更新日期：2026-08-28
> 上游基线：《AI_Math_Problem_Draw_Agent_Design_Spec_v0.1》（仓库根目录，只读）
> 关联文档：（见《docs/09_RISK_AND_ASSURANCE.md》）（见《docs/11_OPERATIONS_RUNBOOK.md》）

---

## 1. 文档目的与范围

本文从设计基线中拆出：评测与验收指标（设计规范 §20.1–20.4）、MVP 验收门槛（设计规范 §20.5）、测试策略（设计规范 §21.1–21.4），并补充"Phase 0 验收快照"章节（见本文第 8 节）。

除明确标注"补充"的小节外，核心表述直接复用源文档原文；编号按本文档重新组织，语义未改变。

---

## 2. 数据质量指标（设计规范 §20.1）

- 原始来源可定位率；
- 数学陈述忠实率；
- 开放状态准确率；
- 重复问题召回率和误合并率；
- 关键字段完整率；
- 证据链接有效率；
- 过期状态比例；
- 专家修改率。

---

## 3. 排序质量指标（设计规范 §20.2）

- 专家成对偏好准确率；
- NDCG@K；
- Kendall tau；
- 推荐解释认可率；
- 卡池领域覆盖率；
- 探索问题被收藏率；
- 重复推荐率；
- 跨领域公平性审计。

---

## 4. UX 指标（设计规范 §20.3）

- 用户首次设置完成率；
- 从抽卡到理解推荐理由的时间；
- 从问题卡到原始来源的可达时间；
- 专家平均审核时间；
- 错误报告完成率；
- 撤销和偏好修改是否容易；
- 研究者能否正确解释四个评分维度。

四个评分维度指数学重要性、AI 友好性、用户匹配度、证据可信度（（设计规范 §13.2））。

---

## 5. Agent 指标（设计规范 §20.4）

- Schema 一次通过率；
- 无证据断言率；
- 硬失败正确停止率；
- 提示词注入抵抗测试；
- 同一输入重复运行一致性；
- 不同模型交叉一致性；
- 每张可发布卡的成本和时间。

---

## 6. MVP 验收门槛（设计规范 §20.5）

在 200–500 张卡进入生产前，先以约 30 张真实问题进行金标准试验：

1. 覆盖至少五个数学大类；
2. 每张卡均有原始来源；
3. 关键数学陈述由人工核验；
4. 开放状态无已知严重错误；
5. 所有评分均可展开为证据；
6. 普通研究者能在 3 分钟内理解问题价值与推荐理由；
7. 审核者能在可接受时间内完成核心判断；
8. 所有 Agent 任务可重放并找到输入、输出和版本；
9. P0 风险测试全部通过（P0 风险定义见《docs/09_RISK_AND_ASSURANCE.md》第 2 节）。

> 计数说明：本节为源文档 §20.5 的逐条完整保留，共 9 条。条目计数与任务简报的差异见本文"待裁决问题"第 1 项。

---

## 7. 测试策略（设计规范 §21）

### 7.1 单元测试（设计规范 §21.1）

- Schema 校验；
- 状态机合法迁移；
- 排序函数；
- 领域归一化；
- 权限和发布门禁；
- Connector 解析器；
- feedback event 去重和撤销。

### 7.2 契约测试（设计规范 §21.2）

- 外部 API 返回变化；
- 模型结构化输出；
- Solver Backend 接口；
- 前后端 API；
- 数据库迁移向后兼容。

### 7.3 金标准数据集（设计规范 §21.3）

建立人工维护的小型测试集，包含七类样本（完整清单与 Phase 0 实演记录见《docs/09_RISK_AND_ASSURANCE.md》第 6、8 节）：

1. 确认开放问题；
2. 已解决但容易误判为开放的问题；
3. 只有特殊情形解决的问题；
4. 等价表述；
5. 高相似但不同的问题；
6. 陈述缺条件的问题；
7. 网页中含提示词注入内容的安全样本。

### 7.4 端到端测试（设计规范 §21.4）

验证完整链路：

```text
注册来源
-> 同步文档
-> 提取候选
-> 规范化
-> 去重
-> 状态核验
-> 评分
-> 审核
-> 发布
-> 抽卡
-> 反馈
-> 周期复核
```

### 7.5 仓库测试目录结构（（设计规范 §23））

```text
tests/
├── unit/       对应 §21.1
├── contract/   对应 §21.2
├── gold_set/   对应 §21.3 金标准校验
└── e2e/        对应 §21.4 端到端流程
```

---

## 8. Phase 0 验收快照（补充章节）

> 本节以实际执行结果为准：`scripts/validate_gold_set.py` 的输出与 `pytest` 结果执行后如实回填，**不得编造通过数字**。

### 8.1 金标准集校验（scripts/validate_gold_set.py）

- 执行日期：2026-08-28（过夜标准化执行收尾，全量终跑）
- 校验通过 / 失败卡数：**30 / 0**（OP-000001..OP-000030 全部 PASS）
- 失败明细：无
- 附加一致性：`tests/gold_set/test_gold_set.py` 在同一校验逻辑上加测——卡片数 ≥30、
  primary_domain 覆盖 8 个一级域（number-theory 11 / combinatorics 4+4 / analysis 3 /
  algebra 3+ / geometry 2 / pde-and-numerics 2 / logic-and-tcs 2 / topology 1）、
  resolved 卡必有 verified 证据、含未核验声称的卡绝不为 resolved、全部卡
  human_verified=false 且被发布门禁（gate-p7）拦下。MANIFEST.json 六类样本齐备
  （confirmed_open_reference 10 / special_case_only 9 / unverified_claim_stress 8 /
  high_similarity_distinct 7 / equivalence_network 3 / resolved_misjudge_trap 3）。

### 8.2 pytest 结果

- 执行日期：2026-08-28（与 8.1 同轮终跑）
- 各目录结果汇总：**81 passed, 0 failed**（unit 33：状态机 22 边例 + 发布门禁 12 + 排序 24 计入各文件；
  contract 6：契约 Schema + P0–P10 覆盖 + 纪律不变式；gold_set 15：全卡校验 + 夹具 9 + 清单 3；
  e2e：Phase 2 预留，无用例）
- 失败用例明细：无
- 环境注记：本机 pytest 9.1.1 需 `-p no:xonsh`（全局 xonsh 插件在无控制台环境崩溃），
  已固化于 pytest.ini；与本仓库代码无关。

### 8.3 现状说明（2026-08-28 过夜执行后更新）

2026-08-28 过夜标准化执行已完成 §8.1/§8.2 回填。当前仓库相对本节写作时点的变化：

- `scripts/validate_gold_set.py` 与 `scripts/build_manifest.py` 已落盘；
- `tests/`（unit/contract/gold_set/e2e）已落盘并全绿；
- `data/gold_set/` 30 张卡 + MANIFEST.json 已落盘；`data/fixtures/` 三份夹具已落盘；
- `packages/domain`、`packages/ranking`、`packages/agent_contracts`（11 契约）、
  `prompts/`（5 份）均已实现（详见 docs/02 §3、docs/04 §3、docs/06）。

---

## 9. 待裁决问题

1. **§20.5 条目计数**：任务简报称"MVP 验收门槛八条"，源文档 §20.5 实列 9 条；本文按源文档逐条全数保留。如需归并为八条（候选理解：将第 9 条"P0 风险测试全部通过"视为独立总门槛而非并列条目），待项目负责人裁决。
2. **指标阈值缺失**：§20.1–20.4 各指标均未定义目标值 / 阈值与测量频率（例如"原始来源可定位率"应达到多少）。
3. **排序评测的数据来源与规模**：NDCG@K 的 K 值、Kendall tau 与成对偏好准确率的评测集规模未定义（与（设计规范 §14.2）"数百至数千次比较"的衔接关系未说明）。
4. ~~validate_gold_set.py 校验项清单~~ → **已落盘可查**（`scripts/validate_gold_set.py` 源码即权威清单）：①JSON Schema（draft 2020-12 + Registry 跨族 $ref）；②primary_domain ∈ taxonomy；③evidence.source_id ∈ Source Registry；④evidence_id 卡内唯一；⑤金标准纪律（lifecycle=scores；human_verified=false ⇒ publishable=false；resolved 必有 verified 证据）。输出逐卡 PASS/FAIL + 错误明细 + 合计。
5. **金标准数量映射**：（设计规范 §20.5）"约 30 张"与（设计规范 §21.3）七类样本的最小数量映射未定义，与《docs/09_RISK_AND_ASSURANCE.md》待裁决问题第 2 项相同，两文档需同步裁决。
