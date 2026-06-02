import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from config import get_settings
from ingestion.pipeline import run_pipeline

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
        path.write_text(json.dumps({"last_ingest": timestamp}), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to save ingest watermark: %s", e)


def _run_scheduled_ingest() -> None:
    """Scheduled ingest job: fetch only documents newer than the last run."""
    run_start = datetime.now().strftime("%Y-%m-%d")
    date_from = _load_watermark()
    logger.info("Scheduled ingest starting (date_from=%s)", date_from or "full")
    try:
        run_pipeline(date_from=date_from)
        _save_watermark(run_start)
        logger.info("Scheduled ingest complete, watermark updated to %s", run_start)
    except Exception as e:
        logger.error("Scheduled ingest failed (watermark NOT updated): %s", e)


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
