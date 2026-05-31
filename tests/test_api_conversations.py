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
    store.create_conversation("c1", "t")
    first_user = store.append_message("c1", "user", "q1")
    store.append_message("c1", "assistant", "a1")
    store.append_message("c1", "user", "q2")
    r = client.post("/conversations/c1/truncate", json={"keep_through_message_id": first_user})
    assert r.status_code == 204
    assert [m["content"] for m in store.get_messages("c1")] == ["q1"]


def test_truncate_404_for_unknown(client):
    r = client.post("/conversations/nope/truncate", json={"keep_through_message_id": 0})
    assert r.status_code == 404


class TestApiKeyAuth:
    def test_requires_key_when_configured(self, tmp_path):
        convo_settings = MagicMock()
        convo_settings.CONVERSATION_DB_PATH = str(tmp_path / "c.db")
        auth_settings = MagicMock()
        auth_settings.API_KEY = "secret"
        with patch("rag.conversations.get_settings", return_value=convo_settings), \
             patch("api.routes.chat.get_settings", return_value=auth_settings):
            from api.main import app
            client = TestClient(app)
            assert client.get("/conversations").status_code == 401
            ok = client.get("/conversations", headers={"X-API-Key": "secret"})
            assert ok.status_code == 200
