"""Admin-only ingestion status & management endpoints.

Gated by ``get_admin_user`` (the ADMIN_EMAILS allowlist). Surfaces ingestion
health (last/next run, Pinecone vector count, scheduler state, last-run summary)
and a manual "run now" trigger that reuses the shared ingest runner.
"""
import asyncio
import logging

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request

from api.routes.auth import get_admin_user
from ingestion import runner
from ingestion import scheduler as sched
from ingestion.store import get_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

# Hold references to in-flight trigger tasks so the event loop does not GC them
# mid-run (asyncio only keeps a weak reference to a bare create_task result).
_bg_tasks: set = set()


@router.get("/ingest/status")
async def ingest_status(request: Request, admin: dict = Depends(get_admin_user)):
    """Ingestion health snapshot (admin-only)."""
    scheduler = getattr(request.app.state, "ingest_scheduler", None)
    next_run, scheduler_active = None, False
    if scheduler is not None:
        job = scheduler.get_job("ingest")
        if job is not None and job.next_run_time is not None:
            scheduler_active = True
            next_run = job.next_run_time.isoformat()

    total_vectors, vector_error = None, None
    try:
        store = get_store()
        stats = await anyio.to_thread.run_sync(store.index.describe_index_stats)
        # Index-wide count. Correct for the default (empty) PINECONE_NAMESPACE the
        # app uses; a non-default namespace would make this an over-count.
        total_vectors = stats.get("total_vector_count")
    except Exception as exc:  # Pinecone network call — never fail the whole status
        vector_error = str(exc)
        logger.warning("Failed to read Pinecone index stats: %s", exc)

    return {
        "last_ingest": sched._load_watermark(),
        "next_scheduled_run": next_run,
        "scheduler_active": scheduler_active,
        "total_vectors": total_vectors,
        "vector_count_error": vector_error,
        "run": runner.get_state(),
    }


@router.post("/ingest/trigger", status_code=202)
async def trigger_ingest(admin: dict = Depends(get_admin_user)):
    """Kick off an incremental ingest in the background (admin-only).

    Returns 202 immediately; 409 if a run (scheduled or manual) is already going.
    The runner's lock is the real overlap guard — this pre-check is just for fast
    UI feedback.
    """
    if runner.is_running():
        raise HTTPException(status_code=409, detail="An ingest is already running")
    task = asyncio.create_task(anyio.to_thread.run_sync(runner.run_ingest_once, "manual"))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return {"status": "started"}
