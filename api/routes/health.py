import logging
from typing import Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from api.routes.auth import _is_admin, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_database() -> bool:
    """Probe the database — app tables and, on Postgres, the vector index (raises
    if it cannot be reached)."""
    from rag.db import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT 1 FROM chunks LIMIT 1"))
    return True


def _check_gemini() -> bool:
    """Probe the Gemini API with a minimal embedding call (raises on auth/quota
    errors, e.g. 402 'prepayment credits are depleted')."""
    from rag.embeddings import GeminiLangChainEmbeddings
    emb = GeminiLangChainEmbeddings()
    emb.client.embeddings.create(model=emb.model, input=["ping"])
    return True


@router.get("/health")
async def health(deep: bool = False, user: Optional[dict] = Depends(get_optional_user)):
    """Liveness by default (cheap, always 200 — used by the platform health check).

    With ``?deep=true`` it also probes the external dependencies (the DB with its
    vector index, and Gemini) and returns 503 if any is unavailable, for
    readiness/diagnostics.
    """
    if not deep:
        return {"status": "ok"}
    # The deep probe makes a billed Gemini call: admins only.
    if not (user and _is_admin(user)):
        raise HTTPException(status_code=403, detail="Admin access required")

    checks: dict[str, str] = {}
    probes = (("database", _check_database), ("gemini", _check_gemini))
    for name, probe in probes:
        try:
            await anyio.to_thread.run_sync(probe)
            checks[name] = "ok"
        except Exception as exc:
            logger.warning("Health check '%s' failed: %r", name, exc)
            checks[name] = "error"

    if any(status != "ok" for status in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "unavailable", "checks": checks})
    return {"status": "ok", "checks": checks}
