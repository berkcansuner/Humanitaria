import pytest
from unittest.mock import patch, MagicMock
from rag.embeddings import OllamaLangChainEmbeddings


def _mock_settings(embed_dim=4096, batch_size=32):
    """Return a mock settings object for embeddings tests."""
    s = MagicMock()
    s.OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
    s.OLLAMA_EMBED_MODEL = "qwen3-embedding:8b"
    s.EMBED_BATCH_SIZE = batch_size
    s.EMBED_DIM = embed_dim
    return s


class TestOllamaLangChainEmbeddings:
    def test_embed_documents(self):
        with patch("rag.embeddings.get_settings", return_value=_mock_settings()), \
             patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.1] * 4096, [0.2] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_documents(["a", "b"])
            assert len(result) == 2
            assert len(result[0]) == 4096

    def test_embed_query(self):
        with patch("rag.embeddings.get_settings", return_value=_mock_settings()), \
             patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.3] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_query("hello")
            assert len(result) == 4096

    def test_embed_documents_batching(self):
        """Texts exceeding batch_size should trigger multiple Ollama calls."""
        with patch("rag.embeddings.get_settings", return_value=_mock_settings(batch_size=2)), \
             patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            # Each batch call returns 2 embeddings
            mock_client.embed.return_value = {"embeddings": [[0.1] * 4096, [0.2] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_documents(["a", "b", "c", "d"])
            assert len(result) == 4
            # 4 texts with batch_size=2 → 2 Ollama calls
            assert mock_client.embed.call_count == 2

    def test_dim_validation_raises_on_mismatch(self):
        """Embedding dimension not matching EMBED_DIM should raise ValueError."""
        with patch("rag.embeddings.get_settings", return_value=_mock_settings(embed_dim=2560)), \
             patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            # Model returns 4096-dim but config says 2560
            mock_client.embed.return_value = {"embeddings": [[0.1] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            with pytest.raises(ValueError, match="Embedding dimension mismatch"):
                emb.embed_query("test")

    def test_retry_on_failure(self):
        """A transient embedding failure should be retried."""
        with patch("rag.embeddings.get_settings", return_value=_mock_settings()), \
             patch("rag.embeddings.ollama.Client") as MockClient, \
             patch("rag.embeddings.time.sleep"):
            mock_client = MagicMock()
            # Fail twice, succeed on third attempt
            mock_client.embed.side_effect = [
                RuntimeError("timeout"),
                RuntimeError("timeout"),
                {"embeddings": [[0.5] * 4096]},
            ]
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_query("retry test")
            assert len(result) == 4096
            assert mock_client.embed.call_count == 3
