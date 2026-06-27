"""Shared single-run ingest guard + in-memory run state.

Both the scheduled job (``ingestion/scheduler.py``) and the admin "run now"
trigger (``api/routes/admin.py``) go through ``run_ingest_once`` so a scheduled
run and a manual run can never overlap — the non-blocking ``threading.Lock`` is
the guarantee (the scheduled job runs on an APScheduler background thread, the
manual trigger on an ``anyio.to_thread`` worker thread; a thread lock is the one
primitive both can share). State is in-memory (lost on restart); the durable
watermark file still records the last successful ingest date.
"""
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from ingestion import scheduler as sched

logger = logging.getLogger(__name__)

_lock = threading.Lock()


@dataclass
class RunState:
    running: bool = False
    source: Optional[str] = None          # "scheduled" | "manual"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    last_error: Optional[str] = None
    last_stats: Optional[dict] = None


_state = RunState()


def is_running() -> bool:
    return _state.running


def get_state() -> dict:
    return asdict(_state)


def run_ingest_once(source: str) -> bool:
    """Run one incremental ingest. Returns False immediately if a run is already
    in progress (no overlap); True once this call has run (success or handled
    error). The watermark is advanced only on success, mirroring the previous
    scheduled-ingest behaviour.
    """
    if not _lock.acquire(blocking=False):
        return False
    try:
        _state.running = True
        _state.source = source
        _state.started_at = datetime.now(timezone.utc).isoformat()
        _state.finished_at = None
        _state.last_error = None
        run_start = datetime.now().strftime("%Y-%m-%d")
        date_from = sched._load_watermark()
        logger.info("Ingest starting (source=%s, date_from=%s)", source, date_from or "full")
        try:
            stats = sched.run_pipeline(date_from=date_from)
            sched._save_watermark(run_start)
            _state.last_stats = {
                ep: {"total": s.total, "succeeded": s.succeeded,
                     "failed": s.failed, "skipped": s.skipped}
                for ep, s in (stats or {}).items()
            }
            # New data landed — the cached breakdown is now stale (recompute on demand).
            try:
                from ingestion import analytics
                analytics.mark_stale()
            except Exception:
                pass
            logger.info("Ingest complete (source=%s), watermark=%s", source, run_start)
        except Exception as exc:
            _state.last_error = str(exc)
            logger.error("Ingest failed (source=%s, watermark NOT updated): %s", source, exc)
        return True
    finally:
        _state.running = False
        _state.finished_at = datetime.now(timezone.utc).isoformat()
        _lock.release()
