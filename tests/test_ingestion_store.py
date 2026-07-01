import logging
import pytest
from unittest.mock import patch, MagicMock
from ingestion.store import PineconeStore, get_store


def _mock_pinecone_settings():
    s = MagicMock()
    s.PINECONE_API_KEY = "k"
    s.PINECONE_INDEX = "reliefweb-docs"
    s.PINECONE_NAMESPACE = ""
    return s


class TestPineconeStore:
    def _make_store(self, mock_index):
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

    def test_upsert_chunks_batches_over_request_limit(self):
        # Pinecone caps a single upsert at ~4MB; large batches must be split.
        mock_index = MagicMock()
        store = self._make_store(mock_index)
        chunks = [{"id": f"abc_{i}", "content": "c", "metadata": {"doc_id": "abc"}} for i in range(250)]
        embeddings = [[0.1] * 3072 for _ in range(250)]
        store.upsert_chunks(chunks, embeddings)
        assert mock_index.upsert.call_count == 3  # 100 + 100 + 50
        assert len(mock_index.upsert.call_args_list[0][1]["vectors"]) == 100
        assert len(mock_index.upsert.call_args_list[2][1]["vectors"]) == 50

    def test_upsert_retries_on_429_then_succeeds(self):
        # Pinecone serverless rate-limits writes (429) under sustained volume;
        # the upsert must back off and retry instead of dropping the batch.
        mock_index = MagicMock()
        mock_index.upsert.side_effect = [Exception("(429) Too Many Requests"), Exception("(429)"), None]
        store = self._make_store(mock_index)
        chunks = [{"id": "abc_0", "content": "c", "metadata": {"doc_id": "abc"}}]
        with patch("ingestion.store.time.sleep") as mock_sleep:
            store.upsert_chunks(chunks, [[0.1] * 3072])
        assert mock_index.upsert.call_count == 3   # failed twice, succeeded on 3rd
        assert mock_sleep.call_count == 2          # backed off before each retry

    def test_upsert_reraises_non_429_immediately(self):
        # Non-rate-limit errors are not retried — fail fast.
        mock_index = MagicMock()
        mock_index.upsert.side_effect = Exception("500 internal error")
        store = self._make_store(mock_index)
        chunks = [{"id": "abc_0", "content": "c", "metadata": {"doc_id": "abc"}}]
        with patch("ingestion.store.time.sleep"):
            with pytest.raises(Exception, match="500"):
                store.upsert_chunks(chunks, [[0.1] * 3072])
        assert mock_index.upsert.call_count == 1

    def test_delete_document_chunks_lists_by_prefix_then_deletes(self):
        mock_index = MagicMock()
        mock_index.list.return_value = iter([["abc_0", "abc_5"]])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc")
        mock_index.list.assert_called_once_with(prefix="abc_", namespace=None)
        mock_index.delete.assert_called_once_with(ids=["abc_0", "abc_5"], namespace=None)

    def test_delete_document_chunks_keeps_current_ids(self):
        # With keep_ids, only surplus/stale chunks are deleted — current chunks stay.
        mock_index = MagicMock()
        mock_index.list.return_value = iter([["abc_0", "abc_1", "abc_2", "abc_3"]])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc", keep_ids={"abc_0", "abc_1"})
        mock_index.delete.assert_called_once_with(ids=["abc_2", "abc_3"], namespace=None)

    def test_delete_document_chunks_keep_ids_noop_when_all_kept(self):
        # If every listed chunk is a current id, nothing is deleted.
        mock_index = MagicMock()
        mock_index.list.return_value = iter([["abc_0", "abc_1"]])
        store = self._make_store(mock_index)
        store.delete_document_chunks("abc", keep_ids={"abc_0", "abc_1"})
        mock_index.delete.assert_not_called()

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
        mock_index = MagicMock()
        mock_index.delete.side_effect = Exception("namespace missing")
        store = self._make_store(mock_index)
        with caplog.at_level(logging.WARNING):
            store.clear_collection()
        assert "Failed to clear Pinecone namespace" in caplog.text


class TestGetStoreFactory:
    def test_factory_returns_pinecone(self):
        with patch("ingestion.store.get_settings", return_value=_mock_pinecone_settings()), \
             patch("ingestion.store.Pinecone"):
            assert isinstance(get_store(), PineconeStore)
