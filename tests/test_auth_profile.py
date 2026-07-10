"""Tests for the profile endpoints: PATCH /auth/me, POST /auth/me/password,
DELETE /auth/me (api/routes/auth.py)."""
import pytest
from fastapi.testclient import TestClient

# Exercise the real cookie auth, not the get_current_user test override.
pytestmark = pytest.mark.real_auth


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


SIGNUP = {"email": "alice@example.com", "password": "password123", "name": "Alice"}


# --- PATCH /auth/me -----------------------------------------------------------

def test_update_name(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.patch("/auth/me", json={"name": "  Alice Renamed  "})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Alice Renamed"
    assert client.get("/auth/me").json()["name"] == "Alice Renamed"


def test_update_name_blank_rejected(client):
    client.post("/auth/signup", json=SIGNUP)
    assert client.patch("/auth/me", json={"name": "   "}).status_code == 422


def test_update_name_requires_auth(client):
    assert client.patch("/auth/me", json={"name": "X"}).status_code == 401


# --- POST /auth/me/password -----------------------------------------------------

def test_change_password_success_and_old_password_dies(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/me/password",
                    json={"current_password": "password123", "new_password": "brand-new-pw9"})
    assert r.status_code == 204, r.text
    client.post("/auth/logout")
    assert client.post("/auth/login",
                       json={"email": SIGNUP["email"], "password": "password123"}).status_code == 401
    assert client.post("/auth/login",
                       json={"email": SIGNUP["email"], "password": "brand-new-pw9"}).status_code == 200


def test_change_password_wrong_current_403(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/me/password",
                    json={"current_password": "WRONG", "new_password": "brand-new-pw9"})
    assert r.status_code == 403


def test_change_password_keeps_current_session_drops_others(client):
    """The session that changed the password stays; other sessions are dropped."""
    from rag import users as users_store

    client.post("/auth/signup", json=SIGNUP)
    uid = client.get("/auth/me").json()["id"]
    other_token = users_store.create_session(uid)   # a second device
    r = client.post("/auth/me/password",
                    json={"current_password": "password123", "new_password": "brand-new-pw9"})
    assert r.status_code == 204
    assert client.get("/auth/me").json() is not None            # current session alive
    assert users_store.get_user_by_session(other_token) is None  # other device out


def test_change_password_google_only_400(client):
    from rag import users as users_store

    user = users_store.get_or_create_google_user("g-sub-1", "goog@example.com", "Goog")
    token = users_store.create_session(user["id"])
    from config import get_settings
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, token)
    r = client.post("/auth/me/password",
                    json={"current_password": "irrelevant1", "new_password": "brand-new-pw9"})
    assert r.status_code == 400


def test_change_password_short_new_rejected(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/me/password",
                    json={"current_password": "password123", "new_password": "short"})
    assert r.status_code == 422
