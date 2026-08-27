"""基线排序单元测试（设计规范 §13.3 / §13.6，权重版本化）。"""

from __future__ import annotations

import math

import pytest

from ai_math_ranking import (
    WEIGHTS_VERSION,
    PoolMix,
    RankingInputError,
    band_from_score,
    core_score,
    pool_mix_for_mode,
    user_score,
)


class TestCoreScore:
    def test_geometric_mean(self):
        assert core_score(100, 100) == pytest.approx(100.0)
        assert core_score(81, 25) == pytest.approx(45.0)
        assert core_score(0, 100) == pytest.approx(0.0)

    def test_symmetry(self):
        assert core_score(80, 20) == pytest.approx(core_score(20, 80))

    def test_out_of_range_rejected(self):
        for bad in (-1, 101, 100.5):
            with pytest.raises(RankingInputError):
                core_score(bad, 50)
            with pytest.raises(RankingInputError):
                core_score(50, bad)


class TestUserScore:
    def test_formula(self):
        expected = math.sqrt(64 * 49) * (0.7 + 0.3 * 80 / 100) * (0.6 + 0.4 * 50 / 100)
        assert user_score(64, 49, 80, 50) == pytest.approx(expected)

    def test_bounds(self):
        # P=C=100 时放大最大；P=C=0 时仍有基线保底（0.7*0.6=0.42）
        base = core_score(50, 50)
        assert user_score(50, 50, 0, 0) == pytest.approx(base * 0.7 * 0.6)
        assert user_score(50, 50, 100, 100) == pytest.approx(base * 1.0 * 1.0)

    def test_monotone_in_all_dims(self):
        s0 = user_score(50, 50, 50, 50)
        assert user_score(60, 50, 50, 50) > s0
        assert user_score(50, 60, 50, 50) > s0
        assert user_score(50, 50, 60, 50) > s0
        assert user_score(50, 50, 50, 60) > s0


class TestBands:
    @pytest.mark.parametrize(
        "score,band",
        [(0, "low"), (29.9, "low"), (30, "medium_low"), (44.9, "medium_low"),
         (45, "medium"), (59.9, "medium"), (60, "medium_high"), (74.9, "medium_high"),
         (75, "high"), (100, "high")],
    )
    def test_thresholds(self, score, band):
        assert band_from_score(score) == band

    def test_invalid(self):
        with pytest.raises(RankingInputError):
            band_from_score(100.1)


class TestPoolMix:
    def test_base_mix_is_80_15_5(self):
        m = pool_mix_for_mode("balanced")
        assert (m.relevance, m.adjacent_exploration, m.distant_serendipity) == (0.80, 0.15, 0.05)

    def test_steady_more_relevance(self):
        assert pool_mix_for_mode("steady").relevance > 0.80

    def test_adventurous_more_exploration(self):
        adv = pool_mix_for_mode("adventurous")
        assert adv.relevance < 0.80
        assert adv.distant_serendipity > 0.05

    def test_all_modes_sum_to_one(self):
        for mode in ("steady", "balanced", "adventurous"):
            m = pool_mix_for_mode(mode)
            assert m.relevance + m.adjacent_exploration + m.distant_serendipity == pytest.approx(1.0)

    def test_unknown_mode_rejected(self):
        with pytest.raises(RankingInputError):
            pool_mix_for_mode("reckless")

    def test_pool_mix_validation(self):
        with pytest.raises(RankingInputError):
            PoolMix(0.5, 0.2, 0.1)


class TestVersioning:
    def test_weights_version_stamped(self):
        assert WEIGHTS_VERSION == "ranking-weights-v0.1"
