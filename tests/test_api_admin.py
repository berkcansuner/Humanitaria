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
        assert auth._user_out({"id": "1", "email": "a@b.com", "name": "A", "google_sub": "g1"}).is_admin is True
        assert auth._user_out({"id": "2", "email": "c@d.com", "name": "C", "google_sub": "g2"}).is_admin is False


def test_admin_requires_google_verified_identity():
    """Password signup never proves mailbox ownership, so an allowlisted email on a
    password-only account (no google_sub) must not carry admin authority."""
    from api.routes import auth
    with patch.object(auth, "get_settings", return_value=_admin_settings("a@b.com")):
        assert auth._user_out({"id": "1", "email": "a@b.com", "name": "A"}).is_admin is False


@pytest.mark.real_auth
def test_signup_with_admin_email_is_refused(client):
    with patch("api.routes.auth.get_settings") as gs:
        gs.return_value = _admin_settings("boss@example.com")
        gs.return_value.SESSION_TTL_HOURS = 1
        gs.return_value.SESSION_COOKIE_NAME = "rw_session"
        gs.return_value.SESSION_COOKIE_SECURE = False
        gs.return_value.AUTH_SIGNUP_RATE_LIMIT = "1000/minute"
        r = client.post("/auth/signup", json={"email": "Boss@Example.com",
                                              "password": "pw-12345678", "name": "X"})
    assert r.status_code == 409
    assert "rw_session" not in r.cookies


def test_admin_user_list_badge_requires_google_link(client):
    from rag import users as users_store
    users_store.create_user("boss@example.com", "Pre-registered", password="pw-12345678")
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("boss@example.com, test@example.com")):
        r = client.get("/admin/users")
    assert r.status_code == 200
    row = next(u for u in r.json()["users"] if u["email"] == "boss@example.com")
    assert row["is_admin"] is False


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


def test_status_ok_for_admin(client):
    mock_store = MagicMock()
    mock_store.counts.return_value = {"chunks": 120, "documents": 40}
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.get_store", return_value=mock_store):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 200
    body = r.json()
    assert (body["chunk_count"], body["document_count"]) == (120, 40)
    assert body["vector_count_error"] is None
    assert body["scheduler_active"] is False        # lifespan not run under TestClient()
    assert set(body) >= {"last_ingest", "next_scheduled_run", "scheduler_active",
                         "chunk_count", "document_count", "vector_count_error", "run"}
    assert body["run"]["running"] is False


def test_status_vector_error_does_not_500(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")), \
         patch("api.routes.admin.get_store", side_effect=RuntimeError("db down")):
        r = client.get("/admin/ingest/status")
    assert r.status_code == 200
    body = r.json()
    assert body["chunk_count"] is None and body["document_count"] is None
    assert "db down" in body["vector_count_error"]


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


# --- /admin/ingest/documents ------------------------------------------------

def test_documents_forbidden_for_non_admin(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("")):
        assert client.get("/admin/ingest/documents").status_code == 403


def test_documents_empty_index(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
        r = client.get("/admin/ingest/documents")
    assert r.status_code == 200
    assert r.json()["items"] == [] and r.json()["total"] == 0


def test_documents_paging_and_search(client):
    from rag.db import connect
    from sqlalchemy import text
    with connect() as conn:
        conn.execute(text(
            "INSERT INTO documents (doc_id, title, url, source, country, doctype, date, updated_at) "
            "VALUES (:doc_id, :title, :url, :source, :country, 'report', :date, 'now')"), [
            {"doc_id": "a", "title": "Flood report", "source": "OCHA", "country": "Sudan", "date": "2024-03-01", "url": "https://x/a"},
            {"doc_id": "b", "title": "Drought update", "source": "WFP", "country": "Yemen", "date": "2024-02-01", "url": ""},
            {"doc_id": "c", "title": "Cholera brief", "source": "WHO", "country": "Sudan", "date": "2024-01-01", "url": ""},
        ])
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
        page = client.get("/admin/ingest/documents?offset=0&limit=2").json()
        assert page["total"] == 3
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
        assert r.status_code == 202
        assert r.json()["status"] == "started"
    finally:
        runner._lock.release()


def test_cron_already_running_returns_409(client):
    runner._state.running = True
    try:
        with patch("api.routes.admin.get_settings", return_value=_cron_settings("secret")):
            r = client.post("/admin/ingest/cron", headers={"X-Cron-Token": "secret"})
        assert r.status_code == 409
        assert r.json()["status"] == "already-running"
    finally:
        runner._state.running = False


# --- /admin/users ----------------------------------------------------------------

def test_admin_users_forbidden_for_non_admin(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("")):
        assert client.get("/admin/users").status_code == 403


@pytest.mark.real_auth
def test_admin_users_unauthenticated(client):
    assert client.get("/admin/users").status_code == 401


def test_admin_users_lists_with_admin_badge_and_search(client):
    from rag import users as users_store

    users_store.get_or_create_google_user("g-boss", "boss@example.com", "Boss")
    users_store.create_user("member@example.com", "Member", password="pw-123456")
    with patch("api.routes.auth.get_settings",
               return_value=_admin_settings("test@example.com, boss@example.com")):
        r = client.get("/admin/users")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2
        by_email = {u["email"]: u for u in body["users"]}
        assert by_email["boss@example.com"]["is_admin"] is True
        assert by_email["member@example.com"]["is_admin"] is False
        assert "password_hash" not in by_email["boss@example.com"]

        r = client.get("/admin/users", params={"q": "member"})
        assert r.json()["total"] == 1


def test_admin_users_pagination_params_validated(client):
    with patch("api.routes.auth.get_settings", return_value=_admin_settings("test@example.com")):
        assert client.get("/admin/users", params={"limit": 500}).status_code == 422
        assert client.get("/admin/users", params={"offset": -1}).status_code == 422
