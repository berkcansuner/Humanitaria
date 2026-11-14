import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from config import get_settings
# Re-exported: runner.py calls it as ``sched.run_pipeline`` (single delegation
# point the tests patch), so it must stay importable from this module.
from ingestion.pipeline import run_pipeline  # noqa: F401

logger = logging.getLogger(__name__)


_WATERMARK_KEY = "ingest_watermark"


def _load_watermark() -> Optional[str]:
    """Where the next incremental ingest starts (ReliefWeb date.created, a
    YYYY-MM-DD date or an ISO timestamp), or None for a full ingest. Stored in the
    app DB: Render's free-tier disk is wiped on every sleep/deploy."""
    from sqlalchemy import text

    from rag.db import connect
    try:
        with connect() as conn:
            row = conn.execute(text("SELECT value FROM ingest_state WHERE key = :k"),
                               {"k": _WATERMARK_KEY}).fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.warning("Failed to read ingest watermark: %s", e)
        return None


def _save_watermark(timestamp: str) -> None:
    from sqlalchemy import text

    from rag.db import connect
    try:
        with connect() as conn:
            conn.execute(text(
                "INSERT INTO ingest_state (key, value, updated_at) VALUES (:k, :v, :u) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at"),
                {"k": _WATERMARK_KEY, "v": timestamp, "u": datetime.now(timezone.utc).isoformat()})
    except Exception as e:
        logger.error("Failed to save ingest watermark: %s", e)


def _run_scheduled_ingest() -> None:
    """Scheduled ingest job: delegate to the shared runner so a scheduled run and a
    manually-triggered run can never overlap (both pass through the same lock)."""
    from ingestion.runner import run_ingest_once
    if not run_ingest_once("scheduled"):
        logger.info("Scheduled ingest skipped: a run is already in progress")


def start_scheduler() -> BackgroundScheduler:
    """Start the background ingestion scheduler and return it for lifecycle management."""
    settings = get_settings()
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run_scheduled_ingest,
        trigger="interval",
        hours=settings.INGEST_SCHEDULE_HOURS,
        id="ingest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Ingestion scheduler started (every %dh, next run in %dh)",
        settings.INGEST_SCHEDULE_HOURS,
        settings.INGEST_SCHEDULE_HOURS,
    )
    return scheduler
