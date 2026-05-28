import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from rag.history import (
    WindowedChatMessageHistory,
    get_session_history,
    clear_session,
    populate_history_from_messages,
    _session_histories,
)


def _mock_settings(k=5, max_sessions=1000, redis_url=""):
    s = MagicMock()
    s.HISTORY_WINDOW_K = k
    s.SESSION_MAX_MEMORY = max_sessions
    s.REDIS_URL = redis_url
    s.SESSION_TTL_HOURS = 24
    return s


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
        with patch("rag.history.get_settings", return_value=_mock_settings()):
            history = get_session_history("test-session")
            assert isinstance(history, WindowedChatMessageHistory)

    def test_get_session_history_same_id_same_object(self):
        with patch("rag.history.get_settings", return_value=_mock_settings()):
            h1 = get_session_history("same-id")
            h2 = get_session_history("same-id")
            assert h1 is h2

    def test_get_session_history_different_id_different_object(self):
        with patch("rag.history.get_settings", return_value=_mock_settings()):
            h1 = get_session_history("id-1")
            h2 = get_session_history("id-2")
            assert h1 is not h2

    def test_clear_session_removes_session(self):
        with patch("rag.history.get_settings", return_value=_mock_settings()):
            get_session_history("to-clear")
        clear_session("to-clear")
        assert "to-clear" not in _session_histories

    def test_clear_session_nonexistent_no_error(self):
        clear_session("nonexistent")

    def test_populate_history_from_messages(self):
        with patch("rag.history.get_settings", return_value=_mock_settings()):
            msgs = [
                HumanMessage(content="hello"),
                AIMessage(content="hi"),
            ]
            populate_history_from_messages("populated", msgs)
            history = get_session_history("populated")
            assert len(history.messages) == 2

    def test_lru_eviction_at_capacity(self):
        """Oldest session is evicted when SESSION_MAX_MEMORY is reached."""
        with patch("rag.history.get_settings", return_value=_mock_settings(max_sessions=3)):
            get_session_history("s1")
            get_session_history("s2")
            get_session_history("s3")
            assert len(_session_histories) == 3

            get_session_history("s4")  # should evict "s1" (least recently used)
            assert "s1" not in _session_histories
            assert len(_session_histories) == 3

    def test_lru_recently_accessed_not_evicted(self):
        """Accessing a session marks it as recently used so it is not evicted first."""
        with patch("rag.history.get_settings", return_value=_mock_settings(max_sessions=3)):
            get_session_history("s1")
            get_session_history("s2")
            get_session_history("s3")
            get_session_history("s1")  # re-access s1 → now most recent
            get_session_history("s4")  # should evict "s2" (now the oldest)
            assert "s1" in _session_histories
            assert "s2" not in _session_histories

    def test_history_uses_configured_window_k(self):
        """WindowedChatMessageHistory respects HISTORY_WINDOW_K from settings."""
        with patch("rag.history.get_settings", return_value=_mock_settings(k=2)):
            h = get_session_history("k-test")
            assert isinstance(h, WindowedChatMessageHistory)
            assert h.k == 2
