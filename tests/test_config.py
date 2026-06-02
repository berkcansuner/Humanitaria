import pytest
from unittest.mock import patch
from config import Settings, get_settings


class TestConfig:
    def test_settings_loads_env(self):
        with patch.dict("os.environ", {"CHUNK_SIZE": "500", "TOP_K_RETRIEVAL": "3"}, clear=False):
            s = Settings()
            assert s.CHUNK_SIZE == 500
            assert s.TOP_K_RETRIEVAL == 3

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


def test_recency_boost_defaults():
    from config import Settings
    s = Settings(_env_file=None)
    assert s.RECENCY_RERANK_POOL == 10
    assert s.RECENCY_BOOST_FACTOR == 0.6


def test_vector_store_and_embed_provider_defaults():
    from config import Settings
    s = Settings(_env_file=None)
    assert s.VECTOR_STORE_PROVIDER == "chroma"
    assert s.EMBED_DIM == 3072
    assert s.GEMINI_EMBED_MODEL == "gemini-embedding-001"
    assert s.PINECONE_INDEX == "reliefweb-docs"
    assert s.PINECONE_CLOUD == "aws"
    assert s.PINECONE_REGION == "us-east-1"
    assert s.PINECONE_NAMESPACE == ""
