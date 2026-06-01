from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama Cloud (LLM)
    OLLAMA_CLOUD_API_KEY: str
    OLLAMA_CLOUD_BASE_URL: str = "https://ollama.com/v1"
    OLLAMA_LLM_MODEL: str = "qwen3.5:397b-cloud"

    # Chat LLM provider: "ollama" veya "gemini" (chat yanıtı için)
    CHAT_LLM_PROVIDER: str = "gemini"

    # Query processor (filtre çıkarma) LLM provider: "gemini" veya "ollama".
    # "gemini" → yerel Ollama bağımlılığı yok, filtre doğruluğu daha yüksek.
    QUERY_LLM_PROVIDER: str = "gemini"

    # Google Gemini (chat üretim LLM'i — OpenAI uyumlu endpoint)
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_LLM_MODEL: str = "gemini-2.5-pro"   # Tier 1'de kullanılabilir; .env'den değiştirilebilir
    GEMINI_QUERY_MODEL: str = "gemini-2.5-flash"  # filtre çıkarma için hızlı/ucuz model

    # Ollama Local (Embedding)
    OLLAMA_LOCAL_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "qwen3-embedding:8b"

    # ReliefWeb
    RELIEFWEB_API_KEY: str = ""
    RELIEFWEB_APPNAME: str = ""
    RELIEFWEB_BASE_URL: str = "https://api.reliefweb.int/v2"

    # ChromaDB
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION: str = "reliefweb_docs"
    EMBED_DIM: int = 4096          # qwen3-embedding:8b — 4096 dim; 4b variant is 2560
    EMBED_BATCH_SIZE: int = 32     # max texts per Ollama embed call

    # Vector store provider: "chroma" veya "pinecone"
    VECTOR_STORE_PROVIDER: str = "chroma"
    # Embedding provider: "ollama" veya "gemini"
    EMBED_PROVIDER: str = "ollama"

    # Gemini embedding (OpenAI-uyumlu endpoint; GEMINI_API_KEY/GEMINI_BASE_URL yeniden kullanılır)
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"

    # Pinecone (serverless)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "reliefweb-docs"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_NAMESPACE: str = ""

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 5
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
    # Optional API key. Empty = open (local dev); non-empty requires the
    # X-API-Key header on the chat endpoints.
    API_KEY: str = ""

    # Session history
    HISTORY_WINDOW_K: int = 5         # number of exchanges (user+assistant pairs) to keep
    SESSION_MAX_MEMORY: int = 1000    # max in-memory sessions before LRU eviction
    REDIS_URL: str = ""               # e.g. redis://localhost:6379 — empty = in-memory
    SESSION_TTL_HOURS: int = 24       # Redis session TTL
    # Persistent conversation store (SQLite, file-based like CHROMA_DB_PATH).
    # Holds the named conversations + messages shown in the sidebar.
    CONVERSATION_DB_PATH: str = "./conversations.db"

    # Ingestion
    FETCH_PDF_CONTENT: bool = False   # download and index PDF attachments (slow, opt-in)


@lru_cache
def get_settings() -> Settings:
    return Settings()
