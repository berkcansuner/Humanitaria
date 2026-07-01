"""/health: cheap liveness by default, dependency readiness with ?deep=true."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def test_health_liveness_is_cheap(client):
    # Default probe must NOT touch Pinecone/DB (Render polls this frequently).
    with patch("api.routes.health._check_pinecone") as pc, \
         patch("api.routes.health._check_database") as db:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
        pc.assert_not_called()
        db.assert_not_called()


def test_health_deep_ok(client):
    with patch("api.routes.health._check_pinecone", return_value=True), \
         patch("api.routes.health._check_database", return_value=True):
        r = client.get("/health?deep=true")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"] == {"pinecone": "ok", "database": "ok"}


def test_health_deep_reports_503_when_pinecone_down(client):
    with patch("api.routes.health._check_pinecone", side_effect=RuntimeError("pinecone down")), \
         patch("api.routes.health._check_database", return_value=True):
        r = client.get("/health?deep=true")
        assert r.status_code == 503
        checks = r.json()["detail"]["checks"]
        assert checks["pinecone"] == "error"
        assert checks["database"] == "ok"


def test_health_deep_reports_503_when_db_down(client):
    with patch("api.routes.health._check_pinecone", return_value=True), \
         patch("api.routes.health._check_database", side_effect=RuntimeError("db down")):
        r = client.get("/health?deep=true")
        assert r.status_code == 503
        assert r.json()["detail"]["checks"]["database"] == "error"
