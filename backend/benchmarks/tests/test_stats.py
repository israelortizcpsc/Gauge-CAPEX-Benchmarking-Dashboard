"""Unit tests for the pure stats layer. No database required."""

import math

import pytest

from benchmarks import stats


class TestPercentile:
    def test_known_values_linear_interpolation(self):
        data = [1, 2, 3, 4, 5]
        # Matches numpy.percentile(data, p) default 'linear' method.
        assert stats.percentile(data, 0) == 1
        assert stats.percentile(data, 50) == 3
        assert stats.percentile(data, 100) == 5
        assert stats.percentile(data, 25) == 2
        assert stats.percentile(data, 80) == pytest.approx(4.2)

    def test_interpolates_between_neighbours(self):
        assert stats.percentile([10, 20], 50) == pytest.approx(15.0)
        assert stats.percentile([0, 100], 90) == pytest.approx(90.0)

    def test_unsorted_input_is_handled(self):
        assert stats.percentile([5, 1, 3, 2, 4], 50) == 3

    def test_single_value(self):
        assert stats.percentile([7], 50) == 7
        assert stats.percentile([7], 10) == 7

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            stats.percentile([], 50)

    def test_out_of_range_p_raises(self):
        with pytest.raises(ValueError):
            stats.percentile([1, 2, 3], 150)


class TestPercentileRank:
    def test_midpoint_convention(self):
        data = [10, 20, 30, 40]
        assert stats.percentile_rank(data, 5) == 0.0
        assert stats.percentile_rank(data, 45) == 100.0
        assert stats.percentile_rank(data, 25) == 50.0  # between 20 and 30

    def test_ties_count_as_half(self):
        # x equals every element -> exactly the median.
        assert stats.percentile_rank([5, 5, 5, 5], 5) == 50.0

    def test_empty_assumes_median(self):
        assert stats.percentile_rank([], 99) == 50.0


class TestSummarize:
    def test_returns_full_distribution(self):
        data = list(range(1, 101))  # 1..100
        dist = stats.summarize(data)
        assert dist.n == 100
        assert dist.mean == pytest.approx(50.5)
        assert dist.p50 == pytest.approx(50.5)
        assert dist.p80 == pytest.approx(80.2)

    def test_empty_returns_none(self):
        assert stats.summarize([]) is None

    def test_as_dict_has_all_percentile_keys(self):
        dist = stats.summarize([1, 2, 3, 4, 5]).as_dict()
        for key in ("n", "mean", "p10", "p25", "p50", "p75", "p80", "p90"):
            assert key in dist


class TestCostGap:
    def test_above_and_below_norm(self):
        assert stats.cost_gap(115, 100) == pytest.approx(0.15)
        assert stats.cost_gap(90, 100) == pytest.approx(-0.10)

    def test_zero_reference_returns_none(self):
        assert stats.cost_gap(10, 0) is None


class TestFelReadiness:
    def test_all_max_is_100_best_practical(self):
        fel = stats.fel_readiness(5, 5, 5)
        assert fel.score == 100
        assert fel.band == "Best Practical"

    def test_all_min_is_zero_screening(self):
        fel = stats.fel_readiness(1, 1, 1)
        assert fel.score == 0
        assert fel.band == "Screening"

    def test_scope_has_the_largest_single_weight(self):
        # Moving the same +2 into scope should lift the score more than moving
        # it into engineering or execution, because scope is weighted highest.
        from_scope = stats.fel_readiness(5, 3, 3).score
        from_eng = stats.fel_readiness(3, 5, 3).score
        from_exe = stats.fel_readiness(3, 3, 5).score
        assert from_scope > from_eng > from_exe
        # sanity: midpoint inputs land mid-band
        assert stats.fel_readiness(3, 3, 3).score == 50

    def test_components_normalized_0_100(self):
        fel = stats.fel_readiness(3, 5, 1)
        assert fel.components["scope"] == 50.0
        assert fel.components["engineering"] == 100.0
        assert fel.components["execution"] == 0.0

    @pytest.mark.parametrize("bad", [0, 6, -1])
    def test_out_of_range_raises(self, bad):
        with pytest.raises(ValueError):
            stats.fel_readiness(bad, 3, 3)

    def test_band_boundaries(self):
        assert stats.fel_band(80) == "Best Practical"
        assert stats.fel_band(79.9) == "Good"
        assert stats.fel_band(60) == "Good"
        assert stats.fel_band(59) == "Fair"
        assert stats.fel_band(40) == "Fair"
        assert stats.fel_band(39) == "Screening"
