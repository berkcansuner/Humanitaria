"""Persistent M&E report store (SQLite).

Holds the generated situation reports shown on the Reports page. Same file-based
SQLite DB as the conversation store (``CONVERSATION_DB_PATH``); a separate table
keeps the concern isolated. Mirrors ``rag/conversations.py``: synchronous, one
connection per call (WAL mode), FastAPI offloads with ``anyio.to_thread.run_sync``.
"""
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import get_settings

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    conn = sqlite3.connect(get_settings().CONVERSATION_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
        CREATE TABLE IF NOT EXISTS reports (
            id          TEXT PRIMARY KEY,
            user_id     TEXT,
            country     TEXT,
            theme       TEXT,
            date_from   TEXT,
            date_to     TEXT,
            language    TEXT,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            sources_json TEXT,
            key_figures_json TEXT,
            doc_count   INTEGER,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id, created_at);
        """
    )
    # Migration for DBs created before the key-figures panel (mirrors conversations.py).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reports)").fetchall()}
    if "key_figures_json" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN key_figures_json TEXT")


def create_report(report_id: str, user_id: str, *, country: str, theme: str | None,
                  date_from: str | None, date_to: str | None, language: str,
                  title: str, content: str, sources: list | None, doc_count: int,
                  key_figures: list | None = None) -> None:
    """Insert a generated report owned by user_id."""
    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
    key_figures_json = json.dumps(key_figures, ensure_ascii=False) if key_figures else None
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reports(id, user_id, country, theme, date_from, date_to, language, "
            "title, content, sources_json, key_figures_json, doc_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (report_id, user_id, country, theme, date_from, date_to, language,
             title, content, sources_json, key_figures_json, doc_count, _now()),
        )


def list_reports(user_id: str) -> list[dict]:
    """Lean rows for the saved-reports list (no body), newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, country, theme, date_from, date_to, language, title, doc_count, created_at "
            "FROM reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: str) -> dict | None:
    """Full report incl. body + parsed sources, or None if it doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["sources"] = json.loads(d.pop("sources_json")) if d.get("sources_json") else None
    d["key_figures"] = json.loads(d.pop("key_figures_json")) if d.get("key_figures_json") else None
    return d


def is_owner(user_id: str, report_id: str) -> bool:
    """True only if report_id exists AND belongs to user_id."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM reports WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        ).fetchone()
    return row is not None


def delete_report(report_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
