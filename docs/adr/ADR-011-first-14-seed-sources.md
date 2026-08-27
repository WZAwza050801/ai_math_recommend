# ADR-011：首批数据源登记（14 个种子源，全部待人工批准启用）

- 状态：Accepted（Phase 0 执行决策；对应基线 §26 开放问题 2）
- 日期：2026-08-28

## 背景

基线 §8 定义了 A–D 信任分级与 Source Registry，§26.2 要求裁决每领域首批权威源。P0（TASK-000 source_registration）是硬性人工门禁：登记 = 人工决策。

## 决策

登记 14 个种子源（SRC-0001..SRC-0014），覆盖基线 §8.1 全部分级示例：

| 分级 | 来源 |
|---|---|
| A | Clay 千禧问题（SRC-0001）、formal-conjectures 仓库（SRC-0008）、Open Problem Garden（SRC-0009） |
| B | OpenAlex（SRC-0011）、学术期刊（SRC-0014）、erdosproblems.com（SRC-0010） |
| C | arXiv（SRC-0002）、OEIS（SRC-0005） |
| D | Tao 博客（SRC-0003）、Polymath wiki（SRC-0004）、Wikipedia（SRC-0006）、Zenodo（SRC-0007）、MathOverflow（SRC-0012）、Naukas（SRC-0013） |

全部条目 `enabled: false`——本 ADR 只完成"候选登记"，不构成启用批准；启用须 P0 人工逐源批准。

## 理由

与 §8.1 示例清单一致，信任分级覆盖 A–D 全谱，可支撑金标准卡的全部证据来源；`enabled:false` 保持"登记≠批准"的 P0 语义。

## 后果

- 卡片 evidence.source_id 必须指向已登记源（校验器强制）。
- docs/03 待裁决问题"trust_tier: internal 超出 A–D"裁定：internal 仅保留给系统内部派生数据（computed_metric 类证据），不用于外部来源；本批 14 源未使用。
- docs/03 待裁决"Zenodo 仅监测限制无法在 allowed_usage 表达"裁定：暂以 `notes` + `usage_restrictions` 文本承载，枚举扩展留给 Phase 1（记入 docs/adr/BACKLOG.md）。
- 任何金标准卡引用 D 级源未核验声称时，一律 verification_status=unverified 且不翻转状态（§11.2）。
