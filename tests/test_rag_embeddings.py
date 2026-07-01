import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _clear_query_embed_cache():
    """The query-embedding cache is module-global; clear it around each test so
    cached vectors never leak between tests and skew call-count assertions."""
    from rag.embeddings import _query_embed_cache
    _query_embed_cache.clear()
    yield
    _query_embed_cache.clear()


def _mock_gemini_settings(embed_dim=3072, batch_size=32):
    s = MagicMock()
    s.GEMINI_API_KEY = "test-key"
    s.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    s.GEMINI_EMBED_MODEL = "gemini-embedding-001"
    s.EMBED_BATCH_SIZE = batch_size
    s.EMBED_DIM = embed_dim
    return s


def _gemini_response(n, dim=3072):
    resp = MagicMock()
    resp.data = [MagicMock(embedding=[0.1] * dim) for _ in range(n)]
    return resp


class TestGeminiLangChainEmbeddings:
    def test_embed_documents(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(2)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            result = emb.embed_documents(["a", "b"])
            assert len(result) == 2
            assert len(result[0]) == 3072

    def test_embed_query(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(1)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            result = emb.embed_query("hello")
            assert len(result) == 3072

    def test_embed_documents_batching(self):
        """Texts exceeding batch_size should trigger multiple embedding calls."""
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings(batch_size=2)), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(2)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            result = emb.embed_documents(["a", "b", "c", "d"])
            assert len(result) == 4
            assert client.embeddings.create.call_count == 2

    def test_dim_validation_raises_on_mismatch(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings(embed_dim=1536)), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(1, dim=3072)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            with pytest.raises(ValueError, match="Embedding dimension mismatch"):
                emb.embed_query("x")

    def test_retry_on_failure(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI") as MockOpenAI, \
             patch("rag.embeddings.time.sleep"):
            client = MagicMock()
            client.embeddings.create.side_effect = [
                RuntimeError("timeout"),
                _gemini_response(1),
            ]
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            result = emb.embed_query("retry")
            assert len(result) == 3072
            assert client.embeddings.create.call_count == 2


class TestQueryEmbeddingCache:
    def test_repeated_query_served_from_cache(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(1)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            v1 = emb.embed_query("same query")
            v2 = emb.embed_query("same query")
            assert v1 == v2
            assert client.embeddings.create.call_count == 1  # second call cached

    def test_distinct_queries_not_shared(self):
        from rag.embeddings import GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI") as MockOpenAI:
            client = MagicMock()
            client.embeddings.create.return_value = _gemini_response(1)
            MockOpenAI.return_value = client
            emb = GeminiLangChainEmbeddings()
            emb.embed_query("query a")
            emb.embed_query("query b")
            assert client.embeddings.create.call_count == 2


class TestGetEmbeddingsFactory:
    def test_factory_returns_gemini(self):
        from rag.embeddings import get_embeddings, GeminiLangChainEmbeddings
        with patch("rag.embeddings.get_settings", return_value=_mock_gemini_settings()), \
             patch("rag.embeddings.OpenAI"):
            assert isinstance(get_embeddings(), GeminiLangChainEmbeddings)
