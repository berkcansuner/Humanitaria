"""Tests for the Gemini embedding client.

Regression guard for P11-01: the OpenAI-compatible client MUST carry an explicit
finite timeout, otherwise a slow Gemini embedding (this runs at the START of every
chat/report retrieval, before the LLM) hangs on the SDK's ~600s default and holds
the single worker.
"""
from unittest.mock import MagicMock, patch


def _fake_settings(timeout=20):
    s = MagicMock()
    s.GEMINI_API_KEY = "test-key"
    s.GEMINI_BASE_URL = "https://example.invalid/"
    s.GEMINI_EMBED_MODEL = "gemini-embedding-001"
    s.EMBED_BATCH_SIZE = 32
    s.EMBED_DIM = 3072
    s.EMBED_TIMEOUT = timeout
    return s


def test_embedding_client_constructed_with_explicit_timeout():
    with patch("rag.embeddings.OpenAI") as MockOpenAI, \
         patch("rag.embeddings.get_settings", return_value=_fake_settings(timeout=20)):
        from rag.embeddings import GeminiLangChainEmbeddings
        GeminiLangChainEmbeddings()
    assert MockOpenAI.call_count == 1
    _args, kwargs = MockOpenAI.call_args
    assert kwargs.get("timeout") == 20, "embedding OpenAI client must set an explicit timeout"
