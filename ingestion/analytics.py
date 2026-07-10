"""Indexed reports list for the admin panel.

Builds a newest-first list of the DISTINCT REPORTS in the active Pinecone
namespace. Pinecone serverless can't sort/aggregate server-side, so we scan the
namespace (``index.list`` ids → keep one ``_0`` chunk per doc → ``index.fetch``
metadata) and order in Python. Mirrors the in-repo scan in
``scripts/backfill_source_urls.py`` (list + fetch, batch 50 to stay under the
fetch-URI length limit / HTTP 414).

The scan is slow (~20-30s for ~30K vectors), so it runs in a background thread,
caches the result in memory AND on disk (``REPORTS_CACHE_PATH``) so a restart
serves the list instantly, and is rebuilt automatically after each ingest.
Concurrency is guarded by a non-blocking ``threading.Lock``, mirroring
``ingestion/runner.py``.
"""
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from config import get_settings
from ingestion.store import get_store

logger = logging.getLogger(__name__)

# Reports list (admin panel): lean per-document row, sorted newest-first.
DOC_FIELDS = ("date", "title", "url", "source", "country", "doc_id", "doctype")
DEFAULT_PAGE = 50
MAX_PAGE = 200
# fetch() puts ids in the request URI; ~1000 ids → HTTP 414 (backfill_source_urls.py:40).
_FETCH_BATCH = 50
# The scan is latency-bound (one fetch per 50 docs, hundreds of batches), so run the
# fetches on a thread pool — same approach as scripts/backfill_source_urls.py.
_FETCH_WORKERS = 32

_lock = threading.Lock()


# --- pure list builders (no Pinecone — fully unit-testable) ------------------

def build_documents(metadatas: Iterable[dict]) -> List[dict]:
    """One lean row per document for the admin Reports list, newest-first.

    Each input is ONE document's metadata (already deduped to its ``_0`` chunk).
    Rows carry only ``DOC_FIELDS`` (None → ""); sorted by ISO ``date`` descending
    (missing dates sort last) then title ascending (case-insensitive)."""
    rows = [{f: ((md or {}).get(f) or "") for f in DOC_FIELDS} for md in metadatas]
    rows.sort(key=lambda r: r["title"].lower())          # stable secondary key
    rows.sort(key=lambda r: r["date"], reverse=True)     # primary: newest first
    return rows


def slice_documents(docs: List[dict], q: str = "", offset: int = 0,
                    limit: int = DEFAULT_PAGE) -> dict:
    """Filter *docs* by case-insensitive substring *q* over title/source/country,
    then return the ``[offset, offset+limit)`` window plus the pre-window match
    total. ``offset`` clamps to ≥0 and ``limit`` to ``[1, MAX_PAGE]``."""
    q = (q or "").strip().lower()
    if q:
        docs = [d for d in docs
                if q in d["title"].lower() or q in d["source"].lower() or q in d["country"].lower()]
    total = len(docs)
    offset = max(0, offset)
    limit = max(1, min(limit, MAX_PAGE))
    return {"total": total, "offset": offset, "limit": limit, "items": docs[offset:offset + limit]}


# --- scan + cache + lock controller (mirrors ingestion/runner.py) ------------

@dataclass
class ReportsCache:
    computing: bool = False
    namespace: Optional[str] = None
    computed_at: Optional[str] = None   # ISO8601 UTC of the last SUCCESSFUL rebuild
    last_error: Optional[str] = None
    documents: Optional[list] = None    # newest-first per-doc rows; None until first success


_state = ReportsCache()


def is_computing() -> bool:
    return _state.computing


def get_documents(q: str = "", offset: int = 0, limit: int = DEFAULT_PAGE) -> dict:
    """Paginated, optionally-filtered slice of the cached document list. Never
    scans (``items`` is empty until the first rebuild populates the cache)."""
    page = slice_documents(_state.documents or [], q=q, offset=offset, limit=limit)
    page.update(computed_at=_state.computed_at, computing=_state.computing,
                namespace=_state.namespace, last_error=_state.last_error)
    return page


