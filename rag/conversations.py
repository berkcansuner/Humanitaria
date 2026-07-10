"""Persistent conversation store.

Holds the named conversations and their messages that back the sidebar. Plain
SQL through the shared engine in ``rag/db.py`` — SQLite file by default
(survives restart, no extra infra), Postgres when ``DATABASE_URL`` is set.

All functions are synchronous; FastAPI routes offload them with
``anyio.to_thread.run_sync`` so the event loop is not blocked.
"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import text

from rag.db import connect as _connect

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_conversation(user_id: str, conv_id: str, title: str) -> None:
    """Insert a conversation owned by user_id; idempotent (existing id is left
    untouched)."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            text(
                "INSERT INTO conversations(id, user_id, title, created_at, updated_at) "
                "VALUES (:id, :uid, :title, :now, :now) ON CONFLICT DO NOTHING"
            ),
            {"id": conv_id, "uid": user_id, "title": title, "now": now},
        )


def conversation_exists(conv_id: str) -> bool:
    """True if a conversation with this id exists for ANY user (used to detect
    id collisions). Ownership is checked with is_owner."""
    with _connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM conversations WHERE id = :id"), {"id": conv_id}
        ).fetchone()
    return row is not None


def is_owner(user_id: str, conv_id: str) -> bool:
    """True only if conv_id exists AND belongs to user_id."""
    with _connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM conversations WHERE id = :id AND user_id = :uid"),
            {"id": conv_id, "uid": user_id},
        ).fetchone()
    return row is not None


def list_conversations(user_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE user_id = :uid ORDER BY updated_at DESC"
            ),
            {"uid": user_id},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_messages(conv_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, role, content, sources_json, created_at FROM messages "
                "WHERE conversation_id = :cid ORDER BY id"
            ),
            {"cid": conv_id},
        ).mappings().fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d.pop("sources_json")) if d.get("sources_json") else None
        result.append(d)
    return result


def append_message(conv_id: str, role: str, content: str, sources=None) -> int:
    """Append a message, bump updated_at, and return the new message id."""
    now = _now()
    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
    with _connect() as conn:
        msg_id = conn.execute(
            text(
                "INSERT INTO messages(conversation_id, role, content, sources_json, created_at) "
                "VALUES (:cid, :role, :content, :sources, :now) RETURNING id"
            ),
            {"cid": conv_id, "role": role, "content": content,
             "sources": sources_json, "now": now},
        ).scalar_one()
        conn.execute(
            text("UPDATE conversations SET updated_at = :now WHERE id = :id"),
            {"now": now, "id": conv_id},
        )
        return msg_id


def rename_conversation(conv_id: str, title: str) -> None:
    with _connect() as conn:
        conn.execute(
            text("UPDATE conversations SET title = :title, updated_at = :now WHERE id = :id"),
            {"title": title, "now": _now(), "id": conv_id},
        )


def delete_conversation(conv_id: str) -> None:
    """Delete a conversation and (via CASCADE) its messages."""
    with _connect() as conn:
        conn.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conv_id})


def delete_last_assistant(conv_id: str) -> None:
    """Drop the most recent assistant message (used by Regenerate)."""
    with _connect() as conn:
        row = conn.execute(
            text(
                "SELECT id FROM messages WHERE conversation_id = :cid AND role = 'assistant' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"cid": conv_id},
        ).fetchone()
        if row:
            conn.execute(text("DELETE FROM messages WHERE id = :id"), {"id": row[0]})


def truncate_after(conv_id: str, message_id: int) -> None:
    """Delete every message after `message_id` (used by Edit/resend)."""
    with _connect() as conn:
        conn.execute(
            text("DELETE FROM messages WHERE conversation_id = :cid AND id > :mid"),
            {"cid": conv_id, "mid": message_id},
        )


def messages_as_langchain(conv_id: str) -> list[BaseMessage]:
    """Map stored rows to LangChain messages for seeding the in-memory window."""
    msgs: list[BaseMessage] = []
    for m in get_messages(conv_id):
        if m["role"] == "user":
            msgs.append(HumanMessage(content=m["content"]))
        else:
            msgs.append(AIMessage(content=m["content"]))
    return msgs


def resync_window(conv_id: str) -> None:
    """Rebuild the in-memory window from the (possibly trimmed) persisted
    messages so the LLM never sees stale context after a truncate."""
    from rag.history import clear_session, populate_history_from_messages

    clear_session(conv_id)
    populate_history_from_messages(conv_id, messages_as_langchain(conv_id))
