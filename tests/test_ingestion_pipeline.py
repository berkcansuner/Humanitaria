import pytest
from unittest.mock import patch, MagicMock
from ingestion.pipeline import run_pipeline, IngestionStats, BATCH_SIZE


class TestPipeline:
    def test_run_pipeline_with_limit(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            run_pipeline(limit=1)
            mock_client.fetch.assert_called_once_with("reports", limit=1, offset=0, date_from=None, country=None)
            mock_store.upsert_chunks.assert_called_once()
            mock_store.clear_collection.assert_not_called()

    def test_run_pipeline_passes_country(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = []
            MockClient.return_value = mock_client
            mock_get_emb.return_value = MagicMock()
            mock_get_store.return_value = MagicMock()
            run_pipeline(limit=1, country="SDN")
            mock_client.fetch.assert_called_once_with("reports", limit=1, offset=0, date_from=None, country="SDN")

    def test_run_pipeline_with_force(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            run_pipeline(limit=1, force=True)
            mock_store.clear_collection.assert_called_once()

    def test_run_pipeline_multiple_endpoints(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            run_pipeline(limit=1, endpoints=["reports", "disasters"])
            assert mock_client.fetch.call_count == 2
            calls = mock_client.fetch.call_args_list
            endpoint_names = [c[0][0] for c in calls]
            assert "reports" in endpoint_names
            assert "disasters" in endpoint_names


class TestIngestionStats:
    def test_default_values(self):
        stats = IngestionStats(endpoint="reports")
        assert stats.endpoint == "reports"
        assert stats.total == 0
        assert stats.succeeded == 0
        assert stats.failed == 0
        assert stats.skipped == 0
        assert stats.errors == []

    def test_custom_values(self):
        stats = IngestionStats(
            endpoint="disasters",
            total=100,
            succeeded=90,
            failed=5,
            skipped=5,
            errors=[{"url": "https://x", "error": "parse failed"}],
        )
        assert stats.total == 100
        assert stats.succeeded == 90
        assert len(stats.errors) == 1


class TestPipelineErrorIsolation:
    def test_single_doc_failure_continues_pipeline(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
            MockClient.return_value = mock_client
            good_doc = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_parse.side_effect = [good_doc, Exception("parse error"), good_doc]
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            # 2 successful docs × 1 chunk each = 2 embeddings needed
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            stats = run_pipeline(limit=3)
            assert stats["reports"].succeeded == 2
            assert stats["reports"].failed == 1
            # New batch pipeline: 2 successful docs upserted together in 1 call
            assert mock_store.upsert_chunks.call_count == 1

    def test_orphan_chunks_deleted_before_upsert(self):
        """delete_document_chunks is called for each document before upserting new chunks."""
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}, {"id": "2"}]
            MockClient.return_value = mock_client
            doc1 = {"id": "id1", "url": "u1", "title": "t1", "body": "b1", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            doc2 = {"id": "id2", "url": "u2", "title": "t2", "body": "b2", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_parse.side_effect = [doc1, doc2]
            mock_chunk.return_value = [{"id": "c_0", "content": "b", "metadata": {}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            run_pipeline(limit=2)
            # delete_document_chunks called once per doc (2 docs)
            assert mock_store.delete_document_chunks.call_count == 2
            called_ids = {c[0][0] for c in mock_store.delete_document_chunks.call_args_list}
            assert called_ids == {"id1", "id2"}

    def test_empty_body_counted_as_skipped(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}, {"id": "2"}]
            MockClient.return_value = mock_client
            mock_parse.side_effect = [
                {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"},
                {"id": "def", "url": "u2", "title": "t2", "body": "", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"},
            ]
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            stats = run_pipeline(limit=2)
            assert stats["reports"].succeeded == 1
            assert stats["reports"].skipped == 1

    def test_parse_returns_none_counted_as_skipped(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = None
            mock_emb = MagicMock()
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            stats = run_pipeline(limit=1)
            assert stats["reports"].skipped == 1
            assert stats["reports"].succeeded == 0
            mock_emb.embed_documents.assert_not_called()

    def test_run_pipeline_returns_stats_dict(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": "1"}]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            stats = run_pipeline(limit=1, endpoints=["reports", "disasters"])
            assert isinstance(stats, dict)
            assert "reports" in stats
            assert "disasters" in stats
            assert isinstance(stats["reports"], IngestionStats)

    def test_errors_capped_at_10(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            mock_client.fetch.return_value = [{"id": str(i)} for i in range(15)]
            MockClient.return_value = mock_client
            mock_parse.side_effect = Exception("fail")
            mock_emb = MagicMock()
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            stats = run_pipeline(limit=15)
            assert stats["reports"].failed == 15
            assert len(stats["reports"].errors) == 10

    def test_batch_size_is_500(self):
        assert BATCH_SIZE == 500

    def test_multi_batch_fetches_in_batches(self):
        with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
             patch("ingestion.pipeline.parse") as mock_parse, \
             patch("ingestion.pipeline.chunk_document") as mock_chunk, \
             patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
             patch("ingestion.pipeline.get_store") as mock_get_store:
            mock_client = MagicMock()
            # First batch returns items, second batch returns empty (end of data)
            mock_client.fetch.side_effect = [
                [{"id": str(i)} for i in range(3)],
                [],
            ]
            MockClient.return_value = mock_client
            mock_parse.return_value = {"id": "abc", "url": "u", "title": "t", "body": "b", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "report"}
            mock_chunk.return_value = [{"id": "abc_0", "content": "b", "metadata": {"url": "u", "title": "t", "country": "", "theme": "", "date": "", "source": "", "format": "", "doctype": "report"}}]
            mock_emb = MagicMock()
            mock_emb.embed_documents.side_effect = lambda texts: [[0.1] * 4096 for _ in texts]
            mock_get_emb.return_value = mock_emb
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            # Request 10 docs, but only 3 available - batch_size should be min(500, 10)
            stats = run_pipeline(limit=10)
            assert stats["reports"].succeeded == 3
            assert stats["reports"].total == 3
            # First call with batch_limit=min(500, 10)=10, second with batch_limit=min(500, 10-3)=7
            assert mock_client.fetch.call_count == 2