def distinct_countries() -> List[str]:
    """Sorted distinct non-empty country names from the cached reports list.

    Powers the M&E report form's country dropdown so it offers only countries that
    actually have indexed data. Empty until the first scan populates the cache."""
    seen = {(d.get("country") or "").strip() for d in (_state.documents or [])}
    return sorted(c for c in seen if c)


# --- disk persistence (mirrors the watermark helpers in scheduler.py) --------

def _cache_path() -> Path:
    return Path(get_settings().REPORTS_CACHE_PATH)


def _save_cache() -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({
            "computed_at": _state.computed_at,
            "namespace": _state.namespace,
            "documents": _state.documents or [],
        }), encoding="utf-8")
        os.replace(tmp, path)   # atomic write
    except Exception as exc:
        logger.error("Failed to save reports cache: %s", exc)


def load_persisted() -> None:
    """Load the on-disk reports cache into memory (called at startup) so the list
    is served instantly after a restart. Missing/corrupt file is a no-op."""
    path = _cache_path()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _state.documents = data.get("documents")
        _state.computed_at = data.get("computed_at")
        _state.namespace = data.get("namespace")
        logger.info("Loaded persisted reports cache: %d documents",
                    len(_state.documents or []))
    except Exception as exc:
        logger.warning("Failed to load reports cache: %s", exc)


def _collect_metadata(index, namespace) -> List[dict]:
    """One metadata dict per document in *namespace*: list every id, keep the ``_0``
    chunk of each doc, then fetch their metadata in parallel batches of 50 (the scan
    is latency-bound, so fetches run on a thread pool)."""
    zero_ids: List[str] = []
    for page in index.list(namespace=namespace):
        zero_ids.extend(i for i in page if i.rsplit("_", 1)[-1] == "0")
    batches = [zero_ids[i:i + _FETCH_BATCH] for i in range(0, len(zero_ids), _FETCH_BATCH)]

    def _fetch(batch):
        vectors = index.fetch(ids=batch, namespace=namespace).vectors
        return [(vec.metadata or {}) for vec in vectors.values()]

    metadatas: List[dict] = []
    with ThreadPoolExecutor(max_workers=_FETCH_WORKERS) as ex:
        for result in ex.map(_fetch, batches):
            metadatas.extend(result)
    return metadatas


def rebuild_documents(apply_retention: bool = False) -> bool:
    """Scan the active namespace, rebuild the cached reports list and persist it to
    disk. Returns False immediately if a scan is already running (no overlap); True
    once this call has run (success or handled error). On error the previously
    cached list is left intact.

    When *apply_retention* is True (set only by the ingest flow — never the admin
    lazy GET), the SAME scan also drives a rolling-window trim: documents older than
    RETENTION_DAYS and per-country-cap overflow are deleted, then excluded from the
    cached list. Both rules off (the default config) → no deletion."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        _state.computing = True
        _state.last_error = None
        store = get_store()
        namespace = store.namespace
        logger.info("Reports scan starting (namespace=%r, retention=%s)", namespace, apply_retention)
        documents = build_documents(_collect_metadata(store.index, namespace))
        if apply_retention:
            from ingestion import retention
            s = get_settings()
            deleted = set(retention.apply_retention(
                store, documents, s.RETENTION_DAYS, s.RETENTION_PER_COUNTRY_CAP))
            if deleted:
                documents = [d for d in documents if d["doc_id"] not in deleted]
        _state.documents = documents
        _state.namespace = namespace or ""
        _state.computed_at = datetime.now(timezone.utc).isoformat()
        _save_cache()
        logger.info("Reports scan complete: %d documents", len(documents))
        return True
    except Exception as exc:
        _state.last_error = str(exc)
        logger.error("Reports scan failed: %s", exc)
        return True
    finally:
        _state.computing = False
        _lock.release()
