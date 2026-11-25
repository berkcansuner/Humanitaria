"""The SPA shell (index.html) must never be cached by the browser.

Without an explicit Cache-Control header browsers apply heuristic caching (based
on Last-Modified), so after a deploy a user's tab keeps a stale index.html that
references hashed chunks which no longer exist → lazy routes (e.g. /reports)
404 and the click silently does nothing. `no-cache` forces revalidation (ETag →
304 when unchanged), while /assets/* stays content-hashed and cacheable.

The SPA is mounted on a fresh app over a temporary dist dir, so these run in CI
(which does not build frontend/dist) instead of being skipped.
"""
import os

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


def test_etag_tracks_content_even_when_size_and_mtime_are_unchanged(client, tmp_path):
    # Vite's shell is the same size every build; a deploy that preserves mtimes
    # must still produce a new ETag, or browsers get 304 for the old shell.
    shell = tmp_path / "index.html"
    old_etag = client.get("/").headers["etag"]
    st = shell.stat()
    shell.write_text(_SHELL.replace("abc123", "def456"), encoding="utf-8")
    os.utime(shell, ns=(st.st_atime_ns, st.st_mtime_ns))
    r = client.get("/reports", headers={"If-None-Match": old_etag})
    assert r.status_code == 200
    assert "index-def456.js" in r.text
    assert r.headers["etag"] != old_etag


def test_direct_index_html_request_gets_the_same_shell_handling(client):
    etag = client.get("/").headers["etag"]
    assert client.get("/index.html", headers={"If-None-Match": etag}).status_code == 304


def test_other_dist_files_are_served_with_no_cache(client, tmp_path):
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    r = client.get("/favicon.svg")
    assert r.status_code == 200
    assert r.text == "<svg/>"
    assert r.headers.get("cache-control") == "no-cache"


def test_shell_missing_mid_rebuild_returns_503_not_500(client, tmp_path):
    (tmp_path / "index.html").unlink()
    r = client.get("/app")
    assert r.status_code == 503
    assert r.headers.get("retry-after")


def test_dist_without_index_html_is_not_mounted(tmp_path):
    (tmp_path / "assets").mkdir()
    app = FastAPI()
    mount_spa(app, tmp_path)
    assert TestClient(app).get("/app").status_code == 404


def test_hashed_assets_are_not_marked_no_cache(client):
    r = client.get("/assets/index-abc123.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") != "no-cache"


# A route with its own prerendered page (dist/privacy.html: the shell plus the page's
# text in <noscript>, for readers that do not run JavaScript, like Google's OAuth
# brand check) gets that page, with the same revalidation as the shell.
_PRIVACY = _SHELL + "<noscript>Privacy policy</noscript>"


@pytest.fixture
def client_with_page(client, tmp_path):
    (tmp_path / "privacy.html").write_text(_PRIVACY, encoding="utf-8")
    return client


def test_route_with_its_own_page_gets_that_page(client_with_page):
    r = client_with_page.get("/privacy")
    assert r.status_code == 200
    assert r.text == _PRIVACY
    assert r.headers.get("cache-control") == "no-cache"
    etag = r.headers["etag"]
    assert client_with_page.get("/privacy", headers={"If-None-Match": etag}).status_code == 304


def test_routes_without_a_page_still_get_the_shell(client_with_page):
    assert client_with_page.get("/app").text == _SHELL
    assert client_with_page.get("/privacy/x").text == _SHELL


def test_page_lookup_cannot_escape_dist(client_with_page, tmp_path):
    (tmp_path.parent / "secret.html").write_text("secret", encoding="utf-8")
    assert client_with_page.get("/..%2fsecret").text == _SHELL
