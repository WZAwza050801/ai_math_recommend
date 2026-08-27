# packages/connectors — 来源采集连接器（占位）

Phase 2 交付：按 Source Registry 逐源实现（arXiv API、OEIS、Open Problem Garden、
formal-conjectures 仓库等）。每个 Connector：

- 只采集 `enabled: true` 的已批准来源（ADR-011）；
- 遵守各源速率限制与礼貌采集要求（§8.3）；
- 输出原始快照（不可变）供 P1 抽取，不做任何语义加工。

- 设计依据：docs/03（数据源注册表）、docs/04（P0/P1）
- 本目录 Phase 0 为空骨架。
