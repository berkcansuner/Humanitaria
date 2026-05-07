import os
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
    EMBED_DIM: int = 4096

    # Chainlit
    CHAINLIT_AUTH_SECRET: str = "change_this_secret"
    CHAINLIT_USERS: str = "user1:pass1,user2:pass2"

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 5
    INGEST_SCHEDULE_HOURS: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
