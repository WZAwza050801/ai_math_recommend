# ADR-013：数据源大扩充（42 源）与 P0 批量启用

- 状态：Accepted
- 日期：2026-08-28（深夜，用户过夜授权执行）

## 背景

用户于 2026-08-28 深夜消息中提供完整平台接入优先级清单（九大类：问题平台 / 文献平台 / 社区平台 / 形式化平台 / 对象数据库 / 人物奖项 / 计算工具 / 不建议依赖 / 第一版十个连接器），并明确授权："能批准的肯定批准"。清单定义四级优先级：P0（第一版直接接入）、P1（第二批）、P2（按领域选择性）、观察源（只发现线索，不作事实依据）。

## 决策

1. Source Registry 从 14 源扩充至 **42 源**（SRC-0001..SRC-0042），逐条按用户清单赋 `priority_tier`（回填既有 14 源 + 新增 28 源）。
2. **启用 11 个 P0 免鉴权源**（enabled=true）：arXiv、formal-conjectures、Open Problem Garden、erdosproblems.com、OpenAlex、MathOverflow（SE API 低配额可用）、AIM Problem Lists、AIM Workshop、GitHub 公共 API、zbMATH Open、Crossref。启用依据=用户一揽子批准；全部无需账号/API Key。
3. **保持禁用**：P1/P2/观察源（按清单第二批/选择性接入）；需要 API Key 的源（Semantic Scholar、CORE）即使列 P1 也禁用，待 Key 落地。
4. 用户清单与既有判定的冲突以**用户清单为准**（例：Clay 由我此前建议的"首批"改为用户指定的 P1 名望池；Wikipedia 归观察源）。
5. Schema 升级 **source_registry v1.1.0**：新增可选字段 `priority_tier`（P0/P1/P2/observation）与 `connector_name`；v1.0.0 实例全部兼容。目录内 schema.json 恒为最新版。

## 账号与凭据的现实约束（如实记录）

- 本机 `gh` 已登录（账号 WZAwza050801，repo 权限）→ GitHub 仓库已创建并推送（私有）。
- **未能代办**：用户提出"需要登录的你自己点击谷歌注册"，但第三方账号注册需要其密码簿与邮箱验证码（发往 3230101115@zju.edu.cn / 3116809059@qq.com），Agent 无法读取，且自动化注册受平台条款限制。已列入晨间清单：需要用户人工注册/申请的仅 Semantic Scholar Key、CORE Key（其余 P0 全免鉴权）。
- 未在任何第三方平台代替用户创建账号。

## 后果

- `scripts/expand_source_registry.py` 幂等可重跑；注册表快照进 git。
- Connector 实现顺序按 P0：arXiv / OpenAlex / Crossref / OPG / formal-conjectures / GitHub / zbMATH / Erdős / AIM / MathOverflow（Phase 2）。
- 每源独立开关的架构原则（用户清单原文）落实：任一平台改版/限流不拖垮系统。
