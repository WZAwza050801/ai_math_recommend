# ADR Backlog — 待形成正式 ADR 的开放设计问题

状态：Pending（不阻塞 Phase 0 金标准原型；进入 Phase 1 开发前逐项裁决）

来源一：设计基线 §26（第 4–12 项；第 1/2/3 项已由 ADR-010/011/012 裁决）。
来源二：docs/00–11 文档拆分时各文末"待裁决问题"节中未闭环项。

| # | 问题 | 来源 | 建议裁决时点 |
|---|---|---|---|
| B-01 | 课题组内部与未来公共版本的权限边界（visibility 三档的判定规则） | §26.4 | Phase 1（权限模型落地时） |
| B-02 | 用户学术画像是否读取论文、主页或简历（隐私与自陈偏好权衡） | §26.5 | Phase 3（用户系统前） |
| B-03 | 专家审核的贡献归属和署名方式 | §26.6 | Phase 1（审核队列实现时） |
| B-04 | 重要性 rubric 的维度权重与领域归一化策略（importance-rubric-v0.1 仅为初版） | §26.7 | Phase 2（首批 LLM 评估校准后） |
| B-05 | AI 友好性 rubric 由哪些模型和专家共同校准 | §26.8 | Phase 2 |
| B-06 | I/A/P/C 四量的值域与缺失值语义（当前实现按 [0,100]，缺证据→insufficient_evidence band） | docs/05 待裁决 | Phase 2（与 B-04 一并） |
| B-07 | 是否引入引用/讨论计数作为 I 的机械下限 | §26.9 | Phase 2 |
| B-08 | likely_open 超过阈值自动降级 Stale 的具体阈值与冷却期 | §26.10；docs/02 | Phase 1（TASK-1001 调度实现时） |
| B-09 | 反馈学习何时从规则基线切换到 Learning to Rank（切换判据） | §26.11 | Phase 4 |
| B-10 | 多语言卡片的规范化目标语言与对照呈现策略 | §26.12 | Phase 2（多语源接入前） |
| B-11 | Source Registry 的 allowed_usage 枚举扩展（如 zenodo_monitor_only） | docs/03 待裁决 | Phase 1 |
| B-12 | P3 Relation Agent 与 P5 Metrics/Importance Agent 的提示词目录归属（建议 prompts/relation/ 与 prompts/assessment/） | docs/04 待裁决 | Phase 2（提示词落地时） |
| B-13 | §11.1 模板与 agent_task_contract Schema 的字段级对照表 | docs/04 待裁决 | Phase 1 |
| B-14 | Rejected/Archived 是否绝对终态（当前实现：绝对终态；恢复需建新卡并回指） | docs/02 待裁决 | Phase 1（如需软恢复再放开） |
| B-15 | 金标准集扩充策略（>31 张时的准入与配额规则） | docs/10 待裁决 | Phase 2 |
