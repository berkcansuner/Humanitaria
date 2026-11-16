import math
import pytest
from analytics.stat_tests import (
    ALPHA, CORRELATION_MIN_POINTS, trend, by_region, correlate, holm,
    TrendResult, RegionResult, CorrelationResult,
)


def test_trend_detects_clear_increase():
    r = trend([10, 20, 30, 40, 50], indicator="IDPs")
    assert isinstance(r, TrendResult)
    assert r.direction == "increasing"
    assert r.slope is not None and r.slope > 0
    assert r.p_value is not None and r.p_value < ALPHA
    assert r.pct_change == pytest.approx(400.0)
    assert r.ci_low is not None and r.ci_high is not None
    assert r.intercept == pytest.approx(10.0)


def test_trend_flat_series_no_trend():
    r = trend([10, 11, 9, 10, 10, 11], indicator="IDPs")
    assert r.direction in ("no trend", "decreasing", "increasing")
    assert r.p_value is not None and r.p_value > ALPHA


def test_trend_insufficient_points():
    r = trend([10, 20], indicator="IDPs", min_points=4)
    assert r.direction == "insufficient_data"
    assert r.slope is None and r.p_value is None
    assert r.n_points == 2
    assert r.intercept is None


def test_trend_zero_variance():
    r = trend([5, 5, 5, 5, 5], indicator="IDPs")
    assert r.direction == "insufficient_data"
    assert r.p_value is None
    assert r.intercept is None


def test_trend_ignores_nan():
    r = trend([10, float("nan"), 30, 40, 50], indicator="IDPs")
    assert r.n_points == 4          # NaN dropped
    assert r.direction == "increasing"


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
    r = correlate([1, 2, 3, 4, 5, 6, 7, 8], [2, 4, 6, 8, 10, 12, 14, 16],
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
    r = correlate([1, 2, 3, 4, 5, 6, 7, 8], [1, 4, 9, 16, 25, 36, 49, 64],
                  indicator_x="A", indicator_y="B", method="spearman")
    assert r.method == "spearman"
    assert r.coefficient == pytest.approx(1.0)   # monotonic


def test_correlate_needs_eight_common_points():
    # Short trending series correlate spuriously; below 8 common periods no test runs.
    assert CORRELATION_MIN_POINTS == 8
    r = correlate([1, 2, 3, 4, 5, 6, 7], [2, 4, 6, 8, 10, 12, 14], indicator_x="A", indicator_y="B")
    assert r.note == "insufficient_data" and r.p_value is None


def test_trend_slope_is_sen_slope_per_year_on_real_times():
    # Uneven spacing (the 3rd year is missing): pairwise slopes 10, 10, 7.5, 10, 6.67, 5
    # -> median 8.75 per year. An index axis would have said 10 per "period".
    r = trend([10, 20, 30, 40], indicator="IDPs", times=[0, 1, 2, 4])
    assert r.slope == pytest.approx(8.75)


def test_trend_reports_kendall_tau_and_sen_ci():
    r = trend([10, 20, 30, 40, 50], indicator="IDPs")
    assert r.tau == pytest.approx(1.0)
    assert r.ci_low <= r.slope <= r.ci_high


def test_trend_ci_is_none_when_too_few_points_for_it():
    # With 4 points the Sen-slope confidence interval is undefined (C > number of pairs).
    r = trend([10, 20, 30, 41], indicator="IDPs")
    assert r.slope is not None and r.ci_low is None and r.ci_high is None


def test_holm_adjusts_in_original_order_and_keeps_none():
    # sorted 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotone 0.03, 0.06, 0.06
    adj = holm([0.01, 0.04, None, 0.03])
    assert adj[2] is None
    assert [adj[0], adj[1], adj[3]] == pytest.approx([0.03, 0.06, 0.06])


def test_holm_caps_at_one():
    assert holm([0.6, 0.7]) == pytest.approx([1.0, 1.0])
