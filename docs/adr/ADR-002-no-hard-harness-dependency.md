# ADR-002：核心系统不依赖 DeepSeek Harness

- 状态：Accepted（设计基线 v0.1 §25）
- 日期：2026-08-27（基线）/ 2026-08-28（Phase 0 落地注记）

## 背景

DeepSeek Harness（或任何执行框架）更新频繁、能力随模型变化，且绑定特定厂商。推荐知识库的实体、证据与状态需要长期稳定。

## 决策

核心系统（数据模型、评估、排序、审核）不依赖任何 Harness；Harness 只通过 `packages/solver_backends` 的 `SolverBackend` 抽象接口在未来接入。

## 理由

推荐知识库必须稳定，求解执行框架应可替换。

## 后果

- Phase 1–4 的任何组件不得 import harness 内部对象作为领域模型（§24.3 同禁）。
- 未来接入时按 §17.3：problem/profile/budget 输入 → attempts 表输出，外部运行记录必须经适配器转换。
- 本仓库未创建任何 harness 依赖；`packages/solver_backends/` 保留为空目录 + README 占位。
