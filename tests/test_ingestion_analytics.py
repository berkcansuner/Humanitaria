"""Tests for the pure breakdown aggregation (ingestion/analytics.py)."""
from ingestion.analytics import aggregate_breakdown, TOP_N, UNKNOWN


def test_counts_per_dimension():
    docs = [
        {"source": "OCHA", "country": "Sudan", "theme": "Health", "format": "Situation Report", "date": "2024-03-10"},
        {"source": "OCHA", "country": "Sudan", "theme": "Food", "format": "News", "date": "2024-03-22"},
        {"source": "WFP", "country": "Yemen", "theme": "Food", "format": "News", "date": "2023-11-01"},
    ]
    out = aggregate_breakdown(docs)
    assert out["total_documents"] == 3
    assert {r["key"]: r["count"] for r in out["by_source"]["items"]} == {"OCHA": 2, "WFP": 1}
    assert {r["key"]: r["count"] for r in out["by_country"]["items"]} == {"Sudan": 2, "Yemen": 1}
    assert {r["key"]: r["count"] for r in out["by_format"]["items"]} == {"News": 2, "Situation Report": 1}
    assert {r["year"]: r["count"] for r in out["by_year"]} == {"2024": 2, "2023": 1}


def test_rank_summary_replaces_other_bar():
    # 17 distinct sources, 1 doc each → top 15 items + tail summary, NO synthetic (other) row.
    docs = [{"source": f"org{i:02d}", "date": "2024-01-01"} for i in range(17)]
    rank = aggregate_breakdown(docs)["by_source"]
    assert len(rank["items"]) == TOP_N
    assert rank["distinct"] == 17
    assert rank["tail_count"] == 2
    assert all(r["key"].startswith("org") for r in rank["items"])  # no "(other)" key


def test_rank_no_tail_when_within_top_n():
    docs = [{"source": f"org{i}", "date": "2024-01-01"} for i in range(5)]
    rank = aggregate_breakdown(docs)["by_source"]
    assert rank["distinct"] == 5
    assert rank["tail_count"] == 0
    assert len(rank["items"]) == 5


def test_missing_fields_go_to_unknown():
    out = aggregate_breakdown([{"date": ""}, {"source": "", "country": None}])
    assert {r["key"]: r["count"] for r in out["by_source"]["items"]}[UNKNOWN] == 2
    assert {r["key"]: r["count"] for r in out["by_country"]["items"]}[UNKNOWN] == 2
    assert {r["year"]: r["count"] for r in out["by_year"]}[UNKNOWN] == 2


def test_years_newest_first_and_grouped_before_min_year():
    docs = (
        [{"date": "2026-01-01"}] * 2
        + [{"date": "2024-05-01"}] * 3
        + [{"date": "2019-01-01"}] * 4   # before min_year 2021 → grouped
        + [{"date": "2010-01-01"}]       # before min_year → grouped
    )
    years = aggregate_breakdown(docs, min_year=2021)["by_year"]
    assert years == [
        {"year": "2026", "count": 2},
        {"year": "2024", "count": 3},
        {"year": "before 2021", "count": 5},
    ]


def test_years_ungrouped_when_no_min_year():
    docs = [{"date": "2026-01-01"}, {"date": "2010-01-01"}]
    years = aggregate_breakdown(docs)["by_year"]
    assert years == [{"year": "2026", "count": 1}, {"year": "2010", "count": 1}]


def test_deterministic_tie_break_by_key_asc():
    items = aggregate_breakdown([{"source": "b"}, {"source": "a"}])["by_source"]["items"]
    assert [r["key"] for r in items] == ["a", "b"]


def test_empty_input():
    out = aggregate_breakdown([])
    assert out["total_documents"] == 0
    assert out["by_source"] == {"items": [], "distinct": 0, "tail_count": 0}
    assert out["by_year"] == []
