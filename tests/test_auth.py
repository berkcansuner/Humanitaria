"""Tests for the email/password auth endpoints (api/routes/auth.py)."""
import pytest
from fastapi.testclient import TestClient

# Exercise the real cookie auth, not the get_current_user test override.
pytestmark = pytest.mark.real_auth


@pytest.fixture
def client():
    # _isolate_conversation_db (autouse) points the user store at a temp DB.
    from api.main import app
    return TestClient(app)


SIGNUP = {"email": "alice@example.com", "password": "password123", "name": "Alice"}


def test_signup_returns_user(client):
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert "id" in body
    assert "password" not in body and "password_hash" not in body


def test_signup_sets_session_cookie(client):
    from config import get_settings

    r = client.post("/auth/signup", json=SIGNUP)
    assert get_settings().SESSION_COOKIE_NAME in r.cookies


def test_signup_duplicate_email_conflicts(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/signup", json={**SIGNUP, "name": "Other"})
    assert r.status_code == 409


def test_signup_short_password_rejected(client):
    r = client.post("/auth/signup", json={**SIGNUP, "password": "short"})
    assert r.status_code == 422


def test_login_success(client):
    client.post("/auth/signup", json=SIGNUP)
    client.post("/auth/logout")  # drop the signup session/cookie
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == SIGNUP["email"]


def test_login_wrong_password_unauthorized(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"})
    assert r.status_code == 401


def test_login_unknown_email_unauthorized(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert r.status_code == 401


def test_login_unknown_email_still_runs_password_check(client):
    """Timing-attack guard (İK2-2b): bcrypt verification runs even when the email
    is unknown, so login latency can't reveal which emails are registered."""
    from unittest.mock import patch
    with patch("api.routes.auth.users_store.verify_password", return_value=False) as vp:
        r = client.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever123"})
    assert r.status_code == 401
    assert vp.called  # bcrypt ran despite no such user (constant-time login)


def test_me_requires_authentication(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user_after_signup(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.get("/auth/me")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == SIGNUP["email"]


def test_logout_invalidates_session(client):
    client.post("/auth/signup", json=SIGNUP)
    assert client.get("/auth/me").status_code == 200
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401


class TestAuthRateLimit:
    """İK2-2a: signup/login are rate-limited per client IP to blunt brute-force
    and signup spam. Uses the shared limiter (api.limiter), enabled only for this
    test — it is disabled by default so other tests aren't throttled."""

    def test_login_is_rate_limited(self, client):
        from unittest.mock import patch, MagicMock
        from api.limiter import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            with patch("api.routes.auth.get_settings",
                       return_value=MagicMock(AUTH_LOGIN_RATE_LIMIT="1/minute")):
                creds = {"email": "nobody@example.com", "password": "password123"}
                first = client.post("/auth/login", json=creds)
                second = client.post("/auth/login", json=creds)
            assert first.status_code == 401   # unknown user, but the attempt still counts
            assert second.status_code == 429  # second attempt within the window is throttled
        finally:
            limiter.reset()
            limiter.enabled = False

    def test_signup_is_rate_limited(self, client):
        from unittest.mock import patch, MagicMock
        from api.limiter import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            with patch("api.routes.auth.get_settings",
                       return_value=MagicMock(AUTH_SIGNUP_RATE_LIMIT="1/minute",
                                              SESSION_TTL_HOURS=24,
                                              SESSION_COOKIE_NAME="rw_session",
                                              SESSION_COOKIE_SECURE=False)):
                first = client.post("/auth/signup", json={"email": "rl1@example.com", "password": "password123", "name": "RL"})
                second = client.post("/auth/signup", json={"email": "rl2@example.com", "password": "password123", "name": "RL"})
            assert first.status_code == 200, first.text
            assert second.status_code == 429
        finally:
            limiter.reset()
            limiter.enabled = False
