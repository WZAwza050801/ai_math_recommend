# packages/model_client — LLM 客户端封装（占位）

Phase 2 交付：统一的模型路由、速率控制、成本核算与 Agent trace 记录。
所有 LLM 调用必须记录 model_runs（prompt_version + 输入摘要 + 时间戳），供审计与回放。

- 设计依据：docs/01（架构）、docs/06（契约的 logging_requirements）
- 本目录 Phase 0 为空骨架。
