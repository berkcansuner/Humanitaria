import pytest
from langchain_core.messages import HumanMessage, AIMessage
from rag.history import (
    WindowedChatMessageHistory,
    get_session_history,
    clear_session,
    populate_history_from_messages,
    _session_histories,
)


class TestWindowedChatMessageHistory:
    def test_add_message_stores_message(self):
        history = WindowedChatMessageHistory(k=5)
        history.add_message(HumanMessage(content="test"))
        assert len(history.messages) == 1

    def test_window_trims_old_messages(self):
        history = WindowedChatMessageHistory(k=2)
        for i in range(5):
            history.add_message(HumanMessage(content=f"msg {i}"))
            history.add_message(AIMessage(content=f"reply {i}"))
        assert len(history.messages) == 4  # k=2 → max 4 messages

    def test_window_keeps_recent_messages(self):
        history = WindowedChatMessageHistory(k=2)
        for i in range(5):
            history.add_message(HumanMessage(content=f"msg {i}"))
            history.add_message(AIMessage(content=f"reply {i}"))
        last = history.messages[-1]
        assert "reply 4" in last.content


class TestSessionStore:
    def setup_method(self):
        _session_histories.clear()

    def test_get_session_history_creates_new(self):
        history = get_session_history("test-session")
        assert isinstance(history, WindowedChatMessageHistory)

    def test_get_session_history_same_id_same_object(self):
        h1 = get_session_history("same-id")
        h2 = get_session_history("same-id")
        assert h1 is h2

    def test_get_session_history_different_id_different_object(self):
        h1 = get_session_history("id-1")
        h2 = get_session_history("id-2")
        assert h1 is not h2

    def test_clear_session_removes_session(self):
        get_session_history("to-clear")
        clear_session("to-clear")
        assert "to-clear" not in _session_histories

    def test_clear_session_nonexistent_no_error(self):
        clear_session("nonexistent")

    def test_populate_history_from_messages(self):
        msgs = [
            HumanMessage(content="hello"),
            AIMessage(content="hi"),
        ]
        populate_history_from_messages("populated", msgs)
        history = get_session_history("populated")
        assert len(history.messages) == 2