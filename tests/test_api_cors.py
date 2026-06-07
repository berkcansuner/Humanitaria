"""CORS preflight tests.

The browser SPA (dev: :5173) calls the API cross-origin and relies on the
httpOnly session cookie, so the preflight must allow credentials and the
Content-Type header used by JSON requests.
"""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# An origin present in the default CORS_ORIGINS allow-list.
_ALLOWED_ORIGIN = "http://localhost:5173"


def test_cors_preflight_allows_content_type():
    resp = client.options(
        "/chat",
        headers={
            "Origin": _ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code == 200
    allowed = resp.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allowed


def test_cors_preflight_allows_credentials():
    resp = client.options(
        "/chat",
        headers={
            "Origin": _ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-credentials") == "true"
