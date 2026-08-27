# apps/api — API 服务（占位）

Phase 1 交付：Problem Card CRUD、生命周期状态机迁移端点（packages/domain）、审核队列、版本与审计。
Phase 3 交付：用户偏好、卡池生成（packages/ranking）、抽卡与反馈端点。

- 设计依据：docs/01（系统架构）、docs/04（SOP）
- 硬边界：发布端点必须调用 evaluate_publish_gate；gate-p7 不可绕过（ADR-012）
- 本目录 Phase 0 为空骨架，不含任何实现。
