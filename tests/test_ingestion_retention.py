"""Tests for rolling-window retention (ingestion/retention.py)."""
from datetime import datetime, timezone

from ingestion import retention
from ingestion.retention import select_expired, cutoff_ts_for


def _doc(doc_id, date="", country="X"):
    return {"doc_id": doc_id, "date": date, "country": country}


# --- select_expired (pure) --------------------------------------------------

def test_date_rule_drops_old_keeps_new_and_missing():
    docs = [_doc("a", "2024-01-01"), _doc("b", "2026-06-01"), _doc("c", "")]
    assert select_expired(docs, cutoff_ts=20250101, per_country_cap=0) == {"a"}


def test_cap_rule_keeps_newest_per_country():
    docs = [
        _doc("a", "2026-06-03", "Sudan"),
        _doc("b", "2026-06-02", "Sudan"),
        _doc("c", "2026-06-01", "Sudan"),   # overflow (keep newest 2)
        _doc("y", "2026-01-01", "Yemen"),   # other country, under cap
    ]
    assert select_expired(docs, cutoff_ts=0, per_country_cap=2) == {"c"}


def test_cap_rule_missing_date_sorts_oldest():
    docs = [
        _doc("a", "2026-06-03", "Sudan"),
        _doc("b", "", "Sudan"),             # missing date → oldest → dropped first
        _doc("c", "2026-06-01", "Sudan"),
    ]
    assert select_expired(docs, cutoff_ts=0, per_country_cap=2) == {"b"}


def test_both_rules_combined():
    docs = [
        _doc("old", "2020-01-01", "Sudan"),     # date-expired
        _doc("a", "2026-06-03", "Sudan"),
        _doc("b", "2026-06-02", "Sudan"),
        _doc("c", "2026-06-01", "Sudan"),       # cap overflow
    ]
    assert select_expired(docs, cutoff_ts=20250101, per_country_cap=2) == {"old", "c"}


def test_disabled_when_both_off():
    docs = [_doc("a", "2000-01-01"), _doc("b", "")]
    assert select_expired(docs, cutoff_ts=0, per_country_cap=0) == set()


# --- cutoff_ts_for ----------------------------------------------------------

def test_cutoff_ts_for():
    now = datetime(2026, 6, 28, tzinfo=timezone.utc)
    assert cutoff_ts_for(365, now=now) == 20250628
    assert cutoff_ts_for(0, now=now) == 0
    assert cutoff_ts_for(-5, now=now) == 0


# --- apply_retention (deletes via the store) --------------------------------

class _FakeStore:
    def __init__(self):
        self.deleted = []

    def delete_document_chunks(self, doc_id):
        self.deleted.append(doc_id)


def test_apply_retention_deletes_old_and_returns_ids():
    store = _FakeStore()
    docs = [_doc("old", "2020-01-01", "Sudan"), _doc("new", "2026-06-01", "Sudan")]
    out = retention.apply_retention(store, docs, retention_days=365, per_country_cap=0)
    assert out == ["old"]
    assert store.deleted == ["old"]


def test_apply_retention_noop_when_disabled():
    store = _FakeStore()
    assert retention.apply_retention(store, [_doc("a", "2000-01-01")],
                                     retention_days=0, per_country_cap=0) == []
    assert store.deleted == []
