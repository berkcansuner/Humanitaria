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


def test_latest_round_regions_ranks_the_given_round_not_period_means():
    from analytics.indicators import by_key
    from scripts.build_landing_snapshot import latest_round_regions

    def row(region, date, pop):
        return {"admin1_name": region, "reference_period_start": date, "population": pop}

    rows = [
        # A was huge early, small now; B is the reverse: the mean ranks A first.
        row("A", "2025-01-31", 900), row("A", "2025-09-30", 100),
        row("B", "2025-01-31", 100), row("B", "2025-09-30", 500),
        row("C", "2025-09-30", 300),
        row("A", "2025-09-30", 50),          # second row, same round: summed (aggregation "sum")
    ]
    out = latest_round_regions(rows, by_key("idps"), "2025-09-30", n=2)
    assert out == [["B", 500], ["C", 300]]


def _ref(host, date, pop):
    return {"asylum_location_name": host, "reference_period_start": date, "population": pop}


def test_latest_by_host_ranks_the_latest_round_and_sums_same_round_rows():
    from scripts.build_landing_snapshot import latest_by_host

    rows = [
        _ref("A", "2024-01-01T00:00:00", 900), _ref("B", "2024-01-01T00:00:00", 100),
        _ref("A", "2025-01-01T00:00:00", 100), _ref("B", "2025-01-01T00:00:00", 400),
        _ref("C", "2025-01-01T00:00:00", 300), _ref("B", "2025-01-01T00:00:00", 50),
    ]
    assert latest_by_host(rows, n=2) == [["B", 450], ["C", 300]]


def test_latest_by_host_is_none_without_rows_or_host_names():
    from scripts.build_landing_snapshot import latest_by_host

    assert latest_by_host([]) is None
    assert latest_by_host([{"reference_period_start": "2025-01-01", "population": 5}]) is None


def test_funding_by_year_sums_periods_in_the_same_calendar_year():
    from scripts.build_landing_snapshot import funding_by_year

    out = funding_by_year(["2024-01-01", "2024-01-01T00:00:00", "2025-01-01"], [1.234, 2.0, 5.0])
    assert out == [[2024, 3.23], [2025, 5.0]]


def test_pct_change_is_first_to_last():
    from scripts.build_landing_snapshot import pct_change

    assert pct_change([200.0, 150.0]) == -25.0
    assert pct_change([5.0]) is None


def test_syria_keeps_the_refugees_series(monkeypatch):
    import scripts.build_landing_snapshot as snap
    from analytics.indicators import by_key

    periods = [f"{y}-01-01T00:00:00" for y in range(2017, 2026)]
    values = [100.0, 200.0, 300.0, 400.0, 900.0, 800.0, 700.0, 650.0, 600.0]  # peak 2021

    def fake_series(key, date_from, today, iso3=snap.SUDAN):
        return by_key(key), periods, values, []

    monkeypatch.setattr(snap, "_series", fake_series)
    out = snap._syria({"count": 3, "since": "2025-11-18"})
    assert out["refugees"]["series"] == [[p[:10], round(v)] for p, v in zip(periods, values)]
    assert out["trend"]["period"] == ["2021-01-01", "2025-01-01"]
