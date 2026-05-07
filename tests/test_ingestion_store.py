import logging
import pytest
from unittest.mock import patch, MagicMock
from ingestion.store import ChromaStore


class TestChromaStore:
    def test_upsert_chunks(self):
        store = ChromaStore()
        mock_collection = MagicMock()
        store.collection = mock_collection
        chunks = [
            {"id": "id1", "content": "c1", "metadata": {"url": "u1", "title": "t1", "country": "Iran", "theme": "Food", "date": "2026-04-01", "source": "WFP", "format": "Report"}},
            {"id": "id2", "content": "c2", "metadata": {"url": "u2", "title": "t2", "country": "Turkey", "theme": "Health", "date": "2026-04-02", "source": "WHO", "format": "Update"}},
        ]
        embeddings = [[0.1] * 4096, [0.2] * 4096]
        store.upsert_chunks(chunks, embeddings)
        mock_collection.upsert.assert_called_once()
        args = mock_collection.upsert.call_args[1]
        assert args["ids"] == ["id1", "id2"]
        assert len(args["embeddings"]) == 2

    def test_clear_collection(self):
        store = ChromaStore()
        mock_client = MagicMock()
        store.client = mock_client
        mock_collection = MagicMock()
        store.collection = mock_collection
        store.clear_collection()
        mock_client.delete_collection.assert_called_once_with(name=store.settings.CHROMA_COLLECTION)
        mock_client.get_or_create_collection.assert_called_once_with(
            name=store.settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

    def test_idempotent_upsert(self):
        store = ChromaStore()
        mock_collection = MagicMock()
        store.collection = mock_collection
        chunks = [{"id": "id1", "content": "c1", "metadata": {"url": "u1", "title": "t1", "country": "", "theme": "", "date": "", "source": "", "format": ""}}]
        embeddings = [[0.1] * 4096]
        store.upsert_chunks(chunks, embeddings)
        store.upsert_chunks(chunks, embeddings)
        assert mock_collection.upsert.call_count == 2


class TestChromaStoreErrorHandling:
    def test_clear_collection_logs_warning_on_error(self, caplog):
        store = ChromaStore()
        mock_client = MagicMock()
        store.client = mock_client
        mock_collection = MagicMock()
        store.collection = mock_collection
        mock_client.delete_collection.side_effect = Exception("delete failed")
        with caplog.at_level(logging.WARNING):
            store.clear_collection()
        assert "Failed to clear collection" in caplog.text
        mock_client.get_or_create_collection.assert_called_once()
