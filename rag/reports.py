"""Persistent M&E report store.

Holds the generated situation reports shown on the Reports page. Same database
as the conversation store (shared engine in ``rag/db.py``); a separate table
keeps the concern isolated. Mirrors ``rag/conversations.py``: synchronous,
FastAPI offloads with ``anyio.to_thread.run_sync``.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from rag.db import connect as _connect

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_report(report_id: str, user_id: str, *, country: str, theme: str | None,
                  date_from: str | None, date_to: str | None, language: str,
                  title: str, content: str, sources: list | None, doc_count: int) -> None:
    """Insert a generated report owned by user_id."""
    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
    with _connect() as conn:
        conn.execute(
            text(
                "INSERT INTO reports(id, user_id, country, theme, date_from, date_to, language, "
                "title, content, sources_json, doc_count, created_at) "
                "VALUES (:id, :uid, :country, :theme, :date_from, :date_to, :language, "
                ":title, :content, :sources, :doc_count, :now)"
            ),
            {"id": report_id, "uid": user_id, "country": country, "theme": theme,
             "date_from": date_from, "date_to": date_to, "language": language,
             "title": title, "content": content, "sources": sources_json,
             "doc_count": doc_count, "now": _now()},
        )


def list_reports(user_id: str) -> list[dict]:
    """Lean rows for the saved-reports list (no body), newest first."""
    with _connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, country, theme, date_from, date_to, language, title, doc_count, created_at "
                "FROM reports WHERE user_id = :uid ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: str) -> dict | None:
    """Full report incl. body + parsed sources, or None if it doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            text("SELECT * FROM reports WHERE id = :id"), {"id": report_id}
        ).mappings().fetchone()
    if row is None:
        return None
    d = dict(row)
    d["sources"] = json.loads(d.pop("sources_json")) if d.get("sources_json") else None
    return d


def is_owner(user_id: str, report_id: str) -> bool:
    """True only if report_id exists AND belongs to user_id."""
    with _connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM reports WHERE id = :id AND user_id = :uid"),
            {"id": report_id, "uid": user_id},
        ).fetchone()
    return row is not None


def delete_report(report_id: str) -> None:
    with _connect() as conn:
        conn.execute(text("DELETE FROM reports WHERE id = :id"), {"id": report_id})
