"""/health: cheap liveness by default, dependency readiness with ?deep=true."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _deep_probe_as_admin(request):
    """The deep probe is admin-only; existing readiness tests run as an admin.
    Tests marked anonymous_health exercise the anonymous path instead."""
    from unittest.mock import MagicMock
    from api.main import app
    from api.routes.auth import get_optional_user
    if request.node.get_closest_marker("anonymous_health"):
        yield
        return
    settings = MagicMock()
    settings.ADMIN_EMAILS = "ops@example.com"
    app.dependency_overrides[get_optional_user] = lambda: {
        "id": "ops", "email": "ops@example.com", "name": "Ops", "google_sub": "g-ops"}
    with patch("api.routes.auth.get_settings", return_value=settings):
        yield
    app.dependency_overrides.pop(get_optional_user, None)


@pytest.mark.anonymous_health
def test_deep_probe_requires_admin(client):
    """Anonymous callers must not be able to trigger billed provider calls."""
    with patch("api.routes.health._check_database") as db, \
         patch("api.routes.health._check_gemini") as gm:
        r = client.get("/health?deep=true")
    assert r.status_code == 403
    db.assert_not_called()
    gm.assert_not_called()


@pytest.mark.anonymous_health
def test_liveness_stays_public(client):
    assert client.get("/health").status_code == 200


def test_health_liveness_is_cheap(client):
    # Default probe must NOT touch the DB (Render polls this frequently).
    with patch("api.routes.health._check_database") as db:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
        db.assert_not_called()


def test_health_deep_ok(client):
    with patch("api.routes.health._check_database", return_value=True), \
         patch("api.routes.health._check_gemini", return_value=True):
        r = client.get("/health?deep=true")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"] == {"database": "ok", "gemini": "ok"}


def test_health_deep_reports_503_when_db_down(client):
    with patch("api.routes.health._check_database", side_effect=RuntimeError("db down")), \
         patch("api.routes.health._check_gemini", return_value=True):
        r = client.get("/health?deep=true")
        assert r.status_code == 503
        assert r.json()["detail"]["checks"]["database"] == "error"


def test_health_deep_includes_gemini(client):
    with patch("api.routes.health._check_database", return_value=True), \
         patch("api.routes.health._check_gemini", return_value=True):
        r = client.get("/health?deep=true")
        assert r.status_code == 200
        assert r.json()["checks"] == {"database": "ok", "gemini": "ok"}


def test_health_deep_reports_503_when_gemini_quota_exhausted(client):
    with patch("api.routes.health._check_database", return_value=True), \
         patch("api.routes.health._check_gemini", side_effect=RuntimeError("402 credits depleted")):
        r = client.get("/health?deep=true")
        assert r.status_code == 503
        assert r.json()["detail"]["checks"]["gemini"] == "error"


def test_health_liveness_skips_gemini(client):
    with patch("api.routes.health._check_gemini") as gm:
        client.get("/health")
        gm.assert_not_called()
