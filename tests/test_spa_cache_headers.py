"""The SPA shell (index.html) must never be cached by the browser.

Without an explicit Cache-Control header browsers apply heuristic caching (based
on Last-Modified), so after a deploy a user's tab keeps a stale index.html that
references hashed chunks which no longer exist → lazy routes (e.g. /reports)
404 and the click silently does nothing. `no-cache` forces revalidation (ETag →
304 when unchanged), while /assets/* stays content-hashed and cacheable.

The SPA is mounted on a fresh app over a temporary dist dir, so these run in CI
(which does not build frontend/dist) instead of being skipped.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import mount_spa

_SHELL = '<!doctype html><script type="module" src="/assets/index-abc123.js"></script>'


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text(_SHELL, encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    app = FastAPI()
    mount_spa(app, tmp_path)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/app", "/reports", "/some-client-route"])
def test_spa_shell_is_served_with_no_cache(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.text == _SHELL
    assert r.headers.get("cache-control") == "no-cache"
    assert r.headers.get("etag")


def test_revalidation_with_matching_etag_returns_304(client):
    etag = client.get("/reports").headers["etag"]
    r = client.get("/reports", headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.content == b""
    assert r.headers.get("etag") == etag
    assert r.headers.get("cache-control") == "no-cache"


def test_weak_etag_and_lists_match(client):
    etag = client.get("/").headers["etag"]
    assert client.get("/", headers={"If-None-Match": f'"other", W/{etag}'}).status_code == 304


def test_stale_etag_gets_the_full_shell(client):
    r = client.get("/app", headers={"If-None-Match": '"from-the-previous-deploy"'})
    assert r.status_code == 200
    assert r.text == _SHELL


def test_hashed_assets_are_not_marked_no_cache(client):
    r = client.get("/assets/index-abc123.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") != "no-cache"
