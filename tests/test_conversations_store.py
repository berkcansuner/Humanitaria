"""Tests for the SQLite conversation store (rag/conversations.py)."""
import pytest
from unittest.mock import MagicMock, patch

from rag import conversations as store

U = "user-1"  # owning user for single-user fixtures


@pytest.fixture
def db(tmp_path):
    """Point the store at a throwaway SQLite file for the duration of a test."""
    settings = MagicMock()
    settings.DATABASE_URL = ""
    settings.CONVERSATION_DB_PATH = str(tmp_path / "conversations.db")
    with patch("rag.db.get_settings", return_value=settings):
        yield


def test_create_and_exists(db):
    assert store.conversation_exists("c1") is False
    store.create_conversation(U, "c1", "İlk sohbet")
    assert store.conversation_exists("c1") is True


def test_create_is_idempotent(db):
    store.create_conversation(U, "c1", "Başlık A")
    store.create_conversation(U, "c1", "Başlık B")  # ignored
    rows = store.list_conversations(U)
    assert len(rows) == 1
    assert rows[0]["title"] == "Başlık A"


def test_is_owner(db):
    store.create_conversation(U, "c1", "t")
    assert store.is_owner(U, "c1") is True
    assert store.is_owner("someone-else", "c1") is False
    assert store.is_owner(U, "nonexistent") is False


def test_list_is_scoped_to_user(db):
    store.create_conversation(U, "c1", "Mine")
    store.create_conversation("other-user", "c2", "Theirs")
    assert [c["id"] for c in store.list_conversations(U)] == ["c1"]
    assert [c["id"] for c in store.list_conversations("other-user")] == ["c2"]


def test_append_and_get_messages(db):
    store.create_conversation(U, "c1", "t")
    store.append_message("c1", "user", "Soru?")
    store.append_message("c1", "assistant", "Cevap.", sources=[{"index": 1, "title": "Doc"}])
    msgs = store.get_messages("c1")
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["sources"] is None
    assert msgs[1]["sources"] == [{"index": 1, "title": "Doc"}]


def test_append_bumps_updated_at_for_ordering(db):
    store.create_conversation(U, "old", "Eski")
    store.create_conversation(U, "new", "Yeni")
    store.append_message("old", "user", "later activity")  # bumps old's updated_at
    ids = [c["id"] for c in store.list_conversations(U)]
    assert ids[0] == "old"  # most recently updated first


def test_rename(db):
    store.create_conversation(U, "c1", "Eski ad")
    store.rename_conversation("c1", "Yeni ad")
    assert store.list_conversations(U)[0]["title"] == "Yeni ad"


def test_delete_cascades_messages(db):
    store.create_conversation(U, "c1", "t")
    store.append_message("c1", "user", "x")
    store.delete_conversation("c1")
    assert store.conversation_exists("c1") is False
    assert store.get_messages("c1") == []


def test_delete_last_assistant(db):
    store.create_conversation(U, "c1", "t")
    store.append_message("c1", "user", "q1")
    store.append_message("c1", "assistant", "a1")
    store.delete_last_assistant("c1")
    msgs = store.get_messages("c1")
    assert [m["role"] for m in msgs] == ["user"]


def test_truncate_after(db):
    store.create_conversation(U, "c1", "t")
    store.append_message("c1", "user", "q1")
    store.append_message("c1", "assistant", "a1")
    store.append_message("c1", "user", "q2")
    keep_id = store.get_messages("c1")[0]["id"]  # the first user message
    store.truncate_after("c1", keep_id)
    msgs = store.get_messages("c1")
    assert [m["content"] for m in msgs] == ["q1"]


def test_messages_as_langchain(db):
    store.create_conversation(U, "c1", "t")
    store.append_message("c1", "user", "merhaba")
    store.append_message("c1", "assistant", "selam")
    lc = store.messages_as_langchain("c1")
    assert [type(m).__name__ for m in lc] == ["HumanMessage", "AIMessage"]
    assert lc[0].content == "merhaba"
