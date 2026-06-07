"""IDOR regression: a user can only see/modify conversations they own.

These exercise the REAL cookie auth (no get_current_user override), so each
TestClient carries its own session and the ownership checks are enforced
end-to-end.
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.real_auth


def _signup(email):
    from api.main import app
    c = TestClient(app)
    c.post("/auth/signup", json={"email": email, "password": "password123", "name": email})
    return c


def test_unauthenticated_requests_are_blocked():
    from api.main import app
    anon = TestClient(app)
    assert anon.get("/conversations").status_code == 401


def test_user_cannot_list_others_conversations():
    alice = _signup("alice@example.com")
    bob = _signup("bob@example.com")
    alice.post("/conversations", json={"title": "Alice's private chat"})

    assert alice.get("/conversations").json() != []
    assert bob.get("/conversations").json() == []


def test_user_cannot_read_modify_or_delete_others_conversation():
    alice = _signup("alice2@example.com")
    bob = _signup("bob2@example.com")
    conv_id = alice.post("/conversations", json={"title": "secret"}).json()["id"]

    assert bob.get(f"/conversations/{conv_id}/messages").status_code == 404
    assert bob.patch(f"/conversations/{conv_id}", json={"title": "hacked"}).status_code == 404
    assert bob.delete(f"/conversations/{conv_id}").status_code == 404
    assert bob.post(f"/conversations/{conv_id}/truncate", json={"keep_through_message_id": 0}).status_code == 404

    # Alice's conversation is untouched.
    assert alice.get(f"/conversations/{conv_id}/messages").status_code == 200
    assert alice.get("/conversations").json()[0]["title"] == "secret"
