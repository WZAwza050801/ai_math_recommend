"""发布门禁（设计规范 §10.2）。

进入 Published 必须同时满足八项条件；任何一项缺失即阻塞。
本函数只做确定性检查，不做任何数学判断。

§10.2 同时严禁：网页搜索 -> LLM 打分 -> 自动发布。
本门禁是该禁令的程序化体现：没有人工核验标记与证据完备性，publishable 永远为 False。
"""

from __future__ import annotations

from typing import Any

from .state_machine import LifecycleState

GATE_VERSION = "publish-gate-v1.0.0"


def evaluate_publish_gate(card: dict[str, Any]) -> tuple[bool, list[str]]:
    """返回 (publishable, blockers)。blockers 为空列表当且仅当全部八项通过。"""

    blockers: list[str] = []

    statements = card.get("statements", {})
    original = statements.get("original", {}) if isinstance(statements, dict) else {}
    normalized = statements.get("normalized", {}) if isinstance(statements, dict) else {}
    provenance = card.get("provenance", {})
    open_status = card.get("open_status", {})
    publication = card.get("publication", {})
    audit = card.get("audit", {})
    importance = card.get("importance_assessment") or {}
    affordance = card.get("ai_affordance_assessment") or {}

    # 1. 原始陈述和精确来源存在
    if not (original.get("text") or original.get("latex")):
        blockers.append("gate-1: 原始陈述缺失")
    if not original.get("source_id"):
        blockers.append("gate-1: 原始来源 source_id 缺失")
    if not original.get("source_location") and not provenance.get("source_urls"):
        blockers.append("gate-1: 无精确定位（source_location 或 source_urls）")

    # 2. 规范化陈述通过校验（此处为结构最小检查；完整校验由 JSON Schema 完成）
    if not normalized.get("text"):
        blockers.append("gate-2: 规范化陈述缺失")

    # 3. 完成疑似重复检查（以 TASK-301 运行记录为准）
    model_runs = audit.get("model_runs", []) if isinstance(audit, dict) else []
    run_names = {r.get("task_name") for r in model_runs if isinstance(r, dict)}
    if "TASK-301_dedup_and_relation" not in run_names:
        blockers.append("gate-3: 未完成疑似重复检查（无 TASK-301 运行记录）")

    # 4. 开放状态不为 resolved / withdrawn_or_malformed
    if open_status.get("status") in ("resolved", "withdrawn_or_malformed"):
        blockers.append(f"gate-4: 开放状态为 {open_status.get('status')}，不得作为开放问题发布")

    # 5. 重要性和 AI 友好性均包含证据
    if not importance.get("evidence"):
        blockers.append("gate-5: 重要性评估无证据")
    if not affordance.get("evidence_for") and not affordance.get("evidence_against"):
        blockers.append("gate-5: AI 友好性评估无证据")

    # 6. 所有关键判断带时间戳和 rubric 版本
    if not open_status.get("last_checked_at"):
        blockers.append("gate-6: 开放状态缺 last_checked_at")
    if not importance.get("rubric_version") or not affordance.get("rubric_version"):
        blockers.append("gate-6: 评估缺 rubric_version")

    # 7. 未人工确认的内容明确标记
    human_reviews = audit.get("human_reviews", []) if isinstance(audit, dict) else []
    if not human_reviews and not publication.get("publish_blockers"):
        blockers.append("gate-7: 存在未人工确认内容但未标记（publish_blockers 为空）")

    # P7 人工审核批准（§12 P7 + ADR-012：Phase 0 起全部卡片发布前必须获得专家 approved 决定。
    # 这是『严禁 网页搜索->LLM 打分->自动发布』的核心闸门。）
    approved = any(
        isinstance(r, dict) and r.get("decision") == "approved" for r in human_reviews
    )
    if not approved:
        blockers.append("gate-p7: 未获得人工审核批准（P7 专家核验 approved 决定缺失）")

    # 8. 不存在 P0 风险阻塞项
    for b in publication.get("publish_blockers", []):
        if "P0" in str(b):
            blockers.append(f"gate-8: 存在 P0 风险阻塞项: {b}")

    # 发布行为本身只能在 Scored -> Published 的合法迁移上发生
    if publication.get("lifecycle_state") != LifecycleState.SCORED.value:
        blockers.append(
            f"gate-0: 发布前必须处于 scored 状态，当前为 {publication.get('lifecycle_state')}"
        )

    return (len(blockers) == 0, blockers)
