"""基线排序公式（版本化，设计规范 §13.3 / §13.6）。

S_core = sqrt(I · A)                              —— 几何平均基线
S_user = S_core · (0.7 + 0.3·P/100) · (0.6 + 0.4·C/100)   —— 个性化重排

I=重要性 A=AI 友好性 P=用户匹配度 C=证据可信度，均为 0–100。
权重元组 (0.7, 0.3) 与 (0.6, 0.4) 属于 WEIGHTS_VERSION；任何修改必须新版本号。
"""

from __future__ import annotations

from dataclasses import dataclass

WEIGHTS_VERSION = "ranking-weights-v0.1"

# 个性化重排权重：用户匹配度占 30% 空间（0.7 基线 + 0.3·P/100），证据可信度占 40% 空间
W_USER = (0.7, 0.3)
W_CONF = (0.6, 0.4)

# 卡池混合策略（§13.6）：80% 高相关 / 15% 邻近探索 / 5% 远距离偶遇
BASE_MIX = (0.80, 0.15, 0.05)  # (exploration_adjacent=15%, exploration_distant=5%)


class RankingInputError(ValueError):
    pass


def _assert_dimension(name: str, value: float) -> float:
    v = float(value)
    if not (0.0 <= v <= 100.0):
        raise RankingInputError(f"{name} 必须在 [0,100]，收到 {value}")
    return v


def core_score(importance: float, ai_affordance: float) -> float:
    """S_core = sqrt(I·A)，返回 [0,100]。"""
    i = _assert_dimension("importance", importance)
    a = _assert_dimension("ai_affordance", ai_affordance)
    return (i * a) ** 0.5


def user_score(
    importance: float,
    ai_affordance: float,
    profile_match: float,
    evidence_confidence: float,
) -> float:
    """S_user = S_core · (0.7 + 0.3·P/100) · (0.6 + 0.4·C/100)。"""
    p = _assert_dimension("profile_match", profile_match)
    c = _assert_dimension("evidence_confidence", evidence_confidence)
    base = core_score(importance, ai_affordance)
    return base * (W_USER[0] + W_USER[1] * p / 100.0) * (W_CONF[0] + W_CONF[1] * c / 100.0)


def band_from_score(score: float) -> str:
    """连续分数 → 前端等级（§13.2：前端默认显示等级，不显示小数分数）。"""
    if score < 0 or score > 100:
        raise RankingInputError(f"score 必须在 [0,100]，收到 {score}")
    if score >= 75:
        return "high"
    if score >= 60:
        return "medium_high"
    if score >= 45:
        return "medium"
    if score >= 30:
        return "medium_low"
    return "low"


@dataclass(frozen=True)
class PoolMix:
    """探索混合比例（高相关 / 邻近 / 远距离），和恒为 1。"""

    relevance: float
    adjacent_exploration: float
    distant_serendipity: float

    def __post_init__(self) -> None:
        total = self.relevance + self.adjacent_exploration + self.distant_serendipity
        if abs(total - 1.0) > 1e-9:
            raise RankingInputError(f"混合比例之和必须为 1，收到 {total}")


class UserMode:
    """三种用户模式（§13.6）。"""

    STEADY = "steady"        # 稳健：更高相关性、更低背景成本
    BALANCED = "balanced"    # 平衡：默认
    ADVENTUROUS = "adventurous"  # 冒险：更多高价值难题与跨领域探索


_MODE_MIX: dict[str, PoolMix] = {
    UserMode.STEADY: PoolMix(0.90, 0.08, 0.02),
    UserMode.BALANCED: PoolMix(BASE_MIX[0], BASE_MIX[1], BASE_MIX[2]),
    UserMode.ADVENTUROUS: PoolMix(0.65, 0.25, 0.10),
}


def pool_mix_for_mode(mode: str) -> PoolMix:
    try:
        return _MODE_MIX[mode]
    except KeyError:
        raise RankingInputError(
            f"未知用户模式 {mode}；合法值: {sorted(_MODE_MIX)}"
        ) from None
