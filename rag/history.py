import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Union

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

from config import get_settings

if TYPE_CHECKING:
    # Imported lazily at runtime (only when REDIS_URL is set); declared here so the
    # return-type forward reference resolves for linters/type-checkers.
    from langchain_community.chat_message_histories import RedisChatMessageHistory

logger = logging.getLogger(__name__)

# Bounded in-memory session store with LRU eviction.
# OrderedDict preserves insertion order; move_to_end marks recent access.
_session_histories: OrderedDict[str, "WindowedChatMessageHistory"] = OrderedDict()


class WindowedChatMessageHistory(InMemoryChatMessageHistory):
    """In-memory chat history with a sliding window of k exchanges."""

    k: int = 5

    def add_message(self, message: BaseMessage) -> None:
        super().add_message(message)
        max_messages = self.k * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]


def _get_memory_history(session_id: str, k: int, max_sessions: int) -> WindowedChatMessageHistory:
    """Return (or create) an in-memory session, evicting the LRU entry if at capacity."""
    if session_id in _session_histories:
        _session_histories.move_to_end(session_id)
        return _session_histories[session_id]
    if len(_session_histories) >= max_sessions:
        oldest_key, _ = _session_histories.popitem(last=False)
        logger.debug("Evicted in-memory session %s (max=%d)", oldest_key, max_sessions)
    history = WindowedChatMessageHistory(k=k)
    _session_histories[session_id] = history
    return history


def get_session_history(session_id: str) -> Union[WindowedChatMessageHistory, "RedisChatMessageHistory"]:
    settings = get_settings()
    k = settings.HISTORY_WINDOW_K
    max_sessions = settings.SESSION_MAX_MEMORY

    if settings.REDIS_URL:
        try:
            from langchain_community.chat_message_histories import RedisChatMessageHistory
            return RedisChatMessageHistory(
                session_id,
                url=settings.REDIS_URL,
                ttl=settings.SESSION_TTL_HOURS * 3600,
            )
        except Exception as e:
            logger.warning("Redis session unavailable, falling back to in-memory: %s", e)

    return _get_memory_history(session_id, k, max_sessions)


def has_session(session_id: str) -> bool:
    """True if an in-memory window already exists for this session.

    Used by the chat route to decide whether to seed the window from the
    persistent store on a cold request (e.g. after a server restart)."""
    return session_id in _session_histories


def clear_session(session_id: str) -> None:
    _session_histories.pop(session_id, None)


def populate_history_from_messages(session_id: str, messages: list) -> None:
    settings = get_settings()
    history = WindowedChatMessageHistory(k=settings.HISTORY_WINDOW_K)
    for msg in messages:
        history.add_message(msg)
    _session_histories[session_id] = history
    # Keep under the memory cap
    while len(_session_histories) > settings.SESSION_MAX_MEMORY:
        _session_histories.popitem(last=False)
