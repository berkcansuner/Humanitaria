"""Tests for the conversation CRUD endpoints (api/routes/conversations.py)."""
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """A TestClient with the conversation store pointed at a throwaway DB."""
    settings = MagicMock()
    settings.CONVERSATION_DB_PATH = str(tmp_path / "conversations.db")
    with patch("rag.conversations.get_settings", return_value=settings):
        from api.main import app
        yield TestClient(app)


def test_list_empty(client):
    r = client.get("/conversations")
    assert r.status_code == 200
    assert r.json() == []


def test_create_then_list(client):
    r = client.post("/conversations", json={"title": "Test sohbeti"})
    assert r.status_code == 200
    conv = r.json()
    assert conv["title"] == "Test sohbeti"
    assert conv["id"]

    listing = client.get("/conversations").json()
    assert len(listing) == 1
    assert listing[0]["id"] == conv["id"]


def test_get_messages_404_for_unknown(client):
    assert client.get("/conversations/nope/messages").status_code == 404


def test_rename(client):
    conv_id = client.post("/conversations", json={"title": "Eski"}).json()["id"]
    r = client.patch(f"/conversations/{conv_id}", json={"title": "Yeni"})
    assert r.status_code == 200
    assert r.json()["title"] == "Yeni"


def test_delete(client):
    conv_id = client.post("/conversations", json={"title": "Silinecek"}).json()["id"]
    assert client.delete(f"/conversations/{conv_id}").status_code == 204
    assert client.get("/conversations").json() == []


def test_truncate_drops_later_messages(client):
    from rag import conversations as store
    # Create through the API so the conversation is owned by the authenticated
    # (overridden) test user; the truncate route enforces ownership.
    conv_id = client.post("/conversations", json={"title": "t"}).json()["id"]
    first_user = store.append_message(conv_id, "user", "q1")
    store.append_message(conv_id, "assistant", "a1")
    store.append_message(conv_id, "user", "q2")
    r = client.post(f"/conversations/{conv_id}/truncate", json={"keep_through_message_id": first_user})
    assert r.status_code == 204
    assert [m["content"] for m in store.get_messages(conv_id)] == ["q1"]


def test_truncate_404_for_unknown(client):
    r = client.post("/conversations/nope/truncate", json={"keep_through_message_id": 0})
    assert r.status_code == 404
