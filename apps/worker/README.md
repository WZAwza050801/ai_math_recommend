# apps/worker — 采集与加工 Worker（占位）

Phase 2 交付：Connectors 轮询（packages/connectors）、P1–P6 管道执行（TASK-101..601 契约驱动）、
Agent trace 持久化；Phase 5：solver backend 调度（ADR-001/002）。

- 设计依据：docs/04（P0–P10 SOP）、docs/06（任务契约）
- 硬边界：Worker 任何输出只能产生 candidate/normalized/…/scored 状态内容，永远不触碰 published
- 本目录 Phase 0 为空骨架，不含任何实现。
