"""Tests for the account interface language: users.ui_language and
PATCH /auth/me/language (api/routes/auth.py)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

# Exercise the real cookie auth, not the get_current_user test override.
pytestmark = pytest.mark.real_auth

SIGNUP = {"email": "alice@example.com", "password": "password123", "name": "Alice"}


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def test_new_user_has_no_language(client):
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.json()["ui_language"] is None


def test_patch_language_persists(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.patch("/auth/me/language", json={"ui_language": "tr"})
    assert r.status_code == 200, r.text
    assert r.json()["ui_language"] == "tr"
    assert client.get("/auth/me").json()["ui_language"] == "tr"


def test_patch_language_rejects_unsupported(client):
    client.post("/auth/signup", json=SIGNUP)
    assert client.patch("/auth/me/language", json={"ui_language": "de"}).status_code == 422


def test_patch_language_requires_auth(client):
    assert client.patch("/auth/me/language", json={"ui_language": "tr"}).status_code == 401


def test_missing_column_fails_the_save_gracefully(client, caplog):
    """If a start could not add users.ui_language (lock timeout, retried on the
    next start), sign-in and /auth/me keep working and saving the language
    answers 503 with a logged warning instead of a 500 traceback."""
    from rag.db import get_engine

    client.post("/auth/signup", json=SIGNUP)
    with get_engine().begin() as conn:
        conn.exec_driver_sql("ALTER TABLE users DROP COLUMN ui_language")
    assert client.get("/auth/me").json()["ui_language"] is None
    with caplog.at_level("WARNING", logger="api.routes.auth"):
        r = client.patch("/auth/me/language", json={"ui_language": "tr"})
    assert r.status_code == 503
    assert isinstance(r.json()["detail"], str)
    assert "language not saved" in caplog.text
    assert "Traceback" not in caplog.text


def test_schema_migration_adds_column_once(tmp_path):
    """A pre-existing users table without ui_language gains it; re-running is a no-op."""
    from rag.db import _ensure_schema

    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, "
            "name TEXT NOT NULL, password_hash TEXT, "
            "auth_provider TEXT NOT NULL DEFAULT 'password', google_sub TEXT UNIQUE, "
            "created_at TEXT NOT NULL)"
        )
    _ensure_schema(engine)
    _ensure_schema(engine)
    names = [c["name"] for c in inspect(engine).get_columns("users")]
    assert names.count("ui_language") == 1
    engine.dispose()
