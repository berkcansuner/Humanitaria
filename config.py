from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini (chat üretim LLM'i — OpenAI uyumlu endpoint)
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_LLM_MODEL: str = "gemini-2.5-flash"   # chat yanıtı (GA; multilingual/RAG). gemini-3.5-flash kronik 503 ("high demand") verdiği için geçildi.
    # Thinking-budget for the chat model: "low" cuts time-to-first-token on the
    # gemini-2.5-flash thinking model. none/low/medium/high; "" = don't send (model default).
    GEMINI_REASONING_EFFORT: str = "low"
    # Chat LLM resilience: bounded retry (in the chat route) on transient upstream
    # 503 'high demand' BEFORE the first token. The OpenAI client's own retries are
    # disabled (max_retries=0 in chain.py) so a 503 fails fast instead of hanging
    # ~60s on its internal backoff; CHAT_LLM_TIMEOUT caps a stuck request.
    CHAT_LLM_TIMEOUT: int = 45
    CHAT_LLM_MAX_RETRIES: int = 2
    GEMINI_QUERY_MODEL: str = "gemini-2.5-flash"  # filtre çıkarma için hızlı/ucuz model

    # ReliefWeb
    RELIEFWEB_API_KEY: str = ""
    RELIEFWEB_APPNAME: str = ""
    RELIEFWEB_BASE_URL: str = "https://api.reliefweb.int/v2"

    EMBED_DIM: int = 3072          # Gemini gemini-embedding-001 → 3072
    EMBED_BATCH_SIZE: int = 32

    # Gemini embedding (OpenAI-uyumlu endpoint; GEMINI_API_KEY/GEMINI_BASE_URL yeniden kullanılır)
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"

    # Pinecone (serverless)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "reliefweb-docs"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_NAMESPACE: str = ""

    # RAG
    CHUNK_SIZE: int = 1500        # characters per chunk (recursive splitter)
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    # Rewrite a follow-up message into a standalone retrieval query using chat
    # history (resolves anaphora like "what about the north?"). Kill-switch.
    QUERY_REWRITE_ENABLED: bool = True
    MMR_FETCH_K: int = 20          # candidate pool for MMR diversity
    MMR_LAMBDA: float = 0.5        # 0=max diversity, 1=max relevance
    # Two-stage retrieval: Pinecone hosted reranker over a larger candidate pool.
    RERANK_ENABLED: bool = True
    RERANK_MODEL: str = "bge-reranker-v2-m3"
    RERANK_CANDIDATE_MULTIPLIER: int = 4   # candidate pool = TOP_K_RETRIEVAL * this
    INGEST_SCHEDULE_HOURS: int = 12
    RERANK_BY_DATE: bool = True
    DATE_DECAY_FACTOR: float = 0.3
    # Recency boost — "current situation" sorgularında (tarih filtresi yok, geçmiş niyeti yok)
    # daha geniş bir alaka havuzunu recency ile yeniden sıralayıp en yeni raporları top-k'ya taşır.
    RECENCY_RERANK_POOL: int = 10      # boost'ta ara alaka havuzu (sonra recency ile top-k'ya inilir)
    RECENCY_BOOST_FACTOR: float = 0.6  # boost'ta recency ağırlığı (varsayılan DATE_DECAY_FACTOR 0.3'e karşı)

    # CORS — comma-separated allowed origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    # API Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    # Rate limiting (slowapi) — applied per client IP to the chat endpoints.
    RATE_LIMIT: str = "20/minute"
    # Per-IP limits on the auth endpoints (brute-force / signup-spam guard).
    AUTH_LOGIN_RATE_LIMIT: str = "5/minute"
    AUTH_SIGNUP_RATE_LIMIT: str = "3/minute"

    # Auth (login/signup — httpOnly cookie session + Google OAuth)
    AUTH_SESSION_SECRET: str = "dev-insecure-change-me"   # signs OAuth state (Starlette SessionMiddleware)
    SESSION_COOKIE_NAME: str = "rw_session"               # httpOnly session cookie name
    SESSION_COOKIE_SECURE: bool = False                   # True in production (HTTPS only)
    FRONTEND_URL: str = "http://localhost:5173"           # post-OAuth redirect target
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    # Comma-separated emails granted the admin ingestion panel (empty = no admins).
    ADMIN_EMAILS: str = ""

    # Session history
    HISTORY_WINDOW_K: int = 5         # number of exchanges (user+assistant pairs) to keep
    SESSION_MAX_MEMORY: int = 1000    # max in-memory sessions before LRU eviction
    REDIS_URL: str = ""               # e.g. redis://localhost:6379 — empty = in-memory
    SESSION_TTL_HOURS: int = 24       # Redis session TTL
    # Persistent conversation store (SQLite, file-based).
    # Holds the named conversations + messages shown in the sidebar.
    CONVERSATION_DB_PATH: str = "./conversations.db"

    # Ingestion
    FETCH_PDF_CONTENT: bool = False   # download and index PDF attachments (slow, opt-in)
    INGEST_WATERMARK_PATH: str = "./.last_ingest.json"   # incremental ingest watermark
    # Default freshness floor for manual ingest: when --date-from is not given,
    # ingest.py only pulls documents from the last N years (0 = no floor / full history).
    # Prevents re-pulling ancient ReliefWeb history (e.g. a country's reports back to the 1990s).
    INGEST_LOOKBACK_YEARS: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
