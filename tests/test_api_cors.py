"""CORS preflight tests.

Browser clients send the optional `X-API-Key` header on authenticated requests.
The CORS preflight must allow it; otherwise, when `API_KEY` is configured, the
browser blocks every authenticated call even though non-browser clients work.
"""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# An origin present in the default CORS_ORIGINS allow-list.
_ALLOWED_ORIGIN = "http://localhost:5173"


def test_cors_preflight_allows_x_api_key_header():
    resp = client.options(
        "/chat",
        headers={
            "Origin": _ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert resp.status_code == 200
    allowed = resp.headers.get("access-control-allow-headers", "").lower()
    assert "x-api-key" in allowed


def test_cors_preflight_still_allows_content_type():
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
