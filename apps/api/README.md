# apps/api — 管理后端 API（Phase 1）

FastAPI 管理后台：问题卡关系主存（ADR-003）、不可变版本审计（ADR-004）、
生命周期状态机与审核队列、**发布门禁（ADR-012，gate-p7 不可绕过）**、
基线抽卡（ADR-007 / ranking-weights-v0.1）、来源注册表只读查询。

- 设计依据：docs/01（系统架构）、docs/04（SOP）、docs/05（排序）、docs/11（运维）
- 复用实现（只调用，不重写）：`packages/domain`（状态机 + 发布门禁）、
  `packages/ranking`（user_score / band_from_score / pool_mix_for_mode）、
  `schemas/problem_card`（JSON Schema 权威契约，经 jsonschema+referencing 校验）

## 启动

```bash
# 开发模式（workdir = apps/api），缺省 SQLite ./aimath.db
python -m uvicorn app.main:app --port 8901

# 生产 / CI：用环境变量切 PostgreSQL（ADR-014）
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/aimath
python -m uvicorn app.main:app --port 8901
```

- 交互式文档：`/docs`（Swagger UI）、`/redoc`
- 首次启动自动建表（`Base.metadata.create_all`）；Phase 1 无迁移框架，
  生产 PostgreSQL 的迁移策略见 ADR-014「后果」一节。
- `GET /` 返回 `apps/web/index.html`（前端未挂载时返回占位说明页）。

## 数据库

| 模式 | 连接串 | 说明 |
|---|---|---|
| 开发（缺省） | `sqlite:///./aimath.db` | Docker 不可用场景；相对 uvicorn 工作目录生成文件库 |
| 生产 | 环境变量 `DATABASE_URL` | 建议 `postgresql+psycopg://...`；ADR-003 关系主存原则不变 |

- `cards` 表：`card_json` 列保存完整问题卡 JSON，其余列为查询投影
  （title / primary_domain / open_status / lifecycle_state / publishable /
  importance_band / affordance_band / version）。
- `card_versions` 表：**每次内容修改追加一行完整快照，只增不删改**（ADR-004）。
  建卡、导入、生命周期迁移、审核追加、发布各产生一个版本。
- `aimath.db` 已被 `apps/api/.gitignore` 与根 `.gitignore`（`*.db`）排除，严禁提交。

## 端点一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | `{status, db, cards}`；db 探活 + 卡片计数 |
| POST | `/api/admin/import_gold_set?force=false` | 扫描 `data/gold_set/OP-*.json` 幂等 upsert，返回 `{imported, skipped}`；**导入后保持 scored，绝不自动发布**；force=true 覆盖重导并追加版本 |
| GET | `/api/cards` | `?status=&domain=&lifecycle=&q=&page=&page_size=`；q 匹配 title/卡内 JSON（LIKE）；`{total, items[8字段]}` |
| POST | `/api/cards` | body=完整问题卡 JSON；过 problem_card Schema（422 带错误明细）；**强制 lifecycle_state=candidate**；已存在 409；写入即追加 v1 快照 |
| GET | `/api/cards/{problem_id}` | 完整卡 JSON（404 处理） |
| GET | `/api/cards/{problem_id}/versions` | 版本轨迹 `{total, items:[{version, changed_by, reason, created_at}]}`（快照正文不入响应） |
| POST | `/api/cards/{problem_id}/lifecycle` | body `{target}`；assert_transition 校验（非法→409）；**target=published→400**（发布必须走 /publish）；成功后同步卡 JSON + 版本快照 |
| POST | `/api/cards/{problem_id}/reviews` | body `{reviewer, decision: approved\|needs_changes\|rejected, notes}`；追加 `audit.human_reviews`（只增不删）+ 快照；**reviewer 必须为 `human:<名字>`**（agent: 前缀 422 拒绝，ADR-012） |
| GET | `/api/cards/{problem_id}/gate` | `evaluate_publish_gate` 结果 `{publishable, blockers}` |
| POST | `/api/cards/{problem_id}/publish` | **全系统唯一 published 路径**：先 assert_transition(scored→published)（非 scored→409），再评估门禁；有 blocker→`422 {publishable:false, blockers:[...]}`；全绿→published + publishable=true + 快照，返回完整卡 |
| GET | `/api/draw` | `?mode=balanced\|steady\|adventurous&n=&domain=`；从 scored/published 卡抽样；按 `pool_mix_for_mode` 拆 relevance/adjacent/distant；relevance 按 user_score 降序（I/A 取卡内 feature 均值或缺省 50，P=50，C=75）；响应 `{mode, weights_version, draws:[{problem_id,title,one_sentence,primary_domain,open_status,importance_band,affordance_band,radius,score,score_band}]}`；score 保留 1 位小数，**仅供排序调试**，用户界面只展示 score_band（§13.2） |
| GET | `/api/sources` | `?enabled=true\|false\|all`；直读 `data/source_registry/*.json`，按 priority_tier（P0→P1→P2→observation）排序；**只读，不提供修改 enabled 的路径**（ADR-011） |

## 发布门禁红线（ADR-012，务必阅读）

1. `publishable` 数据库列只是投影；权威判断永远在
   `packages/domain/publish_gate.evaluate_publish_gate`。
2. 到达 `published` 的唯一路径：`POST /api/cards/{id}/publish`，且必须
   **同时**通过 状态机合法迁移（scored→published）与八项门禁（含 gate-p7
   人工 approved 审核）。
3. 不存在任何"跳过 gate"的代码路径；`/lifecycle` 端点显式拒绝 target=published。
4. 审核记录只能由 `human:` 前缀账号写入，自动流水线无法自审自发。

## 测试

```bash
# 仓库根目录
python -m pytest tests/unit/test_api.py -q   # 本服务 22 项
python -m pytest -q                          # 全量
```

测试使用独立 tmp SQLite engine（monkeypatch `database.engine`/`SessionLocal`），
不触碰默认 `./aimath.db`，也不读写真实开发数据。

## 已知偏差（Phase 2 待办）

- 审核决定枚举：端点契约含 `rejected`，而 `schemas/review` 的
  problem_card `audit.human_reviews.decision` 枚举暂为
  `approved|needs_changes|cannot_judge|escalated`。API 层按契约接受 `rejected`
  并只增不改地落审计；Schema 升版本（v1.1.0 + 新 ADR）后对齐。
- 表结构变更目前靠 `create_all`（新增表/列可用；改列需手工迁移）。
  生产 PostgreSQL 上线前需引入 Alembic（新 ADR）。
- 抽卡 adjacent 段的"近域"暂定义为"与 top1 卡同 primary_domain"，
  Phase 2 接 taxonomy 近邻表后替换（docs/03）。
