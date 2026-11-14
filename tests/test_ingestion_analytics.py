"""Admin reports list, report-form countries and retention over the ``documents``
table (ingestion/analytics.py). Runs on the per-test SQLite DB from conftest."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy import text

from ingestion import analytics
from ingestion.analytics import DOC_FIELDS, MAX_PAGE
from rag.db import connect


def _insert(*rows):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(text(
            "INSERT INTO documents (doc_id, title, url, source, country, doctype, date, updated_at) "
            "VALUES (:doc_id, :title, :url, :source, :country, :doctype, :date, :updated_at)"),
            [{"title": "", "url": "", "source": "", "country": "", "doctype": "report", "date": "",
              "updated_at": now, **r} for r in rows])


def test_list_is_newest_first_with_missing_dates_last_and_title_tiebreak():
    _insert({"doc_id": "old", "date": "2024-01-01", "title": "x"},
            {"doc_id": "nodate", "date": "", "title": "a"},
            {"doc_id": "new-b", "date": "2024-03-01", "title": "beta"},
            {"doc_id": "new-a", "date": "2024-03-01", "title": "Alpha"})
    out = analytics.get_documents()
    assert [d["doc_id"] for d in out["items"]] == ["new-a", "new-b", "old", "nodate"]
    assert out["total"] == 4
    assert set(out["items"][0]) == set(DOC_FIELDS)


def test_search_matches_title_source_or_country_case_insensitively():
    _insert({"doc_id": "1", "title": "Floods in Sudan"},
            {"doc_id": "2", "source": "UNICEF"},
            {"doc_id": "3", "country": "Sudan"},
            {"doc_id": "4", "title": "Other"})
    assert {d["doc_id"] for d in analytics.get_documents(q="SUDAN")["items"]} == {"1", "3"}
    assert analytics.get_documents(q="unicef")["total"] == 1


def test_pagination_reports_full_total_and_clamps_bounds():
    _insert(*({"doc_id": f"d{i:02d}", "date": f"2024-01-{i + 1:02d}"} for i in range(12)))
    page = analytics.get_documents(offset=10, limit=5)
    assert page["total"] == 12 and len(page["items"]) == 2
    clamped = analytics.get_documents(offset=-3, limit=10_000)
    assert clamped["offset"] == 0 and clamped["limit"] == MAX_PAGE


def test_distinct_countries_sorted_without_blanks():
    _insert({"doc_id": "1", "country": "Yemen"}, {"doc_id": "2", "country": "Sudan"},
            {"doc_id": "3", "country": "Yemen"}, {"doc_id": "4", "country": ""})
    assert analytics.distinct_countries() == ["Sudan", "Yemen"]


def test_retention_off_by_default_deletes_nothing():
    _insert({"doc_id": "1", "date": "2000-01-01"})
    store = MagicMock()
    with patch("ingestion.analytics.get_settings",
               return_value=MagicMock(RETENTION_DAYS=0, RETENTION_PER_COUNTRY_CAP=0)), \
         patch("ingestion.store.get_store", return_value=store):
        assert analytics.apply_retention() == []
    store.delete_document_chunks.assert_not_called()


def test_retention_deletes_expired_and_over_cap_documents():
    recent = lambda days_ago: (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")  # noqa: E731
    _insert({"doc_id": "ancient", "date": "2000-01-01", "country": "Yemen"},
            {"doc_id": "y1", "date": recent(10), "country": "Yemen"},
            {"doc_id": "y2", "date": recent(5), "country": "Yemen"},
            {"doc_id": "s1", "date": recent(10), "country": "Sudan"})
    store = MagicMock()
    with patch("ingestion.analytics.get_settings",
               return_value=MagicMock(RETENTION_DAYS=365, RETENTION_PER_COUNTRY_CAP=1)), \
         patch("ingestion.store.get_store", return_value=store):
        deleted = analytics.apply_retention()
    assert deleted == ["ancient", "y1"]
    assert {c.args[0] for c in store.delete_document_chunks.call_args_list} == {"ancient", "y1"}
