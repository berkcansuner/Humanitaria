"""Indexed reports list for the admin panel, the report-form country list and the
rolling-window retention — all plain SQL over the ``documents`` table, which the
ingest writes alongside each document's chunks (``ingestion/store.py``).

(It replaces a scan of the old Pinecone index that downloaded every vector: that
scan pushed the free-tier instance over its memory limit and spent the monthly
read quota.)
"""
import logging
from typing import List

from sqlalchemy import text

from config import get_settings
from rag.db import connect

logger = logging.getLogger(__name__)

# Reports list (admin panel): lean per-document row, sorted newest-first.
DOC_FIELDS = ("date", "title", "url", "source", "country", "doc_id", "doctype")
DEFAULT_PAGE = 50
MAX_PAGE = 200


def get_documents(q: str = "", offset: int = 0, limit: int = DEFAULT_PAGE) -> dict:
    """Case-insensitive substring search over title/source/country, newest first
    (missing dates last, then title), plus the total number of matches."""
    q = (q or "").strip().lower()
    offset = max(0, offset)
    limit = max(1, min(limit, MAX_PAGE))
    where, params = "", {}
    if q:
        where = "WHERE lower(title) LIKE :q OR lower(source) LIKE :q OR lower(country) LIKE :q"
        params["q"] = f"%{q}%"
    with connect() as conn:
        total = conn.execute(text(f"SELECT count(*) FROM documents {where}"), params).scalar_one()
        rows = conn.execute(text(
            f"SELECT {', '.join(DOC_FIELDS)} FROM documents {where} "
            "ORDER BY date DESC, lower(title) ASC LIMIT :limit OFFSET :offset"),
            {**params, "limit": limit, "offset": offset}).mappings().all()
    return {"total": total, "offset": offset, "limit": limit, "items": [dict(r) for r in rows]}


def distinct_countries() -> List[str]:
    """Sorted distinct non-empty country names of the indexed documents — the M&E
    report form offers only countries that actually have data."""
    with connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT country FROM documents WHERE country <> '' ORDER BY country")).all()
    return [r[0] for r in rows]


def apply_retention() -> List[str]:
    """Rolling-window trim after an ingest (RETENTION_DAYS / RETENTION_PER_COUNTRY_CAP;
    both 0 = off). Returns the deleted doc_ids."""
    from ingestion import retention
    from ingestion.store import get_store

    s = get_settings()
    if s.RETENTION_DAYS <= 0 and s.RETENTION_PER_COUNTRY_CAP <= 0:
        return []
    with connect() as conn:
        docs = [dict(r) for r in conn.execute(
            text("SELECT doc_id, date, country, doctype FROM documents")).mappings()]
    return retention.apply_retention(get_store(), docs, s.RETENTION_DAYS, s.RETENTION_PER_COUNTRY_CAP)
