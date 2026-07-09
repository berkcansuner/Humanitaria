"""Security regression tests for the SPA catch-all fallback (api/main.py).

Guards against P1-01: the catch-all `GET /{full_path:path}` must never serve a
file outside frontend/dist. These drive the ASGI app with a RAW, un-normalized
path (containing `..`) directly, because a normal HTTP client (httpx/TestClient)
collapses `..` before it reaches the app — which would hide the vulnerability.
uvicorn does NOT collapse dot segments, so this faithfully models a real attacker
(`curl --path-as-is` / percent-encoded `..%2f`).
"""
import asyncio

from api.main import app


def _raw_get(raw_path: str):
    """Send a GET with an un-normalized path straight to the ASGI app and return
    (status, body_bytes)."""
    async def _call():
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode("latin-1"),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")],
            "server": ("testserver", 80),
            "client": ("testclient", 12345),
        }
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        status = next(m["status"] for m in sent if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
        return status, body

    return asyncio.run(_call())


def test_spa_fallback_blocks_traversal_to_source():
    """`/../../config.py` must not disclose application source."""
    _status, body = _raw_get("/../../config.py")
    assert b"DEFAULT_SESSION_SECRET" not in body, "path traversal served config.py"


def test_spa_fallback_blocks_traversal_to_requirements():
    """A second target outside the SPA dir must also be blocked."""
    _status, body = _raw_get("/../../requirements.txt")
    assert b"langchain" not in body, "path traversal served requirements.txt"


def test_spa_fallback_serves_index_for_client_route():
    """A normal (non-existent) client route still returns the SPA shell (200)."""
    status, body = _raw_get("/some-client-route")
    assert status == 200
    assert b"<" in body  # HTML index.html, not an error
