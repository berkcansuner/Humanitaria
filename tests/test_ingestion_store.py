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


def _mock_pinecone_settings():
    s = MagicMock()
    s.PINECONE_API_KEY = "k"
    s.PINECONE_INDEX = "reliefweb-docs"
    s.PINECONE_NAMESPACE = ""
    return s


def _mock_pinecone_settings_with_provider():
    s = _mock_pinecone_settings()
    s.VECTOR_STORE_PROVIDER = "pinecone"
    return s


class TestPineconeStore:
    def _make_store(self, mock_index):
        from ingestion.store import PineconeStore
        with patch("ingestion.store.get_settings", return_value=_mock_pinecone_settings()), \
             patch("ingestion.store.Pinecone") as MockPC:
            pc = MagicMock()
            pc.Index.return_value = mock_index
            MockPC.return_value = pc
            return PineconeStore()

    def test_upsert_chunks_includes_text_and_values(self):
        mock_index = MagicMock()
        store = self._make_store(mock_index)
        chunks = [{"id": "abc_0", "content": "c1", "metadata": {"doc_id": "abc", "date_ts": 20240101}}]
        store.upsert_chunks(chunks, [[0.1] * 3072])
        mock_index.upsert.assert_called_once()
        vectors = mock_index.upsert.call_args[1]["vectors"]
        assert vectors[0]["id"] == "abc_0"
        assert vectors[0]["values"] == [0.1] * 3072
        assert vectors[0]["metadata"]["text"] == "c1"
        assert vectors[0]["metadata"]["date_ts"] == 20240101
        assert mock_index.upsert.call_args[1]["namespace"] is None

    def test_delete_document_chunks_lists_by_prefix_then_deletes(self):
        mock_index = MagicMock()
        mock_index.list.return_value = iter([["abc_0", "abc_5"]])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc")
        mock_index.list.assert_called_once_with(prefix="abc_", namespace=None)
        mock_index.delete.assert_called_once_with(ids=["abc_0", "abc_5"], namespace=None)

    def test_delete_document_chunks_noop_when_empty(self):
        mock_index = MagicMock()
        mock_index.list.return_value = iter([])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc")
        mock_index.delete.assert_not_called()

    def test_delete_document_chunks_batches_over_1000(self):
        # Pinecone delete accepts at most 1000 ids per request.
        mock_index = MagicMock()
        all_ids = [f"abc_{i}" for i in range(1500)]
        mock_index.list.return_value = iter([all_ids])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc")
        assert mock_index.delete.call_count == 2
        assert len(mock_index.delete.call_args_list[0][1]["ids"]) == 1000
        assert len(mock_index.delete.call_args_list[1][1]["ids"]) == 500

    def test_clear_collection_deletes_all(self):
        mock_index = MagicMock()
        store = self._make_store(mock_index)
        store.clear_collection()
        mock_index.delete.assert_called_once_with(delete_all=True, namespace=None)

    def test_clear_collection_logs_warning_on_error(self, caplog):
        import logging
        mock_index = MagicMock()
        mock_index.delete.side_effect = Exception("namespace missing")
        store = self._make_store(mock_index)
        with caplog.at_level(logging.WARNING):
            store.clear_collection()
        assert "Failed to clear Pinecone namespace" in caplog.text


class TestGetStoreFactory:
    def test_factory_returns_chroma(self):
        from ingestion.store import get_store, ChromaStore
        s = MagicMock(VECTOR_STORE_PROVIDER="chroma", CHROMA_DB_PATH="./chroma_db",
                     CHROMA_COLLECTION="reliefweb_docs")
        with patch("ingestion.store.get_settings", return_value=s), \
             patch("ingestion.store.chromadb.PersistentClient"):
            assert isinstance(get_store(), ChromaStore)

    def test_factory_returns_pinecone(self):
        from ingestion.store import get_store, PineconeStore
        with patch("ingestion.store.get_settings", return_value=_mock_pinecone_settings_with_provider()), \
             patch("ingestion.store.Pinecone"):
            assert isinstance(get_store(), PineconeStore)
