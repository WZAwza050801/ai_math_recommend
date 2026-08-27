# ADR-006：专家以成对比较为主要标签形式

- 状态：Accepted（设计基线 v0.1 §25）
- 日期：2026-08-27（基线）/ 2026-08-28（Phase 0 落地注记）

## 背景

绝对评分（给重要性打 0–100 分）在人类专家间方差极大且不可传递；跨领域绝对分数更不可比。

## 决策

专家标注以成对比较（"A 与 B 哪个更值得尝试"）为主标签形式；绝对分数只作为辅助排序后台量。

## 理由

人类更擅长回答"A 与 B 哪个更值得"而不是稳定地给出绝对 0–100 分。

## 后果

- Review Schema（schemas/review v1.0.0）内含 pairwise_preference 结构（preferred/compared/notes）。
- 前端呈现等级（band）而非连续分数（§13.2）；连续值只存后台。
- 未来 Learning to Rank（Phase 4）以成对偏好为主监督信号（Bradley–Terry 基线）。
