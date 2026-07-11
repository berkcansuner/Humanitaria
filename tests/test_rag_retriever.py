import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from rag.retriever import (
    build_retriever, _get_vectorstore, _build_pinecone_filter,
    dedupe_by_document, rerank_by_relevance,
)
from config import get_settings


class TestApplyDateFilter:
    """Defensive post-retrieval date filter (rag.retriever.apply_date_filter).

    Pinecone already applies a server-side numeric date_ts $gte; this is the
    in-Python backstop. Comparison is lexicographic on YYYY-MM-DD strings."""

    def _doc(self, date):
        meta = {"date": date} if date is not None else {}
        return Document(page_content="x", metadata=meta)

    def test_none_filter_returns_all_unchanged(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01"), self._doc("2020-01-01")]
        assert apply_date_filter(docs, None) == docs

    def test_non_dict_filter_returns_all(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01")]
        assert apply_date_filter(docs, "2024-01-01") == docs  # defensive: not a dict

    def test_empty_or_missing_gte_returns_all(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01"), self._doc("2019-05-05")]
        assert apply_date_filter(docs, {"$gte": ""}) == docs
        assert apply_date_filter(docs, {}) == docs

    def test_gte_drops_older_keeps_boundary_and_newer(self):
        from rag.retriever import apply_date_filter
        older, boundary, newer = self._doc("2023-12-31"), self._doc("2024-01-01"), self._doc("2024-06-15")
        out = apply_date_filter([older, boundary, newer], {"$gte": "2024-01-01"})
        assert out == [boundary, newer]  # boundary is inclusive ($gte), older is dropped

    def test_doc_missing_date_is_dropped_when_gte_set(self):
        from rag.retriever import apply_date_filter
        dated, undated = self._doc("2025-01-01"), self._doc(None)
        out = apply_date_filter([dated, undated], {"$gte": "2024-01-01"})
        assert out == [dated]  # no 'date' → treated as "0000-00-00" → below the floor


class TestRetriever:
    def setup_method(self):
        _get_vectorstore.cache_clear()

    def test_build_retriever_returns_retriever(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            settings = get_settings()
            mock_vs = MagicMock()
            mock_retriever = MagicMock()
            mock_vs.as_retriever.return_value = mock_retriever
            mock_get_vs.return_value = mock_vs
            retriever = build_retriever(filter={"country": "Iran"})
            assert retriever is mock_retriever
            mock_vs.as_retriever.assert_called_once_with(
                search_type="mmr",
                search_kwargs={
                    "k": settings.TOP_K_RETRIEVAL,
                    "fetch_k": settings.MMR_FETCH_K,
                    "lambda_mult": settings.MMR_LAMBDA,
                    "filter": {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}},
                },
            )

    def test_build_retriever_k_override(self):
        # Caller raises k to fetch a larger candidate pool; fetch_k must stay
        # strictly larger so MMR has headroom to diversify (was max(MMR_FETCH_K, k),
        # which collapsed to k==20 and made the diversity step a no-op).
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(k=20)
            call_kwargs = mock_vs.as_retriever.call_args[1]["search_kwargs"]
            assert call_kwargs["k"] == 20
            assert call_kwargs["fetch_k"] >= 20 * 3

    def test_build_retriever_date_filter_widens_pool(self):
        # A date filter thins the pool in Python afterwards, so fetch even more.
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(filter={"date": {"from": "2024-01-01"}}, k=20)
            dated_fetch_k = mock_vs.as_retriever.call_args[1]["search_kwargs"]["fetch_k"]
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(k=20)
            plain_fetch_k = mock_vs.as_retriever.call_args[1]["search_kwargs"]["fetch_k"]
        assert dated_fetch_k > plain_fetch_k

    def test_build_retriever_fetch_k_capped_for_wide_k(self):
        # An indicator report's wide candidate pool (top_k 16 → candidate_k 64) with a
        # date filter would compute fetch_k = 64*12 = 768; MMR over that many 3072-dim
        # vectors is slow enough on constrained CPU to blow the request timeout (the
        # indicator-report 502 bug). fetch_k must be capped at MMR_FETCH_K_CAP.
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            settings = get_settings()
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(filter={"date": {"from": "2024-01-01"}}, k=64)
            fetch_k = mock_vs.as_retriever.call_args[1]["search_kwargs"]["fetch_k"]
        assert fetch_k == settings.MMR_FETCH_K_CAP
        assert fetch_k < 64 * 12  # not the uncapped 768

    def test_build_retriever_no_filter(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            settings = get_settings()
            mock_vs = MagicMock()
            mock_retriever = MagicMock()
            mock_vs.as_retriever.return_value = mock_retriever
            mock_get_vs.return_value = mock_vs
            retriever = build_retriever()
            mock_vs.as_retriever.assert_called_once_with(
                search_type="mmr",
                search_kwargs={
                    "k": settings.TOP_K_RETRIEVAL,
                    "fetch_k": settings.MMR_FETCH_K,
                    "lambda_mult": settings.MMR_LAMBDA,
                    "filter": None,
                },
            )


class TestPineconeFilter:
    def test_empty_returns_none(self):
        from rag.retriever import _build_pinecone_filter
        assert _build_pinecone_filter({}) is None
        assert _build_pinecone_filter(None) is None

    def test_country_alias_uses_in(self):
        from rag.retriever import _build_pinecone_filter
        assert _build_pinecone_filter({"country": "Iran"}) == {
            "country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}
        }

    def test_country_non_alias_uses_eq(self):
        from rag.retriever import _build_pinecone_filter
        assert _build_pinecone_filter({"country": "Yemen"}) == {"country": {"$eq": "Yemen"}}

    def test_date_becomes_numeric_date_ts_gte(self):
        from rag.retriever import _build_pinecone_filter
        assert _build_pinecone_filter({"date": {"$gte": "2024-01-01"}}) == {
            "date_ts": {"$gte": 20240101}
        }

    def test_multi_field_implicit_and(self):
        from rag.retriever import _build_pinecone_filter
        assert _build_pinecone_filter({"country": "Yemen", "date": {"$gte": "2024-06-01"}}) == {
            "country": {"$eq": "Yemen"},
            "date_ts": {"$gte": 20240601},
        }

    def test_theme_matches_old_string_or_new_themes_list(self):
        from rag.retriever import _build_pinecone_filter
        # Old records carry `theme` (string); enriched records carry `themes` (list).
        # $or matches both so a re-index never regresses theme filtering.
        assert _build_pinecone_filter({"theme": "Health"}) == {
            "$or": [{"theme": {"$eq": "Health"}}, {"themes": {"$in": ["Health"]}}]
        }

    def test_theme_combines_with_country(self):
        from rag.retriever import _build_pinecone_filter
        f = _build_pinecone_filter({"country": "Yemen", "theme": "Health"})
        assert f["country"] == {"$eq": "Yemen"}
        assert f["$or"] == [{"theme": {"$eq": "Health"}}, {"themes": {"$in": ["Health"]}}]


class TestProviderVectorstore:
    def setup_method(self):
        from rag.retriever import _get_vectorstore
        _get_vectorstore.cache_clear()

    def teardown_method(self):
        from rag.retriever import _get_vectorstore
        _get_vectorstore.cache_clear()

    def test_pinecone_vectorstore_built(self):
        from rag.retriever import _get_vectorstore
        s = MagicMock(PINECONE_API_KEY="k", PINECONE_INDEX="reliefweb-docs", PINECONE_NAMESPACE="")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever.get_embeddings", return_value=MagicMock()), \
             patch("rag.retriever.Pinecone") as MockPC, \
             patch("rag.retriever.PineconeVectorStore") as MockPVS:
            MockPC.return_value.Index.return_value = MagicMock()
            _get_vectorstore.cache_clear()
            _get_vectorstore()
            MockPVS.assert_called_once()

    def test_vectorstore_result_is_cached(self):
        from rag.retriever import _get_vectorstore
        s = MagicMock(PINECONE_API_KEY="k", PINECONE_INDEX="reliefweb-docs", PINECONE_NAMESPACE="")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever.get_embeddings", return_value=MagicMock()), \
             patch("rag.retriever.Pinecone") as MockPC, \
             patch("rag.retriever.PineconeVectorStore") as MockPVS:
            MockPC.return_value.Index.return_value = MagicMock()
            mock_vs = MagicMock()
            MockPVS.return_value = mock_vs
            _get_vectorstore.cache_clear()
            vs1 = _get_vectorstore()
            vs2 = _get_vectorstore()
            assert vs1 is vs2
            MockPVS.assert_called_once()


def _doc(doc_id, content="text", url=None):
    meta = {"doc_id": doc_id}
    if url is not None:
        meta["url"] = url
    return Document(page_content=content, metadata=meta)


class TestDedupeByDocument:
    def test_keeps_first_chunk_per_document(self):
        docs = [_doc("a", "chunk1"), _doc("a", "chunk2"), _doc("b", "chunk3")]
        out = dedupe_by_document(docs)
        assert len(out) == 2
        assert out[0].page_content == "chunk1"  # highest-ranked chunk of "a" kept
        assert out[1].metadata["doc_id"] == "b"

    def test_falls_back_to_url_when_no_doc_id(self):
        d1 = Document(page_content="c1", metadata={"url": "u1"})
        d2 = Document(page_content="c2", metadata={"url": "u1"})
        out = dedupe_by_document([d1, d2])
        assert len(out) == 1

    def test_empty_list(self):
        assert dedupe_by_document([]) == []


class TestRerankByRelevance:
    def test_noop_when_disabled(self):
        s = MagicMock(RERANK_ENABLED=False)
        docs = [_doc("a"), _doc("b")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=5)
        assert out == docs

    def test_noop_when_single_doc(self):
        s = MagicMock(RERANK_ENABLED=True)
        docs = [_doc("a")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=5)
        assert out == docs

    def test_reorders_by_pinecone_result(self):
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        # Pinecone returns indices in relevance order: c, a
        result = MagicMock()
        result.data = [MagicMock(index=2), MagicMock(index=0)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert [d.metadata["doc_id"] for d in out] == ["c", "a"]
        client.inference.rerank.assert_called_once()

    def test_falls_back_to_original_order_on_error(self):
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        client = MagicMock()
        client.inference.rerank.side_effect = RuntimeError("network down")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs[:2]

    def test_passes_truncate_end_to_reranker(self):
        # bge-reranker-v2-m3 rejects query+document pairs over 1024 tokens, and our
        # chunks can exceed that. Pinecone truncates long pairs when asked, so the
        # rerank call must pass parameters={"truncate": "END"} or it 400s and the
        # relevance signal is silently lost to the MMR fallback.
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b")]
        result = MagicMock()
        result.data = [MagicMock(index=0), MagicMock(index=1)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            rerank_by_relevance("q", docs, top_n=2)
        assert client.inference.rerank.call_args.kwargs.get("parameters") == {"truncate": "END"}

    def test_attaches_relevance_score_to_metadata(self):
        # The Pinecone relevance score is attached so rerank_by_recency can blend
        # it with recency instead of using the steep position-based fallback.
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b")]
        result = MagicMock()
        result.data = [MagicMock(index=1, score=0.91), MagicMock(index=0, score=0.42)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert [d.metadata["doc_id"] for d in out] == ["b", "a"]
        assert out[0].metadata["_relevance_score"] == 0.91
        assert out[1].metadata["_relevance_score"] == 0.42
