"""Indexed-data breakdowns for the admin panel.

Counts DISTINCT REPORTS in the active Pinecone namespace, grouped by source,
date (month + year), country, theme and format. Pinecone serverless can't
aggregate server-side, so we scan the namespace (``index.list`` ids → keep one
``_0`` chunk per doc → ``index.fetch`` metadata) and tally in Python. Mirrors the
in-repo scan in ``scripts/backfill_source_urls.py`` (list + fetch, batch 50 to
stay under the fetch-URI length limit / HTTP 414).

The scan is slow (~20-30s for ~30K vectors), so it runs in a background thread,
caches the result in memory (lost on restart), and is exposed via a manual
refresh. Concurrency is guarded by a non-blocking ``threading.Lock``, mirroring
``ingestion/runner.py``.
"""
import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from ingestion.store import get_store

logger = logging.getLogger(__name__)

TOP_N = 15
UNKNOWN = "(unknown)"
# fetch() puts ids in the request URI; ~1000 ids → HTTP 414 (backfill_source_urls.py:40).
_FETCH_BATCH = 50
# The scan is latency-bound (one fetch per 50 docs, hundreds of batches), so run the
# fetches on a thread pool — same approach as scripts/backfill_source_urls.py.
_FETCH_WORKERS = 32

_lock = threading.Lock()


# --- pure aggregation (no Pinecone — fully unit-testable) --------------------

def _rank(counter: Counter) -> dict:
    """Top-N entries by count desc then key asc, plus a long-tail summary. No
    catch-all ``(other)`` bar — the caller shows a 'top N of M' caption instead."""
    ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "items": [{"key": k, "count": c} for k, c in ordered[:TOP_N]],
        "distinct": len(ordered),
        "tail_count": sum(c for _, c in ordered[TOP_N:]),
    }


def _year_of(date: str) -> str:
    return date[:4] if (len(date) >= 4 and date[:4].isdigit()) else UNKNOWN


def _years(counter: Counter, min_year: Optional[int]) -> List[dict]:
    """Year rows newest-first. Years before *min_year* fold into one
    'before {min_year}' row; ``(unknown)`` trails. min_year=None shows every year."""
    recent, earlier, unknown = {}, 0, 0
    for year, count in counter.items():
        if year == UNKNOWN:
            unknown += count
        elif min_year is not None and int(year) < min_year:
            earlier += count
        else:
            recent[year] = count
    rows = [{"year": y, "count": recent[y]} for y in sorted(recent, reverse=True)]
    if earlier:
        rows.append({"year": f"before {min_year}", "count": earlier})
    if unknown:
        rows.append({"year": UNKNOWN, "count": unknown})
    return rows


def aggregate_breakdown(metadatas: Iterable[dict], min_year: Optional[int] = None) -> dict:
    """Tally distinct-report breakdowns. Each input is ONE document's metadata
    (already deduped to its ``_0`` chunk). Years before *min_year* are grouped."""
    by_source, by_country, by_theme, by_format = Counter(), Counter(), Counter(), Counter()
    by_year: Counter = Counter()
    total = 0
    for md in metadatas:
        md = md or {}
        total += 1
        by_source[md.get("source") or UNKNOWN] += 1
        by_country[md.get("country") or UNKNOWN] += 1
        by_theme[md.get("theme") or UNKNOWN] += 1
        by_format[md.get("format") or UNKNOWN] += 1
        by_year[_year_of(md.get("date") or "")] += 1
    return {
        "total_documents": total,
        "by_source": _rank(by_source),
        "by_country": _rank(by_country),
        "by_theme": _rank(by_theme),
        "by_format": _rank(by_format),
        "by_year": _years(by_year, min_year),
    }


# --- scan + cache + lock controller (mirrors ingestion/runner.py) ------------

@dataclass
class BreakdownState:
    computing: bool = False
    stale: bool = False
    namespace: Optional[str] = None
    computed_at: Optional[str] = None   # ISO8601 UTC of the last SUCCESSFUL compute
    last_error: Optional[str] = None
    data: Optional[dict] = None         # aggregate payload; None until first success


_state = BreakdownState()


def is_computing() -> bool:
    return _state.computing


def get_breakdown() -> dict:
    return asdict(_state)


def mark_stale() -> None:
    """Flag the cached breakdown as out-of-date (e.g. after an ingest). The
    last-known data is kept so the UI can still show it; a refresh recomputes."""
    _state.stale = True


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


def compute_breakdown() -> bool:
    """Scan the active namespace and cache the breakdown. Returns False immediately
    if a scan is already running (no overlap); True once this call has run (success
    or handled error). On error the previously cached data is left intact."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        _state.computing = True
        _state.last_error = None
        store = get_store()
        namespace = store.namespace
        logger.info("Breakdown scan starting (namespace=%r)", namespace)
        data = aggregate_breakdown(_collect_metadata(store.index, namespace),
                                   min_year=datetime.now(timezone.utc).year - 5)
        data["namespace"] = namespace or ""
        data["computed_at"] = datetime.now(timezone.utc).isoformat()
        _state.data = data
        _state.namespace = data["namespace"]
        _state.computed_at = data["computed_at"]
        _state.stale = False
        logger.info("Breakdown scan complete: %d documents", data["total_documents"])
        return True
    except Exception as exc:
        _state.last_error = str(exc)
        logger.error("Breakdown scan failed: %s", exc)
        return True
    finally:
        _state.computing = False
        _lock.release()
