"""Persistent conversation store (SQLite).

Holds the named conversations and their messages that back the sidebar. Plain
stdlib ``sqlite3`` — file-based, survives restart, no extra infra.

All functions are synchronous; FastAPI routes offload them with
``anyio.to_thread.run_sync`` so the event loop is not blocked. A fresh
connection is opened per call (WAL mode for concurrent reads).
"""
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from config import get_settings

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    conn = sqlite3.connect(get_settings().CONVERSATION_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            title      TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            sources_json    TEXT,
            created_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
        """
    )
    # Migrate pre-auth DBs that lack the owner column (legacy rows get user_id
    # NULL → invisible to every user, which is the safe default).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
    )


def create_conversation(user_id: str, conv_id: str, title: str) -> None:
    """Insert a conversation owned by user_id; idempotent (existing id is left
    untouched)."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations(id, user_id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (conv_id, user_id, title, now, now),
        )


def conversation_exists(conv_id: str) -> bool:
    """True if a conversation with this id exists for ANY user (used to detect
    id collisions). Ownership is checked with is_owner."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
    return row is not None


def is_owner(user_id: str, conv_id: str) -> bool:
    """True only if conv_id exists AND belongs to user_id."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id),
        ).fetchone()
    return row is not None


def list_conversations(user_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_messages(conv_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, role, content, sources_json, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
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
        cur = conn.execute(
            "INSERT INTO messages(conversation_id, role, content, sources_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (conv_id, role, content, sources_json, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id)
        )
        return cur.lastrowid


def rename_conversation(conv_id: str, title: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), conv_id),
        )


def delete_conversation(conv_id: str) -> None:
    """Delete a conversation and (via CASCADE) its messages."""
    with _connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def delete_last_assistant(conv_id: str) -> None:
    """Drop the most recent assistant message (used by Regenerate)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM messages WHERE conversation_id = ? AND role = 'assistant' "
            "ORDER BY id DESC LIMIT 1",
            (conv_id,),
        ).fetchone()
        if row:
            conn.execute("DELETE FROM messages WHERE id = ?", (row["id"],))


def truncate_after(conv_id: str, message_id: int) -> None:
    """Delete every message after `message_id` (used by Edit/resend)."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM messages WHERE conversation_id = ? AND id > ?",
            (conv_id, message_id),
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
