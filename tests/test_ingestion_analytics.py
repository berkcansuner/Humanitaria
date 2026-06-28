"""Tests for the pure reports-list helpers + cache persistence (ingestion/analytics.py)."""
from unittest.mock import patch

import pytest

from ingestion import analytics
from ingestion.analytics import (
    build_documents, slice_documents, DOC_FIELDS, DEFAULT_PAGE, MAX_PAGE,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """The reports cache is a module global; give each test a clean slate."""
    analytics._state = analytics.ReportsCache()
    yield
    analytics._state = analytics.ReportsCache()


# --- build_documents (reports list rows, newest-first) ----------------------

def test_build_documents_newest_first():
    docs = build_documents([
        {"date": "2024-01-05", "title": "A"},
        {"date": "2024-03-22", "title": "B"},
        {"date": "2023-11-01", "title": "C"},
    ])
    assert [d["date"] for d in docs] == ["2024-03-22", "2024-01-05", "2023-11-01"]


def test_build_documents_tie_break_title_case_insensitive():
    docs = build_documents([
        {"date": "2024-01-01", "title": "banana"},
        {"date": "2024-01-01", "title": "Apple"},
        {"date": "2024-01-01", "title": "cherry"},
    ])
    assert [d["title"] for d in docs] == ["Apple", "banana", "cherry"]


def test_build_documents_missing_date_sorts_last():
    docs = build_documents([
        {"date": "", "title": "no date"},
        {"date": "2024-01-01", "title": "dated"},
    ])
    assert [d["title"] for d in docs] == ["dated", "no date"]


def test_build_documents_keeps_only_doc_fields_and_coerces_none():
    [row] = build_documents([{
        "date": "2024-01-01", "title": "T", "url": "u", "source": "S",
        "country": None, "doc_id": "id1", "theme": "Health", "date_ts": 20240101,
    }])
    assert set(row) == set(DOC_FIELDS)          # no theme/date_ts leak
    assert row["country"] == ""                 # None → ""


# --- slice_documents (filter + paginate) ------------------------------------

def _rows(n):
    return build_documents(
        [{"title": f"t{i:02d}", "date": "2024-01-01", "doc_id": f"d{i}"} for i in range(n)]
    )


def test_slice_documents_paginates_with_full_total():
    rows = _rows(10)
    page = slice_documents(rows, offset=0, limit=3)
    assert page["total"] == 10
    assert len(page["items"]) == 3
    assert [r["doc_id"] for r in page["items"]] == ["d0", "d1", "d2"]
    last = slice_documents(rows, offset=9, limit=3)
    assert last["total"] == 10
    assert [r["doc_id"] for r in last["items"]] == ["d9"]   # partial last page


def test_slice_documents_search_filters_title_source_country():
    rows = build_documents([
        {"title": "Flood report", "source": "OCHA", "country": "Sudan", "date": "2024-03-01", "doc_id": "a"},
        {"title": "Drought update", "source": "WFP", "country": "Yemen", "date": "2024-02-01", "doc_id": "b"},
    ])
    assert [r["doc_id"] for r in slice_documents(rows, q="FLOOD")["items"]] == ["a"]   # title, case-insensitive
    assert [r["doc_id"] for r in slice_documents(rows, q="wfp")["items"]] == ["b"]     # source
    assert [r["doc_id"] for r in slice_documents(rows, q="yemen")["items"]] == ["b"]   # country
    assert slice_documents(rows, q="zzz")["total"] == 0


def test_slice_documents_clamps_offset_and_limit():
    rows = _rows(5)
    out = slice_documents(rows, offset=-5, limit=9999)
    assert out["offset"] == 0
    assert out["limit"] == MAX_PAGE
    assert slice_documents(rows, limit=0)["limit"] == 1


def test_slice_documents_empty_query_returns_all():
    out = slice_documents(_rows(7), q="", limit=DEFAULT_PAGE)
    assert out["total"] == 7
    assert len(out["items"]) == 7


# --- disk persistence round-trip --------------------------------------------

def test_cache_persist_round_trip(tmp_path):
    cache = tmp_path / ".reports_cache.json"
    docs = build_documents([
        {"date": "2024-02-01", "title": "B", "doc_id": "b"},
        {"date": "2024-03-01", "title": "A", "doc_id": "a"},
    ])
    with patch.object(analytics, "_cache_path", return_value=cache):
        analytics._state = analytics.ReportsCache(
            documents=docs, computed_at="2024-03-02T00:00:00+00:00", namespace="ns")
        analytics._save_cache()
        assert cache.exists()
        analytics._state = analytics.ReportsCache()   # simulate a restart
        analytics.load_persisted()
    assert [d["doc_id"] for d in analytics._state.documents] == ["a", "b"]   # newest-first preserved
    assert analytics._state.computed_at == "2024-03-02T00:00:00+00:00"
    assert analytics._state.namespace == "ns"


def test_load_persisted_missing_file_is_noop(tmp_path):
    with patch.object(analytics, "_cache_path", return_value=tmp_path / "nope.json"):
        analytics.load_persisted()
    assert analytics._state.documents is None
