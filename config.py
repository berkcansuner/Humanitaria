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

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 5
    MMR_FETCH_K: int = 20          # candidate pool for MMR diversity
    MMR_LAMBDA: float = 0.5        # 0=max diversity, 1=max relevance
    INGEST_SCHEDULE_HOURS: int = 12
    RERANK_BY_DATE: bool = True
    DATE_DECAY_FACTOR: float = 0.3

    # CORS — comma-separated allowed origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    # API Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
