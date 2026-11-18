from scripts.build_landing_snapshot import (
    coverage_points, peak_window_trend, top_regions, trend_test,
)


def _country(iso3, name, lat, lon):
    return {"fields": {"iso3": iso3, "name": name, "location": {"lat": lat, "lon": lon}}}


def test_coverage_points_joins_counts_and_location():
    countries = [_country("SDN", "Sudan", 15.5, 32.5), _country("YEM", "Yemen", 15.3, 44.2)]
    points = coverage_points(countries, {"Sudan": 120, "Yemen": 40})
    assert points == [
        {"iso3": "SDN", "name": "Sudan", "lat": 15.5, "lon": 32.5, "reports": 120},
        {"iso3": "YEM", "name": "Yemen", "lat": 15.3, "lon": 44.2, "reports": 40},
    ]


def test_skips_countries_without_location():
    countries = [
        {"fields": {"iso3": "XXX", "name": "Nowhere"}},
        _country("SDN", "Sudan", 15.5, 32.5),
        _country("YEM", "Yemen", 15.3, 44.2),
    ]
    points = coverage_points(countries, {"Nowhere": 9, "Sudan": 5, "Yemen": 0})
    assert [p["iso3"] for p in points] == ["SDN"]


def test_top_regions_rounds_and_limits():
    ranking = [(f"R{i}", 1000.6 - i) for i in range(7)]
    out = top_regions(ranking)
    assert len(out) == 5
    assert out[0] == ["R0", 1001]
    assert all(isinstance(v, int) for _, v in out)


def test_coverage_points_match_documents_country_by_short_or_plain_name():
    countries = [
        {"fields": {"iso3": "IRN", "name": "Iran (Islamic Republic of)", "shortname": "Iran",
                    "location": {"lat": 32.5, "lon": 54.3}}},
        {"fields": {"iso3": "ABW", "name": "Aruba (The Netherlands)",
                    "location": {"lat": 12.5, "lon": -70.0}}},
    ]
    points = coverage_points(countries, {"Iran": 283, "Aruba": 2})
    assert [(p["iso3"], p["reports"]) for p in points] == [("IRN", 283), ("ABW", 2)]


def test_trend_test_keeps_the_report_trend_result():
    stat = {"kind": "trend", "indicator": "Internally displaced people (IDPs)",
            "direction": "decreasing", "slope": -412345.678, "p_value": 0.000123456,
            "p_adjusted": 0.000370368, "significant": True, "pct_change": -9.87,
            "n_points": 31, "ci_low": -500000.0, "ci_high": -300000.0, "tau": -0.61,
            "first_period": "2023-08-31", "last_period": "2026-09-30T00:00:00", "unit": "people"}
    assert trend_test(stat) == {
        "test": "Mann-Kendall trend test, Sen's slope",
        "direction": "decreasing",
        "slope_per_year": -412346,
        "p_value": 0.000123,
        "p_adjusted": 0.00037,
        "significant": True,
        "n_points": 31,
        "period": ["2023-08-31", "2026-09-30"],
    }


def test_peak_window_trend_tests_only_the_series_from_its_peak():
    periods = [f"2024-{m:02d}-28" for m in range(1, 13)] + [f"2025-{m:02d}-28" for m in range(1, 10)]
    values = [100 + 10 * i for i in range(12)] + [300 - 12 * i for i in range(9)]  # peak 2025-01
    out = peak_window_trend(periods, values, min_points=4)
    assert out["period"] == ["2025-01-28", "2025-09-28"]
    assert out["n_points"] == 9
    assert out["direction"] == "decreasing"
    assert out["slope_per_year"] < 0
    # a single test: the Holm adjustment leaves p as it is
    assert out["p_adjusted"] == out["p_value"]
    assert out["significant"] is True
