# AI Math Problem Draw Agent（AI 数学开放问题抽卡推荐系统）

从权威来源系统化采集、规范化、核验开放数学问题，形成结构化问题卡（Problem Card），
按重要性与 AI 友好性评估、排序，以"抽卡"式受控探索推荐给研究者。

> **当前状态：Phase 0（设计标准化 + 金标准样本）已完成。**
> 30+ 张金标准问题卡全部停留 `scored` 状态等待人工核验；无任何已发布内容。

## 设计基线

`AI_Math_Problem_Draw_Agent_Design_Spec_v0.1 (1).md`（仓库根，不可变基线，2026-08-27）。
拆分后的规范文档见 `docs/00–11_*.md`；关键决策见 `docs/adr/`（ADR-001..012 + BACKLOG）。

## 仓库结构

```text
apps/                # web / api / worker（Phase 1+ 占位）
packages/
  domain/            # Pydantic 镜像 + 生命周期状态机 + 发布门禁（已实现）
  ranking/           # ranking-weights-v0.1 基线排序（已实现）
  agent_contracts/   # TASK-000..TASK-1001 十一份任务契约 YAML（已实现）
  model_client/      # 占位
  connectors/        # 占位
  solver_backends/   # 占位（ADR-001/002：第一版不求解）
schemas/             # 六族 JSON Schema（draft 2020-12，权威契约）
prompts/             # extraction / normalization / status_verification / assessment
data/
  gold_set/          # OP-000001..OP-000030 金标准卡 + MANIFEST.json
  source_registry/   # SRC-0001..0014 种子源（enabled=false 待批准）
  taxonomies/        # domains.json（9 个一级域，ADR-010）
  fixtures/          # FIX-001 残缺卡 / FIX-002 注入样本 / FIX-003 去重样本
docs/                # 00–11 拆分文档 + adr/
tests/               # unit / contract / gold_set（e2e 留待 Phase 2）
scripts/             # validate_gold_set.py
```

## 快速开始

```bash
# 环境：Python ≥3.11；pip install pydantic jsonschema pyyaml pytest referencing

# 校验金标准集（全部卡片必须 PASS）
python scripts/validate_gold_set.py

# 运行测试套件
python -m pytest
```

## 核心纪律（不可违反）

1. **没有证据就没有断言**（§11.2）：任何字段级判断必须绑定 EvidenceItem。
2. **"没有找到证明" ≠ "仍然开放"**（§11.2）：检索不到解答时状态只能是 status_uncertain 及以下档位。
3. **未核验声称不得翻转状态**（§11.2）：预印本/博客/Zenodo 的证明声称一律 unverified，写入 contradicting_evidence 等待人工核验。
4. **原始陈述不可覆盖**（ADR-004）：normalized 与 original 并存，semantic_risks 强制填写。
5. **禁止自动发布**（ADR-012）：发布门禁含 gate-p7 硬性人工批准；LLM 输出永远不能独自把卡片送入 published。
6. **状态机不可绕过**（§24.3）：candidate→…→published 的合法迁移由 packages/domain 强制。
7. **不输出伪成功概率**（ADR-005）：AI 友好性只有维度证据 + 等级，没有"解决概率"。

## 版本化约定

- Schema：`schemas/<family>/v1.0.0/schema.json`（修改即升版本）
- 评分权重：`ranking-weights-v0.1`
- 评估 rubric：`importance-rubric-v0.1` / `ai-affordance-rubric-v0.1`
- 提示词：`extraction-v0.1` / `normalization-v0.1` / `status_verification-v0.1`

## 路线图

Phase 0 ✅（本仓库现状）→ Phase 1 数据库与管理后台 → Phase 2 自动采集与知识加工
→ Phase 3 抽卡前端 → Phase 4 反馈学习 → Phase 5 求解后端（详见 docs/01 与设计基线 §22）。
