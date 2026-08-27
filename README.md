# AI Math Problem Draw Agent（AI 数学开放问题抽卡推荐系统）

从权威来源系统化采集、规范化、核验开放数学问题，形成结构化问题卡（Problem Card），
按重要性与 AI 友好性评估、排序，以"抽卡"式受控探索推荐给研究者。

> **当前状态：Phase 0 完成；Phase 1–3 原型已落地（2026-08-29 过夜执行，ADR-013/014）。**
> 管理后端（FastAPI + SQLite/PostgreSQL）、抽卡前端、礼貌采集连接器与规则式候选流水线可用；
> 30 张金标准卡全部停留 `scored` 状态等待人工核验；无任何已发布内容。

## 设计基线

`AI_Math_Problem_Draw_Agent_Design_Spec_v0.1 (1).md`（仓库根，不可变基线，2026-08-27）。
拆分后的规范文档见 `docs/00–11_*.md`；关键决策见 `docs/adr/`（ADR-001..014 + BACKLOG）。

## 仓库结构

```text
apps/
  api/               # Phase 1 管理后端（FastAPI：CRUD/状态机/审核/门禁/抽卡）
  web/               # Phase 3 抽卡前端（单文件 index.html，由 API 直接托管）
  worker/            # Phase 2 规则式候选流水线（run_once.py）
packages/
  domain/            # Pydantic 镜像 + 生命周期状态机 + 发布门禁
  ranking/           # ranking-weights-v0.1 基线排序
  agent_contracts/   # TASK-000..TASK-1001 十一份任务契约 YAML
  connectors/        # Phase 2 礼貌采集连接器（8 个 P0 源，实测 5 OK/2 部分/1 失败）
  model_client/      # 占位（LLM 接入后替换规则式抽取）
  solver_backends/   # 占位（ADR-001/002：第一版不求解）
schemas/             # 六族 JSON Schema（draft 2020-12；source_registry 已升 v1.1.0）
prompts/             # extraction / normalization / status_verification / assessment
data/
  gold_set/          # OP-000001..OP-000030 金标准卡 + MANIFEST.json
  source_registry/   # SRC-0001..0042（42 源，11 个 P0 已启用，ADR-013）
  candidates/        # 流水线候选卡（OP-8xxxxx，规则式生成）
  raw/               # 连接器快照 + _catalog.json 文献索引
  taxonomies/        # domains.json（9 个一级域，ADR-010）
  fixtures/          # FIX-001 残缺卡 / FIX-002 注入样本 / FIX-003 去重样本
docs/                # 00–11 拆分文档 + adr/
tests/               # unit / contract / gold_set（161 项）
scripts/             # validate_gold_set.py / expand_source_registry.py / run_connectors_smoke.py
MORNING_CHECKLIST.md # 留给项目主人的待办（核验/Key 申请/裁决）
```

## 快速开始

```bash
# 环境：Python ≥3.11；pip install pydantic jsonschema pyyaml pytest referencing \
#        fastapi uvicorn sqlalchemy httpx

# 1) 启动管理后端 + 抽卡前端（开发模式，SQLite）
python -m uvicorn app.main:app --port 8901 --app-dir apps/api
#    浏览器打开 http://127.0.0.1:8901/ → 首次先执行导入：
curl -X POST http://127.0.0.1:8901/api/admin/import_gold_set
#    生产：设置 DATABASE_URL=postgresql+psycopg://…（ADR-014）

# 2) 采集（礼貌限速，P0 源真实抓取）
python scripts/run_connectors_smoke.py --limit 5

# 3) 规则式候选生成（快照 → Schema 校验过的 candidate 卡）
python apps/worker/run_once.py

# 4) 校验金标准集与全量测试
python scripts/validate_gold_set.py
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
