# ADR-009：Phase 0 标准化的双轨数据契约（JSON Schema 权威 + Pydantic 镜像）

- 状态：Accepted（Phase 0 执行决策）
- 日期：2026-08-28

## 背景

设计基线 §22 Phase 0 要求交付 Schema 与约 30 张金标准卡，但未指定 Phase 0 的载体（文件 vs 数据库）与校验技术栈。Phase 1 才引入 PostgreSQL（ADR-003）。

## 决策

1. Phase 0 以 JSON 文件为数据载体：`data/gold_set/OP-*.json`（卡片）、`data/source_registry/SRC-*.json`（来源注册表）、`data/taxonomies/domains.json`（分类法）。
2. JSON Schema（draft 2020-12）为权威契约：六族 Schema 落盘 `schemas/`，`$id` 形如 `https://ai-math-recommend.dev/schemas/<family>/v1.0.0/schema.json`，跨族 `$ref` 经 referencing.Registry 解析。
3. `packages/domain` 提供 Pydantic 运行时镜像 + 状态机 + 发布门禁，服务 Phase 1 服务层复用；两者不一致时以 JSON Schema 为准并修 Pydantic。
4. 金标准卡一律停留 `lifecycle_state="scored"`、`publishable=false`、`human_verified=false`——Phase 0 无任何已发布内容。
5. 全部卡片由"事实单驱动"的 Agent 流程生成，每张卡必须通过 `scripts/validate_gold_set.py`（Schema + 分类法交叉校验 + 来源注册表交叉校验 + evidence_id 唯一性 + 金标准纪律五项）。

## 理由

文件载体让 Phase 0 成果可 diff、可评审、可版本化；双轨校验在引入数据库前即可机器化执行 §20.5 的验收标准。

## 后果

- Phase 1 迁移到 PostgreSQL 时，JSON 文件成为种子数据；Schema 字段名即列名设计，无转换损耗。
- Pydantic 镜像与 Schema 的等价性由 tests/gold_set 间接保证（全部卡片同时过 Schema 与门禁逻辑）。
- docs/02 文末待裁决问题"状态命名大小写不一致"按本 ADR 裁定：Schema 小写下划线为准（PASCAL_TO_LOWER 映射表见 ai_math_domain/enums.py）。
- docs/02 待裁决"Scored 及更早阶段发现已解决无流转路径"裁定：保守策略——非 Published 状态不得直接进入 Resolved；此类发现走 P7 人工裁决（state_machine.py 注释）。
