# ADR-005：不发布伪成功概率

- 状态：Accepted（设计基线 v0.1 §25）
- 日期：2026-08-27（基线）/ 2026-08-28（Phase 0 落地注记）

## 背景

一旦系统给出"某模型解决某问题的概率为 X%"，用户会把它当作客观测量，而实际上不存在按模型与预算分层的真实求解实验数据。

## 决策

系统只输出结构性评估（AI Affordance：维度证据 + 等级 band），不输出任何概率语义的数字。

## 理由

没有真实、按模型与预算分层的求解实验数据。

## 后果

- AI Affordance 术语在产品文案中不得称为"可解概率"（§3.5）。
- TASK-601 契约的 quality_checks 含禁用词扫描（"概率%/probability of solving"）。
- 金标准卡的 ai_affordance_assessment 只含 evidence_for/against/unknowns + feature_values + band。
- 未来若引入概率预测（Phase 5 之后），必须基于 attempts 数据并另立 ADR。
