"""The SPA shell (index.html) must never be cached by the browser.

Without an explicit Cache-Control header browsers apply heuristic caching (based
on Last-Modified), so after a deploy a user's tab keeps a stale index.html that
references hashed chunks which no longer exist → lazy routes (e.g. /reports)
404 and the click silently does nothing. `no-cache` forces revalidation (ETag →
304 when unchanged), while /assets/* stays content-hashed and cacheable.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app, frontend_dir

_HAS_DIST = (frontend_dir / "index.html").exists()


@pytest.mark.skipif(not _HAS_DIST, reason="frontend/dist not built in this environment")
@pytest.mark.parametrize("path", ["/app", "/reports", "/some-client-route"])
def test_spa_shell_is_served_with_no_cache(path):
    r = TestClient(app).get(path)
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"
