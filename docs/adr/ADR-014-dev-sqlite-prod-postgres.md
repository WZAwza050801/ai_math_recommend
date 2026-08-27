# ADR-014：开发环境 SQLite / 生产 PostgreSQL 双模数据库

- 状态：Accepted（Phase 1 执行决策）
- 日期：2026-08-28
- 关联：ADR-003（关系主存）、ADR-004（不可变轨迹）、ADR-012（发布门禁）

## 背景

Phase 1 需要为管理后台提供关系主存（ADR-003）。原计划经 docker-compose 启用
PostgreSQL，但当前开发机 Docker 不可用；同时 ADR-003 的动机（实体、版本、
来源、状态、审核关系需要严格一致性）要求主存必须是**关系库**，不能退化为
文档存储或内存对象。

## 决策

1. **双模连接串**：`apps/api/app/database.py` 读环境变量 `DATABASE_URL`，
   缺省回退 `sqlite:///./aimath.db`（开发模式）；生产/CI 通过环境变量注入
   PostgreSQL 连接串，约定形如
   `postgresql+psycopg://<user>:<password>@<host>:5432/<database>`。
2. **ADR-003 原则不变**：SQLite 只是开发期替身，它仍然是关系数据库——
   外键（card_versions.problem_id → cards.problem_id）、约束、事务、SQL
   全部按关系语义使用；生产永远是 PostgreSQL（ADR-003 决策不撤销）。
3. **方言兼容写法**：全部数据访问经 SQLAlchemy 2.x ORM 表达，不使用任何
   SQLite 专有 SQL；仅引擎参数按方言分支（SQLite 加
   `check_same_thread=False`，PostgreSQL 加 `pool_pre_ping=True`）。
4. **版本审计不受影响**：`card_versions` 不可变快照表（ADR-004）在两种
   模式下行为一致；发布门禁（ADR-012）与数据库选型完全解耦。

## 理由

- 本机无 Docker 时，SQLite 以零运维成本保住关系语义（外键/事务/约束），
  测试（tmp 库）与开发（文件库）可完全隔离；
- SQLAlchemy 方言吸收层让"换库不改业务代码"成立，双模切换只是环境变量；
- 测试套件证明：同一套 ORM 代码在 tmp SQLite 上通过全部 API 行为测试，
  生产 PostgreSQL 的差异集中在连接与迁移，而非业务逻辑。

## 后果

- 开发库 `apps/api/aimath.db` 已加入 `apps/api/.gitignore`，严禁提交；
- SQLite 并发写弱（单写者），仅可接受于单机开发；生产必须 PostgreSQL；
- SQLite 不强制外键检查除非 `PRAGMA foreign_keys=ON`，应用层始终按外键
  语义写入（Phase 1 只有 cards/card_versions 一对关系，风险可控）；
- Phase 1 用 `Base.metadata.create_all` 建表（只支持新增表/列）；生产
  PostgreSQL 上线前必须引入 Alembic 迁移（含降级脚本与版本记录，§24.3
  "没有迁移、回滚和版本记录地修改数据库"禁止条款），届时另立 ADR；
- 时间戳列统一 `DateTime(timezone=True)` + UTC，规避两库时区行为差异。
