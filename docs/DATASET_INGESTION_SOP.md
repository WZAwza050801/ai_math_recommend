# DATASET_INGESTION_SOP · 开放数据集批量接入标准作业程序

> 版本：v1.0（2026-08-29）
> 契约依据：[TASK-002_dataset_bulk_ingest](../packages/agent_contracts/TASK-002_dataset_bulk_ingest.yaml)
> 原则：**每个数据集 = TASK-002 的一次参数化实例**。接入工作不从零设计，只填参数；
> 纪律（不猜映射、候选停 candidate、去重仅标记、首批人工抽样）在契约层锁死，实例层不可豁免。

## 1. 标准流水线（八步，任何数据集都走同一条路）

```
①登记 → ②探测 → ③映射表 → ④快照落盘 → ⑤确定性转换 → ⑥Schema 校验
→ ⑦去重预检(仅标记) → ⑧抽样人工过目 → 放量 → 记账
```

| 步 | 做什么 | 产出 | 失败处理 |
|---|---|---|---|
| ① 登记 | Source Registry 条目（许可/信任级/优先级） | SRC-xxx.json | 未登记即硬失败 |
| ② 探测 | 拉样本，列字段清单/枚举值/条数 | 探测报告 | 结构不明 → 停，人工看 |
| ③ 映射表 | 数据集字段→卡字段；**状态词表映射 + 领域映射**，映射不上的字段留空 | mapping.yaml | **映射不上=跳过该条，禁止默认值** |
| ④ 快照 | 完整落 `data/raw/<SRC>/`，一次写入不可变 | 原始证据 | 校验和不一致 → 重拉 |
| ⑤ 转换 | 只做确定性变换（等值/查表）；语义字段留给 Wave A 的 LLM 任务 | 候选卡(8xxxxx) | — |
| ⑥ 校验 | 100% 过 problem_card Schema；失败率>5% 整批硬失败 | 校验报告 | 查映射表 bug |
| ⑦ 去重预检 | 标题相似 + 嵌入候选对 → **只标记 equivalent_to? 候选，不合并** | 候选对清单 | 合并=人工专属 |
| ⑧ 抽样 | 首批抽 20 张人工过目（主人或指定审） | 过目记录 | 不过目不放量 |

记账：`last_successful_sync` + 增量游标（文件 hash / ETag / max_id）。

## 2. 状态词表映射（全局统一，实例只能引用不能改）

| 数据集原始状态 | 我们的 open_status | 备注 |
|---|---|---|
| open / unsolved / conjecture | confirmed_open | 仅当数据集本身是 A/B 级维护 |
| proved / solved / theorem | **不直接 resolved**：标 status_uncertain + resolved_scope 待人工 | 防映射错误翻转状态（红线 3） |
| disproved | status_uncertain + contradicting_evidence 条目 | 同上 |
| 有争议 / 多个声称 | status_uncertain | — |
| 无状态字段 | status_uncertain | 永不默认开放 |

## 3. 附录 A：开放数据集积压清单（按接入难度排序）

### 第一梯队：结构化、许可明确（TASK-002 实例可直接开做）

| # | 数据集 | 形态 | 许可 | 预估规模 | 难度 | 前置 |
|---|---|---|---|---|---|---|
| D1 | **teorth/erdosproblems** | git, data/problems.yaml | Apache-2.0 | 1217 题（含状态/悬赏/Lean 标签） | S | 无（速赢 Q1） |
| D2 | **google-deepmind/formal-conjectures** | git, Lean 文件 | Apache-2.0 | 数百猜想（Erdős+其他） | S | 快照已在 raw/ |
| D3 | **OEIS** | 批量下载（gz 文件） | CC BY-SA 4.0 | ~37 万序列（含猜想型 A?? 标记） | M | 全量大，先筛 Conjecture 类 |
| D4 | **LMFDB** | HTTP API | 站点条款（非商业） | 数十万数学对象 | M | 对象≠问题：走"反例/对象核验"用例 |
| D5 | **House of Graphs** | API/批量 | 学术用途 | 极值图/反例图库 | S-M | 同上 |
| D6 | **Wikidata**（SPARQL：猜想实体+奖项+人物） | 查询 | CC0 | 数千实体 | M | 做对齐层不做卡 |

### 第二梯队：半结构化（HTML/PDF，需要解析器 + 首批严检）

| # | 数据集 | 形态 | 难度 | 备注 |
|---|---|---|---|---|
| D7 | AIM Problem Lists（多个列表） | HTML/PDF | M | 格式不统一，逐列表做 |
| D8 | Kourovka Notebook（群论） | PDF（版本化） | M | 版本对照=天然状态核验素材 |
| D9 | TOPP 计算几何 | HTML | S | 条目年代早，状态需重查 |
| D10 | Scottish Book | 网页/专著 | M | 历史问题，多已有后续 |
| D11 | Clay 千禧问题 | HTML | S | 7 题，走名望池，手工值得 |
| D12 | MathOverflow（SE API） | JSON | M | 不是问题库：做"状态信号源" |

### 第三梯队：形式化生态（喂 AI 友好性特征，不直接产卡）

| # | 数据集 | 用途 |
|---|---|---|
| D13 | mathlib（Lean） | 定理/定义覆盖度特征 |
| D14 | Archive of Formal Proofs（Isabelle） | 同上 |
| D15 | Metamath / Mizar / HOL Light 库 | 同上（按需） |

### 第四梯队：文献图（已连通，服务状态核验而非产卡）

OpenAlex / Crossref / zbMATH / arXiv（快照已在 raw/，Wave D 状态核验 agent 的燃料）。

## 4. 实例化模板（每个数据集填一张）

```yaml
# instances/D<n>.yaml
source_id: SRC-0010
snapshot: {method: git_clone, path: data/raw/SRC-0010/, cursor: commit_sha}
status_mapping: standard_v1        # 引用 §2 全局表
domain_mapping: {erdosproblems_builtin: combinatorics-and-graph-theory, ...}
field_map:
  id: problem_id_prefix            # Erdos-488 → OP-8xxxxx 别名字段
  problem: statements.original.text
  status: open_status（经 §2 表）
  prize: importance_assessment.evidence[]（悬赏=社区价值证据）
  lean_formalization: ai_affordance_assessment.evidence_for[]（形式化事件=硬特征）
batch_thresholds: {schema_fail_max: 0.05, sample_review_n: 20}
```

## 5. 与波次的依赖

- 第一梯队 D1/D2：**现在就能做**（确定性映射够用）
- D3（OEIS 全量）：需 Wave A 抽取 agent（筛选"猜想型"序列是语义任务）
- D6/D13（对齐层）：需 Wave C 嵌入向量
- 全部实例的⑦去重预检在 Wave C 之前降级为标题相似度

## 6. 扩展新数据集的准入检查（未来任何"比较 open 的集合"）

1. 有没有稳定标识（repo / API / 版本化下载）？没有 → 观察源，不接入
2. 许可允许我们的用途吗？（CC BY-SA/Apache/CC0 = 绿灯）
3. 数据是"问题"还是"对象/文献"？对象和文献走各自专用通道
4. 状态字段是社区维护的吗？是 → 映射仍走 §2 保守表
