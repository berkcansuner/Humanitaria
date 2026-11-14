"""Admin-only ingestion status & management endpoints.

Gated by ``get_admin_user`` (the ADMIN_EMAILS allowlist). Surfaces ingestion
health (last/next run, indexed chunk/document counts, scheduler state, last-run summary)
and a manual "run now" trigger that reuses the shared ingest runner.
"""
import asyncio
import logging
import secrets

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from api.routes.auth import get_admin_user, _is_admin
from config import get_settings
from ingestion import analytics
from ingestion import runner
from ingestion import scheduler as sched
from ingestion.store import get_store
from rag import users as users_store

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

    counts, vector_error = {}, None
    try:
        counts = await anyio.to_thread.run_sync(get_store().counts)
    except Exception as exc:  # never fail the whole status
        vector_error = str(exc)
        logger.warning("Failed to count indexed chunks: %s", exc)

    return {
        "last_ingest": sched._load_watermark(),
        "next_scheduled_run": next_run,
        "scheduler_active": scheduler_active,
        "chunk_count": counts.get("chunks"),
        "document_count": counts.get("documents"),
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
    logger.info("admin: ingest trigger by user=%s", admin.get("id"))
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
    """Paginated, optionally-filtered list of indexed reports, newest-first (admin-only)."""
    return await anyio.to_thread.run_sync(analytics.get_documents, q, offset, limit)


@router.get("/users")
async def list_users(
    admin: dict = Depends(get_admin_user),
    q: str = Query("", max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Paginated, searchable read-only user list (admin-only). is_admin is
    computed server-side (allowlist + Google link) for the badge."""
    rows, total = await anyio.to_thread.run_sync(users_store.list_users, q, offset, limit)
    out = []
    for r in rows:
        linked = bool(r.pop("google_linked", 0))
        out.append({**r, "is_admin": _is_admin({"email": r["email"], "google_sub": linked})})
    return {
        "users": out,
        "total": total,
    }


@router.post("/ingest/cron", status_code=202)
async def cron_ingest(x_cron_token: str = Header(default="", alias="X-Cron-Token")):
    """Token-gated automation trigger (called daily by the Cloudflare Worker cron).

    Responds 202 immediately and runs ONE ingest + rolling-retention pass in the
    background (same pattern as /ingest/trigger): Render's proxy times out long
    requests with a 502, so a synchronous response cannot survive the first run
    after a cold start. The job itself (~5-10 min) finishes well inside the
    free-tier 15-min idle window, and its outcome lands in the admin status panel.
    Gated by ``INGEST_TRIGGER_TOKEN`` (constant-time compare); 403 if the token is
    unset or mismatched. Not session-gated — automation has no cookie. The
    session-cookie UI trigger (/ingest/trigger) is unaffected."""
    token = get_settings().INGEST_TRIGGER_TOKEN
    if not token or not secrets.compare_digest(x_cron_token or "", token):
        raise HTTPException(status_code=403, detail="Invalid or missing cron token")
    if runner.is_running():
        return JSONResponse(
            status_code=409,
            content={"status": "already-running", "run": runner.get_state()},
        )
    task = asyncio.create_task(anyio.to_thread.run_sync(runner.run_ingest_once, "cron"))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return {"status": "started"}
