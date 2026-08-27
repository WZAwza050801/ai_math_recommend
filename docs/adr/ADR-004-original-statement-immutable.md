# ADR-004：原始陈述不可覆盖

- 状态：Accepted（设计基线 v0.1 §25）
- 日期：2026-08-27（基线）/ 2026-08-28（Phase 0 落地注记）

## 背景

规范化数学陈述（翻译、量词显式化、符号统一）存在改变数学语义的高风险，且此类错误难以事后发现。

## 决策

原始陈述一经写入不可改写覆盖；系统必须并列保存原始陈述、规范化陈述、通俗导览与规范化差异/语义风险说明。

## 理由

数学规范化存在改变语义的高风险。

## 后果

- `statements.original` 为不可变字段（附 immutable_content_hash 位，Phase 1 由管道计算写入）。
- `statements.normalized.normalization_notes` 与 `semantic_risks` 为必填语义审计轨。
- 所有 Agent 任务契约的 forbidden_actions 均含"不得覆盖不可变字段/删改已有证据"（由 tests/contract 强制）。
- Phase 0 金标准卡全部保留原文（英文原陈述）+ 中文规范化陈述并排。
