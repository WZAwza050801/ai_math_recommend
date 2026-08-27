"""ai_math_ranking — 第一版基线排序（设计规范 §13.3、§13.6）。

全部权重与混合参数版本化（ranking-weights-v0.1）；该公式只是可替换的工程基线，
不代表科学定律（§13.3）。前端只展示等级，连续数值仅存后台（§13.2）。
"""

from .baseline import (
    WEIGHTS_VERSION,
    PoolMix,
    RankingInputError,
    UserMode,
    band_from_score,
    core_score,
    pool_mix_for_mode,
    user_score,
)

__all__ = [
    "WEIGHTS_VERSION",
    "UserMode",
    "PoolMix",
    "RankingInputError",
    "core_score",
    "user_score",
    "band_from_score",
    "pool_mix_for_mode",
]
