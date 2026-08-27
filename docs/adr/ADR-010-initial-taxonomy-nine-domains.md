# ADR-010：首批数学大类 taxonomy（9 个一级域）

- 状态：Accepted（Phase 0 执行决策；对应基线 §26 开放问题 1）
- 日期：2026-08-28

## 背景

基线 §26.1 将"第一批五个数学大类的具体 taxonomy"列为进入开发前必须裁决的问题。金标准 30 卡需要覆盖足够的领域广度才能测试跨域推荐与去重。

## 决策

首批一级域定为 9 个（超出基线草案的 5 个，以覆盖金标准卡的实际分布）：

`number-theory`、`analysis`、`algebra`、`algebraic-geometry`、`combinatorics-and-graph-theory`、`geometry`、`topology`、`pde-and-numerics`、`logic-and-tcs`

落盘于 `data/taxonomies/domains.json`，含中文名、描述、topics 词表、problem_types / expected_output_types 词汇表。卡片 `classification.primary_domain` 必须取自该文件（校验器强制）。

## 理由

- 金标准问题池（数论/分析/代数/组合/几何/拓扑/PDE/逻辑与计算复杂性）自然横跨 9 域；人为压缩到 5 域会让多个旗舰问题无类可归。
- 9 域粒度与 arXiv 分类（math.NT/GT/...）大致对齐，便于未来 Connector 映射。

## 后果

- taxonomy 版本化（文件内 `version: 1.0.0`）；任何修改需新版本 + ADR。
- 二级 topics 是开放词表（agent 可提议新增，人工审核后并入）。
- docs/05 中重要性评分的领域归一化（§26.7）以 primary_domain 为归一化单位。
