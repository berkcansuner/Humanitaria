import pytest
from unittest.mock import patch, MagicMock
from rag.embeddings import OllamaLangChainEmbeddings


class TestOllamaLangChainEmbeddings:
    def test_embed_documents(self):
        with patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.1] * 4096, [0.2] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_documents(["a", "b"])
            assert len(result) == 2
            assert len(result[0]) == 4096

    def test_embed_query(self):
        with patch("rag.embeddings.ollama.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.embed.return_value = {"embeddings": [[0.3] * 4096]}
            MockClient.return_value = mock_client
            emb = OllamaLangChainEmbeddings()
            result = emb.embed_query("hello")
            assert len(result) == 4096
