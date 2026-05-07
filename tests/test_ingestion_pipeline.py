import pytest
from unittest.mock import patch, MagicMock
from ingestion.pipeline import run_pipeline


class TestPipeline:
    def test_run_pipeline_with_limit(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse_report") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
             patch("ingestion.pipeline.ChromaStore") as MockStore:
            mock_client = MagicMock()
            mock_client.fetch_reports.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": ""}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": ""}}]
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1] * 4096]
            MockEmbedder.return_value = mock_embedder
            mock_store = MagicMock()
            MockStore.return_value = mock_store
            run_pipeline(limit=1)
            mock_client.fetch_reports.assert_called_once_with(limit=1, offset=0)
            mock_store.upsert_chunks.assert_called_once()
            mock_store.clear_collection.assert_not_called()

    def test_run_pipeline_with_force(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse_report") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
             patch("ingestion.pipeline.ChromaStore") as MockStore:
            mock_client = MagicMock()
            mock_client.fetch_reports.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": ""}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": ""}}]
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1] * 4096]
            MockEmbedder.return_value = mock_embedder
            mock_store = MagicMock()
            MockStore.return_value = mock_store
            run_pipeline(limit=1, force=True)
            mock_store.clear_collection.assert_called_once()
