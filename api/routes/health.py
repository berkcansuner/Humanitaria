import logging

import anyio
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_pinecone() -> bool:
    """Probe the Pinecone index (raises if unreachable/misconfigured)."""
    from ingestion.store import get_store
    get_store().index.describe_index_stats()
    return True


def _check_database() -> bool:
    """Probe the users/conversations DB (raises if it cannot be reached)."""
    from rag.db import get_engine
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


@router.get("/health")
async def health(deep: bool = False):
    """Liveness by default (cheap, always 200 — used by the platform health check).

    With ``?deep=true`` it also probes the external dependencies (Pinecone + the
    DB) and returns 503 if any is unavailable, for readiness/diagnostics.
    """
    if not deep:
        return {"status": "ok"}

    checks: dict[str, str] = {}
    for name, probe in (("pinecone", _check_pinecone), ("database", _check_database)):
        try:
            await anyio.to_thread.run_sync(probe)
            checks[name] = "ok"
        except Exception as exc:
            logger.warning("Health check '%s' failed: %r", name, exc)
            checks[name] = "error"

    if any(status != "ok" for status in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "unavailable", "checks": checks})
    return {"status": "ok", "checks": checks}
