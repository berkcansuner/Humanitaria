"""Shared single-run ingest guard + in-memory run state.

Both the scheduled job (``ingestion/scheduler.py``) and the admin "run now"
trigger (``api/routes/admin.py``) go through ``run_ingest_once`` so a scheduled
run and a manual run can never overlap — the non-blocking ``threading.Lock`` is
the guarantee (the scheduled job runs on an APScheduler background thread, the
manual trigger on an ``anyio.to_thread`` worker thread; a thread lock is the one
primitive both can share). State is in-memory (lost on restart); the durable
watermark (app DB, ``ingest_state``) records where the next run starts.
"""
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from config import get_settings
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
    error). The watermark is not advanced when the run raises, and never past a
    document that failed or was left beyond the run's limit.
    """
    if not _lock.acquire(blocking=False):
        return False
    try:
        _state.running = True
        _state.source = source
        _state.started_at = datetime.now(timezone.utc).isoformat()
        _state.finished_at = None
        _state.last_error = None
        run_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Reading (and later saving) the DB-stored watermark is also the daily DB
        # activity that keeps a free-tier Supabase project from pausing.
        date_from = sched._load_watermark()
        # Endpoints ingested by every automatic/admin-triggered run (scheduled job,
        # admin "run now", daily cron) — configurable via INGEST_ENDPOINTS so
        # disasters (or a future endpoint) can be added/removed without a code
        # change. This is the ONE place all three trigger paths converge.
        endpoints = [e.strip() for e in get_settings().INGEST_ENDPOINTS.split(",") if e.strip()]
        logger.info("Ingest starting (source=%s, date_from=%s, endpoints=%s)",
                    source, date_from or "full", endpoints)
        try:
            stats = sched.run_pipeline(date_from=date_from, endpoints=endpoints)
            # Advance only past what actually landed: a failed batch or a run cut
            # off at its limit holds the watermark at the earliest such item, so
            # the next run picks it up again (re-ingest is idempotent).
            held = [s.resume_from for s in (stats or {}).values() if s.resume_from]
            watermark = min([run_start, *held])
            sched._save_watermark(watermark)
            if held:
                _state.last_error = f"Not every document was ingested; next run resumes from {watermark}"
                logger.warning("Ingest incomplete (source=%s), watermark held at %s", source, watermark)
            _state.last_stats = {
                ep: {"total": s.total, "succeeded": s.succeeded,
                     "failed": s.failed, "skipped": s.skipped}
                for ep, s in (stats or {}).items()
            }
            # Rolling-window retention (drop >RETENTION_DAYS old and per-country-cap
            # overflow). Both off by default → inert. Never fails the ingest.
            try:
                from ingestion import analytics
                analytics.apply_retention()
            except Exception as exc:
                logger.warning("Retention failed: %s", exc)
            logger.info("Ingest complete (source=%s), watermark=%s", source, watermark)
        except Exception as exc:
            _state.last_error = str(exc)
            logger.error("Ingest failed (source=%s, watermark NOT updated): %s", source, exc)
        return True
    finally:
        _state.running = False
        _state.finished_at = datetime.now(timezone.utc).isoformat()
        _lock.release()
