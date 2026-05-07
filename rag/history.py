import logging
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

_session_histories: dict[str, "WindowedChatMessageHistory"] = {}


class WindowedChatMessageHistory(InMemoryChatMessageHistory):
    """In-memory chat history with a sliding window of k exchanges."""

    k: int = 5

    def add_message(self, message: BaseMessage) -> None:
        super().add_message(message)
        max_messages = self.k * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]


def get_session_history(session_id: str) -> WindowedChatMessageHistory:
    if session_id not in _session_histories:
        _session_histories[session_id] = WindowedChatMessageHistory(k=5)
    return _session_histories[session_id]


def clear_session(session_id: str) -> None:
    _session_histories.pop(session_id, None)


def populate_history_from_messages(session_id: str, messages: list[BaseMessage]) -> None:
    history = WindowedChatMessageHistory(k=5)
    for msg in messages:
        history.add_message(msg)
    _session_histories[session_id] = history