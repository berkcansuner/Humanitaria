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
