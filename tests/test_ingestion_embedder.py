import pytest
from unittest.mock import patch, MagicMock
from ingestion.embedder import OllamaEmbedder


class TestOllamaEmbedder:
    def test_embed_single_text(self):
        embedder = OllamaEmbedder()
        with patch("ingestion.embedder.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.1] * 4096]}
            MockClient.return_value = mock_client
            vec = embedder.embed("hello")
            assert len(vec) == 4096
            assert vec[0] == 0.1

    def test_embed_batch(self):
        embedder = OllamaEmbedder()
        with patch("ingestion.embedder.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.2] * 4096, [0.3] * 4096]}
            MockClient.return_value = mock_client
            vecs = embedder.embed_batch(["a", "b"])
            assert len(vecs) == 2
            assert len(vecs[0]) == 4096

    def test_embed_retries_on_failure(self):
        embedder = OllamaEmbedder()
        with patch("ingestion.embedder.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.side_effect = [Exception("timeout"), {"embeddings": [[0.1] * 4096]}]
            MockClient.return_value = mock_client
            with patch("time.sleep"):
                vec = embedder.embed("hello")
                assert len(vec) == 4096
                assert mock_client.embed.call_count == 2
