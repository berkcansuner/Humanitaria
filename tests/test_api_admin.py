"""Tests for the admin ingestion endpoints (api/routes/admin.py) + admin auth helpers."""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ingestion import runner
from ingestion import analytics


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_reports_cache():
    """The reports cache is a module global (like runner._state); give each test a
    clean slate so cases don't leak into one another."""
    analytics._state = analytics.ReportsCache()
    yield
    analytics._state = analytics.ReportsCache()


def _admin_settings(emails):
    s = MagicMock()
    s.ADMIN_EMAILS = emails
    return s


def _cron_settings(token):
    s = MagicMock()
    s.INGEST_TRIGGER_TOKEN = token
    return s


# --- auth helpers -----------------------------------------------------------

def test_is_admin_email_allowlist():
    from api.routes import auth
    with patch.object(auth, "get_settings", return_value=_admin_settings("Admin@Example.com, other@x.com")):
        assert auth._is_admin_email("admin@example.com") is True   # case-insensitive
        assert auth._is_admin_email("OTHER@X.COM") is True
        assert auth._is_admin_email("nope@example.com") is False
        assert auth._is_admin_email("") is False


def test_user_out_sets_is_admin():
    from api.routes import auth
    with patch.object(auth, "get_settings", return_value=_admin_settings("a@b.com")):
        assert auth._user_out({"id": "1", "email": "a@b.com", "name": "A"}).is_admin is True
        assert auth._user_out({"id": "2", "email": "c@d.com", "name": "C"}).is_admin is False


# --- /admin/ingest/status ---------------------------------------------------

def test_status_forbidden_for_non_admin(client):
    # _auth_override authenticates as test@example.com; empty ADMIN_EMAILS → 403.
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("")):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 403


@pytest.mark.real_auth
def test_status_unauthenticated(client):
    # No auth override + no cookie → 401 from get_current_user (runs before admin check).
    assert client.get("/admin/ingest/status").status_code == 401


def test_status_ok_for_admin(client, tmp_path):
    mock_store = MagicMock()
    mock_store.namespace = ""   # the namespace the app queries (default)
    mock_store.index.describe_index_stats.return_value = {
        "total_vector_count": 123,
        "namespaces": {"": {"vector_count": 100}, "v2": {"vector_count": 23}},
    }
    wm = tmp_path / ".last_ingest.json"
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.get_store", return_value=mock_store), \
         patch("ingestion.scheduler._watermark_path", return_value=wm):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 200
    body = r.json()
    assert body["namespace"] == ""
    assert body["namespace_vectors"] == 100   # active namespace, not the 123 index-wide total
    assert body["total_vectors"] == 123
    assert body["vector_count_error"] is None
    assert body["scheduler_active"] is False        # lifespan not run under TestClient()
    assert set(body) >= {"last_ingest", "next_scheduled_run", "scheduler_active",
                         "namespace", "namespace_vectors", "total_vectors",
                         "vector_count_error", "run"}
    assert body["run"]["running"] is False


def test_status_vector_error_does_not_500(client, tmp_path):
    wm = tmp_path / ".last_ingest.json"
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.get_store", side_effect=RuntimeError("pinecone down")), \
         patch("ingestion.scheduler._watermark_path", return_value=wm):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 200
    body = r.json()
    assert body["total_vectors"] is None
    assert body["namespace_vectors"] is None
    assert "pinecone down" in body["vector_count_error"]


# --- /admin/ingest/trigger --------------------------------------------------

def test_trigger_forbidden_for_non_admin(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("")):
        r = client.post("/admin/ingest/trigger")
    assert r.status_code == 403


