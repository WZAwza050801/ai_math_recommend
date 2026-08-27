# 晨间清单 — 留给项目主人的待办（2026-08-29 早晨）

过夜执行已完成 Phase 1–3 的核心实现（详见 EXECUTION_LOG.md 与最终报告）。
以下事项**只有你能做**，按重要性排序：

## 1. 金标准卡人工核验（P7，最重要）

30 张卡全部停在 `scored/publishable=false`，等专家签字。建议流程：

```bash
python -m uvicorn app.main:app --port 8901 --app-dir apps/api   # 启动后端
# 浏览器打开 http://127.0.0.1:8901/ → 「问题库」逐张看 → 优先看这 8 张：
# OP-000005(abc) OP-000011(Singmaster) OP-000017(Casas-Alvero) OP-000020(LonelyRunner)
# OP-000019(UnionClosed) OP-000021(Rota) OP-000028(CH) OP-000029(EDP) OP-000030(Kepler)
```

发现事实错误：不要直接改 JSON，走 API 的 review 流程或改卡后 version+1。

## 2. 需要你注册/申请的账号（我无法代办的部分）

我无法读取你的密码簿和邮箱验证码，且自动化注册受平台条款限制，所以以下留给你：

| 服务 | 用途 | 申请入口 |
|---|---|---|
| Semantic Scholar API Key | P1 文献连接器（引用网络） | https://www.semanticscholar.org/product/api |
| CORE API Key | P1 开放获取全文 | https://core.ac.uk/services/api |

注册邮箱可用 3230101115@zju.edu.cn 或 3116809059@qq.com。
拿到 Key 后放入环境变量 `S2_API_KEY` / `CORE_API_KEY`，再启用对应注册表条目。

**P0 全部 11 个源都已免鉴权启用，不申请上面两个也不影响当前功能。**

## 3. GitHub 仓库已建好（无需操作，知会一下）

- https://github.com/WZAwza050801/ai_math_recommend（**私有**）
- 用了你本机已登录的 gh 凭据创建并推送；如想公开，`gh repo edit --visibility public`。

## 4. 发布前检查（想让卡对外可见时）

任何一张卡要发布，必须：
1. 在「问题库」给它加一条 `decision=approved` 的人工审核记录；
2. 调 `POST /api/cards/{id}/publish`——八项门禁 + gate-p7 人工批准全过才会成功。

这是系统红线（ADR-012），没有绕过路径。

## 5. 已知待复核事实点（各卡 notes 里有标记）

- OP-000015：EV-000015-2 的 tier 标 C，与 SRC-0014 注册等级 B 不一致；
- OP-000016：Tao 高次数结果的覆盖界待查；
- OP-000023：τ(5) 的 44.65 型上界声称（只在 notes，未进正字段）；
- OP-000030：Flyspeck 的 Forum of Mathematics π (2017) 出处待查；
- 完整清单见各卡 `notes` / `unknowns` 与 EXECUTION_LOG「遗留给人工」节。

## 6. 其余决策（不急）

- docs/adr/BACKLOG.md 的 15 项开放设计问题（进入 Phase 1 深度开发前裁决）。
