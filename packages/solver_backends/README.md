# packages/solver_backends — 求解后端接口（占位）

Phase 5 交付：`SolverBackend` 抽象接口与适配器（DeepSeek Harness 或其他）。
接口契约：problem + profile + budget 输入 → attempts 结构化输出（schemas/attempt v1.0.0）。

- 硬边界（ADR-001/002）：第一版不求解；核心系统不依赖任何 Harness；
  求解结果永远分级（成功/失败/部分）且不得自动写回问题卡——须经 P7 人工核验。
- 本目录 Phase 0 为空骨架。