def test_trigger_conflict_when_running(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.runner.is_running", return_value=True):
        r = client.post("/admin/ingest/trigger")
    assert r.status_code == 409


def test_trigger_starts_when_idle(client):
    # Hold the runner lock so the background task the route spawns is a guaranteed
    # no-op (run_ingest_once returns False without touching the pipeline) whenever the
    # event loop schedules it — keeps the test off the network and deterministic.
    assert runner._lock.acquire(blocking=False)
    try:
        runner._state.running = False  # route's pre-check must see idle
        with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
            r = client.post("/admin/ingest/trigger")
        assert r.status_code == 202
        assert r.json() == {"status": "started"}
    finally:
        runner._lock.release()


# --- ingestion.rebuild_documents (the reports scan) -------------------------

def test_rebuild_documents_scans_zero_chunks_and_caches(tmp_path):
    mock_store = MagicMock()
    mock_store.namespace = ""
    mock_store.index.list.return_value = [["docA_0", "docA_1", "docB_0"], ["docC_0"]]
    meta = {
        "docA_0": {"source": "OCHA", "country": "Sudan", "date": "2024-01-05", "doc_id": "docA"},
        "docB_0": {"source": "WFP", "country": "Yemen", "date": "2024-02-10", "doc_id": "docB"},
        "docC_0": {"source": "OCHA", "country": "Sudan", "date": "2023-12-01", "doc_id": "docC"},
    }

    def _fetch(ids, namespace):
        return SimpleNamespace(vectors={i: SimpleNamespace(metadata=meta[i]) for i in ids})

    mock_store.index.fetch.side_effect = _fetch
    cache = tmp_path / ".reports_cache.json"
    with patch("ingestion.analytics.get_store", return_value=mock_store), \
         patch.object(analytics, "_cache_path", return_value=cache):
        assert analytics.rebuild_documents() is True

    # Only the _0 chunk of each doc is fetched (docA_1 is filtered out before fetch).
    fetched = [i for call in mock_store.index.fetch.call_args_list for i in call.kwargs["ids"]]
    assert "docA_1" not in fetched
    assert set(fetched) == {"docA_0", "docB_0", "docC_0"}

    # One scan (index.list once), list newest-first, cache persisted to disk.
    assert mock_store.index.list.call_count == 1
    assert [d["doc_id"] for d in analytics._state.documents] == ["docB", "docA", "docC"]
    assert analytics._state.computed_at is not None
    assert analytics._state.last_error is None
    assert cache.exists()


def test_rebuild_documents_records_error_and_keeps_data(tmp_path):
    mock_store = MagicMock()
    mock_store.namespace = ""
    mock_store.index.list.side_effect = RuntimeError("pinecone list failed")
    with patch("ingestion.analytics.get_store", return_value=mock_store), \
         patch.object(analytics, "_cache_path", return_value=tmp_path / "c.json"):
        assert analytics.rebuild_documents() is True
    assert "pinecone list failed" in analytics._state.last_error
    assert analytics._state.documents is None
    assert analytics._state.computing is False


# --- /admin/ingest/documents ------------------------------------------------

def test_documents_forbidden_for_non_admin(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("")):
        assert client.get("/admin/ingest/documents").status_code == 403


def test_documents_lazy_triggers_build_when_empty(client):
    # Empty cache + idle → the GET schedules a background build and reports computing.
    # Hold the analytics lock so the scheduled rebuild is a guaranteed no-op (returns
    # False without scanning Pinecone) whenever the loop runs it — off the network.
    assert analytics._lock.acquire(blocking=False)
    try:
        with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
            r = client.get("/admin/ingest/documents")
        assert r.status_code == 200
        body = r.json()
        assert body["computing"] is True
        assert body["items"] == []
        assert body["total"] == 0
    finally:
        analytics._lock.release()


def test_documents_no_trigger_when_already_computing(client):
    analytics._state.computing = True   # a scan is already running
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.analytics.rebuild_documents") as mock_rebuild:
        r = client.get("/admin/ingest/documents")
    assert r.status_code == 200
    assert r.json()["computing"] is True
    mock_rebuild.assert_not_called()


def test_documents_paging_and_search_from_cache(client):
    # Seed the cache directly so the lazy trigger does not fire (documents is not None).
    analytics._state.documents = analytics.build_documents([
        {"title": "Flood report", "source": "OCHA", "country": "Sudan", "date": "2024-03-01", "doc_id": "a", "url": "https://x/a"},
        {"title": "Drought update", "source": "WFP", "country": "Yemen", "date": "2024-02-01", "doc_id": "b", "url": ""},
        {"title": "Cholera brief", "source": "WHO", "country": "Sudan", "date": "2024-01-01", "doc_id": "c", "url": ""},
    ])
    analytics._state.computed_at = "2024-03-02T00:00:00+00:00"
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
        page = client.get("/admin/ingest/documents?offset=0&limit=2").json()
        assert page["total"] == 3
        assert page["computing"] is False                          # cache present → no rebuild
        assert [d["doc_id"] for d in page["items"]] == ["a", "b"]   # newest-first window
        page2 = client.get("/admin/ingest/documents?offset=2&limit=2").json()
        assert [d["doc_id"] for d in page2["items"]] == ["c"]       # partial last page
        by_country = client.get("/admin/ingest/documents?q=sudan").json()
        assert [d["doc_id"] for d in by_country["items"]] == ["a", "c"]


# --- /admin/ingest/cron (token-gated automation trigger) --------------------

def test_cron_forbidden_without_token(client):
    # INGEST_TRIGGER_TOKEN empty → endpoint disabled (403) even with a header.
    with patch("api.routes.admin.get_settings", return_value=_cron_settings("")):
        assert client.post("/admin/ingest/cron").status_code == 403
        assert client.post("/admin/ingest/cron", headers={"X-Cron-Token": "x"}).status_code == 403


def test_cron_forbidden_wrong_token(client):
    with patch("api.routes.admin.get_settings", return_value=_cron_settings("secret")):
        r = client.post("/admin/ingest/cron", headers={"X-Cron-Token": "nope"})
    assert r.status_code == 403


def test_cron_runs_with_valid_token(client):
    # Hold the runner lock so the spawned run_ingest_once is a guaranteed no-op.
    assert runner._lock.acquire(blocking=False)
    try:
        runner._state.running = False
        with patch("api.routes.admin.get_settings", return_value=_cron_settings("secret")):
            r = client.post("/admin/ingest/cron", headers={"X-Cron-Token": "secret"})
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "skipped")
    finally:
        runner._lock.release()


# --- rebuild_documents + retention integration ------------------------------

def test_rebuild_documents_applies_retention(tmp_path):
    mock_store = MagicMock()
    mock_store.namespace = ""
    mock_store.index.list.return_value = [["old_0", "new_0"]]
    meta = {
        "old_0": {"doc_id": "old", "date": "2020-01-01", "country": "Sudan"},
        "new_0": {"doc_id": "new", "date": "2026-06-01", "country": "Sudan"},
    }

    def _fetch(ids, namespace):
        return SimpleNamespace(vectors={i: SimpleNamespace(metadata=meta[i]) for i in ids})

    mock_store.index.fetch.side_effect = _fetch
    s = MagicMock()
    s.RETENTION_DAYS = 365
    s.RETENTION_PER_COUNTRY_CAP = 0
    cache = tmp_path / ".reports_cache.json"
    with patch("ingestion.analytics.get_store", return_value=mock_store), \
         patch("ingestion.analytics.get_settings", return_value=s), \
         patch.object(analytics, "_cache_path", return_value=cache):
        assert analytics.rebuild_documents(apply_retention=True) is True

    # 'old' (2020) is past the 1-year window → its chunks deleted, cache keeps only 'new'.
    mock_store.delete_document_chunks.assert_any_call("old")
    assert [d["doc_id"] for d in analytics._state.documents] == ["new"]
