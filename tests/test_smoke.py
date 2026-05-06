import pytest
from unittest.mock import patch, MagicMock


def test_all_imports():
    from ingestion.client import ReliefWebClient
    from ingestion.parser import parse_report
    from ingestion.chunker import chunk_document
    from ingestion.embedder import OllamaEmbedder
    from ingestion.store import ChromaStore
    from ingestion.pipeline import run_pipeline
    from rag.embeddings import OllamaLangChainEmbeddings
    from rag.retriever import build_retriever
    from rag.memory import build_memory
    from rag.query_processor import extract_filters
    from rag.chain import build_chain
    from config import get_settings
    assert True


def test_pipeline_smoke_mocked():
    with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
         patch("ingestion.pipeline.OllamaEmbedder") as MockEmbedder, \
         patch("ingestion.pipeline.ChromaStore") as MockStore:
        mock_client = MagicMock()
        mock_client.fetch_reports.return_value = []
        MockClient.return_value = mock_client
        from ingestion.pipeline import run_pipeline
        run_pipeline(limit=1)
        mock_client.fetch_reports.assert_called_once()
