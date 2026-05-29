import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import chat, health
from config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up RAG components and start the ingestion scheduler at startup."""
    settings = get_settings()

    # Warm up RAG components so the first request is not slow.
    # Embedding warmup runs a dummy query to load the model into memory.
    try:
        from rag.retriever import _get_vectorstore
        from rag.chain import build_chain
        from rag.embeddings import OllamaLangChainEmbeddings
        _get_vectorstore()
        build_chain()
        logger.info("RAG vectorstore + chain warmed up")
        # Embed a short dummy text to load the model into GPU/CPU memory
        embedder = OllamaLangChainEmbeddings()
        embedder.embed_query("warmup")
        logger.info("Embedding model warmed up")
    except Exception as exc:
        logger.warning("Startup warmup failed (non-fatal, will retry on first request): %s", exc)

    # Start background ingestion scheduler
    scheduler = None
    if settings.INGEST_SCHEDULE_HOURS > 0:
        try:
            from ingestion.scheduler import start_scheduler
            scheduler = start_scheduler()
        except Exception as exc:
            logger.warning("Ingestion scheduler failed to start (non-fatal): %s", exc)

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped")


app = FastAPI(title="ReliefWeb RAG API", lifespan=lifespan)

settings = get_settings()
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, tags=["chat"])

frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
