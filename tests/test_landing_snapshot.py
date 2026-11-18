from scripts.build_landing_snapshot import coverage_points, top_regions


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
