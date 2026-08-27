# ADR-012：全部卡片发布前必须人工确认（P7 硬性闸门）

- 状态：Accepted（Phase 0 执行决策；对应基线 §26 开放问题 3）
- 日期：2026-08-28

## 背景

基线 §26.3 问"哪些卡必须人工确认后才对普通用户可见"。§10.2 发布门禁八条件中"未人工确认的内容明确标记"只是标记要求；若仅按字面执行，一张标记完备但从未经专家审阅的卡可以合法进入 Published，与 §24.3"严禁 网页搜索→LLM 打分→自动发布"及 §12 P7 的定位冲突。

## 决策

1. Phase 0 起，任何卡片进入 `published` 前，`audit.human_reviews` 必须至少含一条 `decision="approved"` 的人工审核记录。
2. 该要求以 `gate-p7` 阻塞项实现在 `packages/domain/publish_gate.py`，并有单元测试锁定（tests/unit/test_publish_gate.py::test_gate_p7_requires_approved_human_review）。
3. 金标准集 31 张卡全部 `human_verified=false`、`human_reviews=[]`，因此全部被门禁拦下——这是有意为之的安全状态。

## 理由

对数学内容而言，错误发布（把已解决问题当开放问题推荐）直接摧毁系统可信度；而人工审核 31 张卡的成本可控。宁可全拦，不可漏放。

## 后果

- 未来如需分级可见性（组内预览 vs 公开），须新 ADR 细化"approved"的粒度（如领域专家 vs 值班编辑），但"至少一条 approved"为下限。
- 状态机合法迁移（scored→published）只是必要条件；门禁是充分条件，二者共同生效。
- 自动化流水线永远无法独自把卡片送入 published——这是产品红线（§3.6/§19.1）。
