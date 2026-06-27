"""Tests for the admin ingestion endpoints (api/routes/admin.py) + admin auth helpers."""
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ingestion import runner


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def _admin_settings(emails):
    s = MagicMock()
    s.ADMIN_EMAILS = emails
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
    mock_store.index.describe_index_stats.return_value = {"total_vector_count": 123}
    wm = tmp_path / ".last_ingest.json"
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.get_store", return_value=mock_store), \
         patch("ingestion.scheduler._watermark_path", return_value=wm):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 200
    body = r.json()
    assert body["total_vectors"] == 123
    assert body["vector_count_error"] is None
    assert body["scheduler_active"] is False        # lifespan not run under TestClient()
    assert set(body) >= {"last_ingest", "next_scheduled_run", "scheduler_active",
                         "total_vectors", "vector_count_error", "run"}
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
