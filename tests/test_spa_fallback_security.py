"""Security regression tests for the SPA catch-all fallback (api/main.py).

Guards P1-01: the catch-all must never serve a file outside frontend/dist.

The containment decision lives in the pure helper `_safe_spa_file`, so the core
regression guard runs deterministically in ANY environment (including CI, which
does not build frontend/dist). The traversal targets (config.py, requirements.txt)
exist at the repo root and resolve OUTSIDE the dist dir → the helper must return
None. If the containment check were removed, these would return a real path and
the tests would fail.
"""
import asyncio

import pytest

from api.main import _safe_spa_file, frontend_dir


# --- deterministic unit tests on the containment helper (run everywhere) -----

def test_helper_blocks_traversal_to_source():
    assert _safe_spa_file("../../config.py") is None


def test_helper_blocks_traversal_to_requirements():
    assert _safe_spa_file("../../requirements.txt") is None


def test_helper_blocks_deep_traversal():
    assert _safe_spa_file("../../../../etc/passwd") is None
    assert _safe_spa_file("../../conversations.db") is None


def test_helper_rejects_nonexistent_path():
    assert _safe_spa_file("no-such-file-xyz") is None


def test_helper_rejects_empty_path():
    assert _safe_spa_file("") is None


# --- end-to-end via the real ASGI route (only when the SPA is built) ---------

_HAS_DIST = (frontend_dir / "index.html").is_file()


def _raw_get(raw_path: str):
    """Send a GET with an un-normalized path straight to the ASGI app (bypassing the
    httpx/TestClient normalization that would collapse ..) and return (status, body)."""
    from api.main import app

    async def _call():
        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1", "method": "GET", "scheme": "http",
            "path": raw_path, "raw_path": raw_path.encode("latin-1"),
            "query_string": b"", "root_path": "",
            "headers": [(b"host", b"testserver")],
            "server": ("testserver", 80), "client": ("testclient", 12345),
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


@pytest.mark.skipif(not _HAS_DIST, reason="frontend/dist not built in this environment")
def test_route_blocks_traversal_and_serves_index():
    # A raw traversal path must yield the SPA shell, never the traversed file.
    _status, body = _raw_get("/../../config.py")
    assert b"DEFAULT_SESSION_SECRET" not in body
    # A normal client route still returns index.html (200).
    status, body = _raw_get("/some-client-route")
    assert status == 200
    assert b"<" in body
