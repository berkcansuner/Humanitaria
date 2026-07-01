"""Google OAuth login. Authlib's network calls are mocked — no real Google."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

pytestmark = pytest.mark.real_auth


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def test_google_callback_creates_user_and_logs_in(client):
    # Exercise the real _google_userinfo glue, mocking only authlib's leaf calls:
    # state lookup + code→token exchange + the userinfo endpoint (NOT id_token /
    # JWKS, which we deliberately stopped using).
    fake_userinfo = {"sub": "google-123", "email": "guser@example.com", "name": "G User", "email_verified": True}
    with patch("api.routes.auth.oauth.google.framework.get_state_data",
               new=AsyncMock(return_value={"redirect_uri": "http://test/auth/google/callback"})), \
         patch("api.routes.auth.oauth.google.framework.clear_state_data", new=AsyncMock()), \
         patch("api.routes.auth.oauth.google.fetch_access_token",
               new=AsyncMock(return_value={"access_token": "tok"})), \
         patch("api.routes.auth.oauth.google.userinfo",
               new=AsyncMock(return_value=fake_userinfo)):
        r = client.get("/auth/google/callback?code=abc&state=xyz", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "/app" in r.headers["location"]

    # The session cookie set by the callback now authenticates the user.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "guser@example.com"


def _patch_userinfo(fake_userinfo):
    """Patch authlib's leaf calls so google_callback resolves to *fake_userinfo*."""
    return [
        patch("api.routes.auth.oauth.google.framework.get_state_data",
              new=AsyncMock(return_value={"redirect_uri": "http://test/auth/google/callback"})),
        patch("api.routes.auth.oauth.google.framework.clear_state_data", new=AsyncMock()),
        patch("api.routes.auth.oauth.google.fetch_access_token",
              new=AsyncMock(return_value={"access_token": "tok"})),
        patch("api.routes.auth.oauth.google.userinfo",
              new=AsyncMock(return_value=fake_userinfo)),
    ]


def test_google_callback_rejects_unverified_email(client):
    """A Google account whose email is not verified must NOT be linked/created —
    otherwise it could hijack an existing password account with the same email."""
    import contextlib
    fake = {"sub": "g-unv", "email": "attacker@example.com", "name": "X", "email_verified": False}
    with contextlib.ExitStack() as stack:
        for p in _patch_userinfo(fake):
            stack.enter_context(p)
        r = client.get("/auth/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/login" in r.headers["location"]
    assert "error=google" in r.headers["location"]


def test_google_callback_rejects_missing_email_verified(client):
    """Fail closed: if the userinfo omits email_verified, treat it as unverified."""
    import contextlib
    fake = {"sub": "g-missing", "email": "someone@example.com", "name": "Y"}
    with contextlib.ExitStack() as stack:
        for p in _patch_userinfo(fake):
            stack.enter_context(p)
        r = client.get("/auth/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/login" in r.headers["location"]
    assert "error=google" in r.headers["location"]


def test_google_callback_db_error_redirects_not_500(client):
    """A DB race on account create/link (concurrent callbacks → IntegrityError) must
    degrade to the login redirect, honouring the callback's 'never 500' contract."""
    import contextlib
    import sqlite3
    fake = {"sub": "g-race", "email": "race@example.com", "name": "R", "email_verified": True}
    with contextlib.ExitStack() as stack:
        for p in _patch_userinfo(fake):
            stack.enter_context(p)
        stack.enter_context(patch(
            "api.routes.auth.users_store.get_or_create_google_user",
            side_effect=sqlite3.IntegrityError("UNIQUE constraint failed"),
        ))
        r = client.get("/auth/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/login" in r.headers["location"]
    assert "error=google" in r.headers["location"]


def test_google_login_returns_503_when_unconfigured(client):
    with patch("api.routes.auth.get_settings", return_value=MagicMock(GOOGLE_CLIENT_ID="")):
        r = client.get("/auth/google/login", follow_redirects=False)
        assert r.status_code == 503


def test_google_callback_failure_redirects_to_login_not_500(client):
    """A failed OAuth exchange (wrong secret, lost state, unreachable Google host)
    must degrade to a friendly redirect, not a blank 500."""
    from authlib.integrations.starlette_client import OAuthError

    with patch("api.routes.auth._google_userinfo",
               new=AsyncMock(side_effect=OAuthError("invalid_client", "bad secret"))):
        r = client.get("/auth/google/callback?code=x&state=y", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/login" in r.headers["location"]
    assert "error=google" in r.headers["location"]
