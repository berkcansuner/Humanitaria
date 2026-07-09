import json
import logging
import os
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from config import get_settings
# Re-exported: runner.py calls it as ``sched.run_pipeline`` (single delegation
# point the tests patch), so it must stay importable from this module.
from ingestion.pipeline import run_pipeline  # noqa: F401

logger = logging.getLogger(__name__)


def _watermark_path() -> Path:
    """Return the path to the incremental ingest watermark file."""
    return Path(get_settings().INGEST_WATERMARK_PATH)


def _load_watermark() -> Optional[str]:
    """Return the ISO date string of the last successful ingest, or None."""
    path = _watermark_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("last_ingest")
        except Exception as e:
            logger.warning("Failed to read ingest watermark: %s", e)
    return None


def _save_watermark(timestamp: str) -> None:
    path = _watermark_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"last_ingest": timestamp}), encoding="utf-8")
        os.replace(tmp, path)   # atomic: a crash never leaves a half-written watermark
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
