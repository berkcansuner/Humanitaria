"""Conversational query rewriting (follow-up resolution).

A follow-up like "what about the north?" or "ya kuzeyde?" is meaningless to the
retriever on its own. Given the prior turns, rewrite it into a standalone query
so retrieval inherits the conversation's subject (country, topic, timeframe).

Only the RETRIEVAL query is rewritten; the answer is still generated from the
user's original message. Falls back to the original message on any error or when
there is no history.
"""
import logging

from config import get_settings

logger = logging.getLogger(__name__)

_HISTORY_TURNS = 6  # last N messages fed as context

_REWRITE_PROMPT = (
    "Given the conversation so far and a follow-up message, rewrite the follow-up "
    "as a standalone search query that makes sense without the conversation. "
    "Keep the user's language. Preserve country, topic and timeframe from context. "
    "If the message is already standalone, return it unchanged. "
    "Return ONLY the rewritten query, nothing else.\n\n"
    "Conversation:\n{history}\n\nFollow-up: {question}\nStandalone query:"
)

_rewriter = None


def _get_rewriter():
    global _rewriter
    if _rewriter is None:
        from langchain_openai import ChatOpenAI
        s = get_settings()
        _rewriter = ChatOpenAI(
            model=s.GEMINI_QUERY_MODEL,
            base_url=s.GEMINI_BASE_URL,
            api_key=s.GEMINI_API_KEY,
            temperature=0.0,
            timeout=5,
        )
    return _rewriter


def _format_history(messages) -> str:
    lines = []
    for m in messages[-_HISTORY_TURNS:]:
        role = "User" if getattr(m, "type", "") == "human" else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


def rewrite_query(message: str, chat_history: list, llm=None) -> str:
    """Resolve a follow-up into a standalone retrieval query. Returns the original
    message unchanged when there is no history or on any failure."""
    if not chat_history:
        return message
    llm = llm or _get_rewriter()
    try:
        resp = llm.invoke(
            _REWRITE_PROMPT.format(history=_format_history(chat_history), question=message)
        )
        rewritten = getattr(resp, "content", str(resp)).strip()
        return rewritten or message
    except Exception as e:
        logger.warning("Query rewrite failed, using original message: %s", e)
        return message
