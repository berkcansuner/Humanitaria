import pytest
from unittest.mock import patch, MagicMock
from ingestion.pipeline import run_pipeline


class TestPipeline:
    def test_run_pipeline_with_limit(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
             patch("ingestion.pipeline.ChromaStore") as MockStore:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1] * 2560]
            MockEmbedder.return_value = mock_embedder
            mock_store = MagicMock()
            MockStore.return_value = mock_store
            run_pipeline(limit=1)
            mock_client.fetch.assert_called_once_with("reports", limit=1, offset=0)
            mock_store.upsert_chunks.assert_called_once()
            mock_store.clear_collection.assert_not_called()

    def test_run_pipeline_with_force(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
             patch("ingestion.pipeline.ChromaStore") as MockStore:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1] * 2560]
            MockEmbedder.return_value = mock_embedder
            mock_store = MagicMock()
            MockStore.return_value = mock_store
            run_pipeline(limit=1, force=True)
            mock_store.clear_collection.assert_called_once()

    def test_run_pipeline_multiple_endpoints(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
             patch("ingestion.pipeline.ChromaStore") as MockStore:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1] * 2560]
            MockEmbedder.return_value = mock_embedder
            mock_store = MagicMock()
            MockStore.return_value = mock_store
            run_pipeline(limit=1, endpoints=["reports", "disasters"])
            assert mock_client.fetch.call_count == 2
            calls = mock_client.fetch.call_args_list
            endpoint_names = [c[0][0] for c in calls]
            assert "reports" in endpoint_names
            assert "disasters" in endpoint_names