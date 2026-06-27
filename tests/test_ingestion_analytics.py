"""Tests for the pure breakdown aggregation (ingestion/analytics.py)."""
from ingestion.analytics import aggregate_breakdown, TOP_N, OTHER, UNKNOWN


def test_counts_per_dimension():
    docs = [
        {"source": "OCHA", "country": "Sudan", "theme": "Health", "format": "Situation Report", "date": "2024-03-10"},
        {"source": "OCHA", "country": "Sudan", "theme": "Food", "format": "News", "date": "2024-03-22"},
        {"source": "WFP", "country": "Yemen", "theme": "Food", "format": "News", "date": "2023-11-01"},
    ]
    out = aggregate_breakdown(docs)
    assert out["total_documents"] == 3
    assert {r["key"]: r["count"] for r in out["by_source"]} == {"OCHA": 2, "WFP": 1}
    assert {r["key"]: r["count"] for r in out["by_country"]} == {"Sudan": 2, "Yemen": 1}
    assert {r["key"]: r["count"] for r in out["by_format"]} == {"News": 2, "Situation Report": 1}
    assert {r["month"]: r["count"] for r in out["by_month"]} == {"2024-03": 2, "2023-11": 1}
    assert {r["year"]: r["count"] for r in out["by_year"]} == {"2024": 2, "2023": 1}


def test_top_n_folds_remainder_into_other():
    # 17 distinct sources, 1 doc each → top 15 + one (other) row with the trailing 2.
    docs = [{"source": f"org{i:02d}", "date": "2024-01-01"} for i in range(17)]
    rows = aggregate_breakdown(docs)["by_source"]
    assert len(rows) == TOP_N + 1
    assert rows[-1] == {"key": OTHER, "count": 2}


def test_no_other_row_when_within_top_n():
    docs = [{"source": f"org{i}", "date": "2024-01-01"} for i in range(5)]
    rows = aggregate_breakdown(docs)["by_source"]
    assert all(r["key"] != OTHER for r in rows)


def test_missing_fields_go_to_unknown():
    out = aggregate_breakdown([{"date": ""}, {"source": "", "country": None}])
    assert {r["key"]: r["count"] for r in out["by_source"]}[UNKNOWN] == 2
    assert {r["key"]: r["count"] for r in out["by_country"]}[UNKNOWN] == 2
    assert {r["month"]: r["count"] for r in out["by_month"]}[UNKNOWN] == 2
    assert {r["year"]: r["count"] for r in out["by_year"]}[UNKNOWN] == 2


def test_months_sorted_chronologically_unknown_last():
    docs = [{"date": "2024-05-01"}, {"date": "2023-01-01"}, {"date": ""}]
    months = [r["month"] for r in aggregate_breakdown(docs)["by_month"]]
    assert months == ["2023-01", "2024-05", UNKNOWN]


def test_deterministic_tie_break_by_key_asc():
    rows = aggregate_breakdown([{"source": "b"}, {"source": "a"}])["by_source"]
    assert [r["key"] for r in rows] == ["a", "b"]


def test_empty_input():
    out = aggregate_breakdown([])
    assert out["total_documents"] == 0
    assert out["by_source"] == []
    assert out["by_month"] == []
