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
    fake_token = {"userinfo": {"sub": "google-123", "email": "guser@example.com", "name": "G User"}}
    with patch("api.routes.auth.oauth.google.authorize_access_token",
               new=AsyncMock(return_value=fake_token)):
        r = client.get("/auth/google/callback", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "/app" in r.headers["location"]

    # The session cookie set by the callback now authenticates the user.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "guser@example.com"


def test_google_login_returns_503_when_unconfigured(client):
    with patch("api.routes.auth.get_settings", return_value=MagicMock(GOOGLE_CLIENT_ID="")):
        r = client.get("/auth/google/login", follow_redirects=False)
        assert r.status_code == 503
