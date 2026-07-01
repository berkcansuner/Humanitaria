import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import chat, health, conversations, auth, admin, reports
from api.limiter import limiter
from api.observability import configure_logging, init_sentry
from config import get_settings, DEFAULT_SESSION_SECRET

logger = logging.getLogger(__name__)


def _docs_kwargs(settings) -> dict:
    """Hide the interactive API docs (/docs, /redoc, /openapi.json) in production so
    the internal admin/auth surface is not publicly discoverable."""
    if settings.is_production:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def _verify_production_config(settings) -> None:
    """Fail fast at startup if a production deployment runs with insecure defaults."""
    if settings.is_production and settings.AUTH_SESSION_SECRET == DEFAULT_SESSION_SECRET:
        raise RuntimeError(
            "AUTH_SESSION_SECRET is the insecure default in a production environment. "
            "Set a strong AUTH_SESSION_SECRET (see .env.example)."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up RAG components and start the ingestion scheduler at startup."""
    settings = get_settings()

    # Warm up RAG components so the first request is not slow.
    # Embedding warmup runs a dummy query to load the model into memory.
    try:
        from rag.retriever import _get_vectorstore
        from rag.chain import build_chain
        from rag.embeddings import get_embeddings
        _get_vectorstore()
        build_chain()
        logger.info("RAG vectorstore + chain warmed up")
        # Embed a short dummy text to load the model into GPU/CPU memory.
        embedder = get_embeddings()
        embedder.embed_query("warmup")
        logger.info("Embedding model warmed up")
    except Exception as exc:
        logger.warning("Startup warmup failed (non-fatal, will retry on first request): %s", exc)

    # Load the persisted reports cache so the admin list is served instantly after
    # a restart (the first-ever build is kicked off lazily by the documents route).
    try:
        from ingestion import analytics
        analytics.load_persisted()
    except Exception as exc:
        logger.warning("Failed to load reports cache (non-fatal): %s", exc)

    # Start background ingestion scheduler
    scheduler = None
    if settings.INGEST_SCHEDULE_HOURS > 0:
        try:
            from ingestion.scheduler import start_scheduler
            scheduler = start_scheduler()
        except Exception as exc:
            logger.warning("Ingestion scheduler failed to start (non-fatal): %s", exc)

    # Expose the scheduler to routes (the admin panel reads its next run time);
    # stays None when scheduling is disabled or startup failed.
    app.state.ingest_scheduler = scheduler

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped")


settings = get_settings()
# Configure logging first so subsequent startup logs use the app's level/format;
# then wire optional Sentry error tracking (no-op unless SENTRY_DSN is set).
configure_logging(settings.LOG_LEVEL)
init_sentry(settings.SENTRY_DSN, environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE)
_verify_production_config(settings)

app = FastAPI(title="ReliefWeb RAG API", lifespan=lifespan, **_docs_kwargs(settings))

# Rate limiting: register the shared limiter and the 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
# allow_credentials=True so the browser sends/stores the httpOnly session cookie
# on cross-origin dev calls (frontend :5173 → API :8000). Requires an explicit
# origin list (never "*" with credentials), which CORS_ORIGINS provides.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
# Signed cookie used by Authlib to hold the Google OAuth state/nonce mid-flow.
app.add_middleware(SessionMiddleware, secret_key=settings.AUTH_SESSION_SECRET)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, tags=["auth"])
app.include_router(chat.router, tags=["chat"])
app.include_router(conversations.router, tags=["conversations"])
app.include_router(admin.router, tags=["admin"])
app.include_router(reports.router, tags=["reports"])

frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    # Vite's hashed assets are served directly. Everything else falls back to
    # index.html so vue-router history-mode client routes (/pricing, /app) work
    # on refresh. This block is defined AFTER the API routers so it only catches
    # GET paths the API didn't claim.
    assets_dir = frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        candidate = frontend_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)        # favicon, robots.txt, etc.
        return FileResponse(frontend_dir / "index.html")  # client routes → SPA


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
