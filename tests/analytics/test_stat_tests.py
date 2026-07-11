import math
import pytest
from analytics.stat_tests import (
    ALPHA, trend, compare, by_region, correlate,
    TrendResult, CompareResult, RegionResult, CorrelationResult,
)


def test_trend_detects_clear_increase():
    r = trend([10, 20, 30, 40, 50], indicator="IDPs")
    assert isinstance(r, TrendResult)
    assert r.direction == "increasing"
    assert r.slope is not None and r.slope > 0
    assert r.p_value is not None and r.p_value < ALPHA
    assert r.pct_change == pytest.approx(400.0)
    assert r.ci_low is not None and r.ci_high is not None


def test_trend_flat_series_no_trend():
    r = trend([10, 11, 9, 10, 10, 11], indicator="IDPs")
    assert r.direction in ("no trend", "decreasing", "increasing")
    assert r.p_value is not None and r.p_value > ALPHA


def test_trend_insufficient_points():
    r = trend([10, 20], indicator="IDPs", min_points=4)
    assert r.direction == "insufficient_data"
    assert r.slope is None and r.p_value is None
    assert r.n_points == 2


def test_trend_zero_variance():
    r = trend([5, 5, 5, 5, 5], indicator="IDPs")
    assert r.direction == "insufficient_data"
    assert r.p_value is None


def test_trend_ignores_nan():
    r = trend([10, float("nan"), 30, 40, 50], indicator="IDPs")
    assert r.n_points == 4          # NaN dropped
    assert r.direction == "increasing"


def test_compare_significant_change():
    r = compare([10, 12, 11, 10], [30, 32, 31, 29], indicator="Needs",
                period_a="2025-H1", period_b="2025-H2")
    assert isinstance(r, CompareResult)
    assert r.pct_change is not None and r.pct_change > 100
    assert r.significant is True
    assert r.p_value is not None and r.p_value < ALPHA


def test_compare_insufficient_data():
    r = compare([10], [], indicator="Needs", period_a="a", period_b="b")
    assert r.significant is False
    assert r.note == "insufficient_data"
    assert r.p_value is None


def test_by_region_ranks_and_tests():
    series = {"North": [100, 110, 120], "South": [10, 12, 11], "East": [50, 55, 52]}
    r = by_region(series, indicator="Needs", period="2025")
    assert isinstance(r, RegionResult)
    assert r.ranking[0][0] == "North"      # highest mean first
    assert r.ranking[-1][0] == "South"
    assert r.p_value is not None and r.significant is True


def test_by_region_single_region_not_significant():
    r = by_region({"North": [100, 110]}, indicator="Needs", period="2025")
    assert r.ranking[0][0] == "North"
    assert r.significant is False          # need >=2 groups to test


def test_correlate_perfect_positive():
    r = correlate([1, 2, 3, 4, 5], [2, 4, 6, 8, 10],
                  indicator_x="A", indicator_y="B")
    assert isinstance(r, CorrelationResult)
    assert r.coefficient == pytest.approx(1.0)
    assert r.significant is True
    assert r.method == "pearson"


def test_correlate_insufficient_overlap():
    r = correlate([1, 2], [2, 4], indicator_x="A", indicator_y="B")
    assert r.coefficient is None
    assert r.note == "insufficient_data"


def test_correlate_spearman_method():
    r = correlate([1, 2, 3, 4], [1, 4, 9, 16],
                  indicator_x="A", indicator_y="B", method="spearman")
    assert r.method == "spearman"
    assert r.coefficient == pytest.approx(1.0)   # monotonic
