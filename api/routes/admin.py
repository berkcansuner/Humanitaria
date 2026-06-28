"""Admin-only ingestion status & management endpoints.

Gated by ``get_admin_user`` (the ADMIN_EMAILS allowlist). Surfaces ingestion
health (last/next run, Pinecone vector count, scheduler state, last-run summary)
and a manual "run now" trigger that reuses the shared ingest runner.
"""
import asyncio
import logging
import secrets

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from api.routes.auth import get_admin_user
from config import get_settings
from ingestion import analytics
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

    namespace, namespace_vectors, total_vectors, vector_error = None, None, None, None
    try:
        store = get_store()
        namespace = store.namespace or ""   # the namespace retrieval actually queries
        stats = await anyio.to_thread.run_sync(store.index.describe_index_stats)
        total_vectors = stats.get("total_vector_count")          # index-wide (all namespaces)
        ns_summary = (stats.get("namespaces") or {}).get(namespace)
        if ns_summary is not None:
            namespace_vectors = ns_summary.get("vector_count")   # what the app queries
    except Exception as exc:  # Pinecone network call — never fail the whole status
        vector_error = str(exc)
        logger.warning("Failed to read Pinecone index stats: %s", exc)

    return {
        "last_ingest": sched._load_watermark(),
        "next_scheduled_run": next_run,
        "scheduler_active": scheduler_active,
        "namespace": namespace,
        "namespace_vectors": namespace_vectors,
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


@router.get("/ingest/documents")
async def ingest_documents(
    admin: dict = Depends(get_admin_user),
    q: str = Query("", max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Paginated, optionally-filtered list of indexed reports for the active
    namespace, newest-first (admin-only). The list auto-builds: if nothing is
    cached yet (first visit / after an error) and no scan is running, a background
    rebuild is kicked off and ``computing`` returns True so the UI can poll until
    it lands. Afterwards each ingest refreshes the cache automatically."""
    if analytics._state.documents is None and not analytics.is_computing():
        task = asyncio.create_task(anyio.to_thread.run_sync(analytics.rebuild_documents))
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
        page = analytics.get_documents(q=q, offset=offset, limit=limit)
        page["computing"] = True   # the scan was just scheduled; tell the UI to poll
        return page
    return analytics.get_documents(q=q, offset=offset, limit=limit)


@router.post("/ingest/cron")
async def cron_ingest(x_cron_token: str = Header(default="", alias="X-Cron-Token")):
    """Token-gated automation trigger (called daily by the Cloudflare Worker cron).

    Runs ONE ingest + rolling-retention pass SYNCHRONOUSLY so the caller stays
    connected until it finishes — that keeps a sleeping free-tier instance awake for
    the whole (small) daily job. Gated by ``INGEST_TRIGGER_TOKEN`` (constant-time
    compare); 403 if the token is unset or mismatched. Not session-gated — automation
    has no cookie. The session-cookie UI trigger (/ingest/trigger) is unaffected."""
    token = get_settings().INGEST_TRIGGER_TOKEN
    if not token or not secrets.compare_digest(x_cron_token or "", token):
        raise HTTPException(status_code=403, detail="Invalid or missing cron token")
    if runner.is_running():
        return {"status": "already-running", "run": runner.get_state()}
    ran = await anyio.to_thread.run_sync(runner.run_ingest_once, "cron")
    return {"status": "ok" if ran else "skipped", "run": runner.get_state()}
