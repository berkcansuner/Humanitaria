"""Rolling-window retention for the active Pinecone namespace.

Keeps the indexed dataset current and quota-friendly. After each ingest we drop:
  - documents older than RETENTION_DAYS (rolling date window), and
  - per country, everything beyond the newest RETENTION_PER_COUNTRY_CAP documents.

``select_expired`` is a PURE function over the metadata the admin reports scan already
collected (one namespace scan feeds both the reports list and this trim — no extra
scan). Deletion reuses ``store.delete_document_chunks`` (chunk-id prefix list+delete).
Both rules are OFF by default (0) so retention is inert until explicitly enabled.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Set

logger = logging.getLogger(__name__)

UNKNOWN_COUNTRY = "(unknown)"


def _date_ts(doc: dict) -> int:
    """YYYYMMDD int from a doc's ISO ``date``; 0 if missing/unparseable."""
    raw = (doc.get("date") or "")[:10]
    try:
        return int(raw.replace("-", "")) if raw.count("-") == 2 else 0
    except ValueError:
        return 0


def cutoff_ts_for(retention_days: int, now=None) -> int:
    """YYYYMMDD int for (today − retention_days); 0 when retention_days<=0 (date rule off)."""
    if not retention_days or retention_days <= 0:
        return 0
    now = now or datetime.now(timezone.utc)
    return int((now - timedelta(days=retention_days)).strftime("%Y%m%d"))


def select_expired(docs: Iterable[dict], cutoff_ts: int = 0, per_country_cap: int = 0) -> Set[str]:
    """Return the set of ``doc_id``s to delete under the rolling-window policy. PURE.

    Each input is one document's metadata (``doc_id``, ``date``, ``country``, ``doctype``).
    A doc is expired if EITHER:
      - date rule: ``0 < date_ts < cutoff_ts`` (older than the window; a missing/0 date
        is never expired by this rule), OR
      - cap rule: within its (``country``, ``doctype``) group it is not among the newest
        ``per_country_cap`` non-date-expired docs (sorted date desc, doc_id asc for ties;
        a missing date sorts oldest, so it is dropped first when the group is over the
        cap). Grouping by doctype too keeps a country's reports and its disasters on
        separate counters, so ingesting one doctype can never silently evict the other
        out of a shared cap.

    ``cutoff_ts<=0`` disables the date rule; ``per_country_cap<=0`` disables the cap rule.
    """
    expired: Set[str] = set()
    survivors = []
    for d in docs:
        if not d:
            continue
        ts = _date_ts(d)
        if cutoff_ts > 0 and 0 < ts < cutoff_ts:
            expired.add(d.get("doc_id"))
        else:
            survivors.append((d, ts))

    if per_country_cap and per_country_cap > 0:
        by_group = defaultdict(list)
        for d, ts in survivors:
            group_key = (d.get("country") or UNKNOWN_COUNTRY, d.get("doctype") or "")
            by_group[group_key].append((d, ts))
        for rows in by_group.values():
            rows.sort(key=lambda dt: (-dt[1], dt[0].get("doc_id") or ""))  # newest first
            for d, _ in rows[per_country_cap:]:
                expired.add(d.get("doc_id"))

    expired.discard(None)
    expired.discard("")
    return expired


def apply_retention(store, docs, retention_days: int, per_country_cap: int) -> List[str]:
    """Delete expired documents' chunks from *store*'s namespace; return deleted doc_ids
    (sorted). No-op when both rules are off. Reuses ``store.delete_document_chunks``."""
    cutoff = cutoff_ts_for(retention_days)
    expired = select_expired(docs, cutoff_ts=cutoff, per_country_cap=per_country_cap)
    if not expired:
        return []
    logger.info("Retention: deleting %d documents (cutoff_ts=%s, per_country_cap=%s)",
                len(expired), cutoff or "off", per_country_cap or "off")
    for doc_id in expired:
        store.delete_document_chunks(doc_id)
    return sorted(expired)
