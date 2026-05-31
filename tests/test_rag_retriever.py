import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from rag.retriever import (
    build_retriever, _get_vectorstore, _build_chroma_filter, _build_pinecone_filter,
    dedupe_by_document, rerank_by_relevance,
)
from config import get_settings


class TestChromaFilter:
    def test_empty_filter_returns_none(self):
        assert _build_chroma_filter({}) is None
        assert _build_chroma_filter(None) is None

    def test_single_field_country_uses_in_for_aliased(self):
        # Countries with full ReliefWeb names get $in with both forms
        result = _build_chroma_filter({"country": "Iran"})
        assert result == {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}}

    def test_single_field_country_eq_for_non_aliased(self):
        # Countries without a known alias get $eq
        result = _build_chroma_filter({"country": "Yemen"})
        assert result == {"country": {"$eq": "Yemen"}}

    def test_date_field_excluded(self):
        # Date is excluded from Chroma (applied in Python post-retrieval)
        result = _build_chroma_filter({"date": {"$gte": "2024-01-01"}})
        assert result is None

    def test_multi_field_uses_and(self):
        result = _build_chroma_filter({"country": "Iran", "theme": "Health"})
        assert result == {"$and": [
            {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}},
            {"theme": {"$eq": "Health"}},
        ]}

    def test_date_excluded_from_chroma_filter(self):
        # Date filtering is done in Python post-retrieval; ChromaDB $gte only supports numbers
        result = _build_chroma_filter({"country": "Iran", "date": {"$gte": "2024-01-01"}})
        # date key is stripped, only country remains
        assert result == {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}}


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
        # Caller raises k to fetch a larger candidate pool; fetch_k follows.
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(k=20)
            call_kwargs = mock_vs.as_retriever.call_args[1]["search_kwargs"]
            assert call_kwargs["k"] == 20
            assert call_kwargs["fetch_k"] >= 20

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

    def test_build_retriever_date_excluded_from_chroma(self):
        # Force chroma provider so the test is independent of the ambient .env.
        with patch("rag.retriever._get_vectorstore") as mock_get_vs, \
             patch.object(get_settings(), "VECTOR_STORE_PROVIDER", "chroma"):
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(filter={"country": "Iran", "date": {"$gte": "2024-01-01"}})
            call_kwargs = mock_vs.as_retriever.call_args[1]
            chroma_filter = call_kwargs["search_kwargs"]["filter"]
            # Only country remains; date is applied in Python post-retrieval
            assert chroma_filter == {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}}

    def test_get_vectorstore_caches_chroma(self):
        # Force chroma provider so the test is independent of the ambient .env.
        with patch("rag.retriever.Chroma") as MockChroma, \
             patch("rag.retriever.get_embeddings", return_value=MagicMock()), \
             patch.object(get_settings(), "VECTOR_STORE_PROVIDER", "chroma"):
            mock_vs1 = MagicMock()
            MockChroma.return_value = mock_vs1
            vs1 = _get_vectorstore()
            vs2 = _get_vectorstore()
            assert vs1 is vs2
            MockChroma.assert_called_once()


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


class TestProviderVectorstore:
    def setup_method(self):
        from rag.retriever import _get_vectorstore
        _get_vectorstore.cache_clear()

    def teardown_method(self):
        from rag.retriever import _get_vectorstore
        _get_vectorstore.cache_clear()

    def test_pinecone_vectorstore_built_when_provider_pinecone(self):
        from rag.retriever import _get_vectorstore
        s = MagicMock(VECTOR_STORE_PROVIDER="pinecone", EMBED_PROVIDER="gemini",
                     PINECONE_API_KEY="k", PINECONE_INDEX="reliefweb-docs", PINECONE_NAMESPACE="")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever.get_embeddings", return_value=MagicMock()), \
             patch("rag.retriever.Pinecone") as MockPC, \
             patch("rag.retriever.PineconeVectorStore") as MockPVS:
            MockPC.return_value.Index.return_value = MagicMock()
            _get_vectorstore.cache_clear()
            _get_vectorstore()
            MockPVS.assert_called_once()

    def test_chroma_vectorstore_built_when_provider_chroma(self):
        from rag.retriever import _get_vectorstore
        s = MagicMock(VECTOR_STORE_PROVIDER="chroma", EMBED_PROVIDER="ollama",
                     CHROMA_COLLECTION="reliefweb_docs", CHROMA_DB_PATH="./chroma_db")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever.get_embeddings", return_value=MagicMock()), \
             patch("rag.retriever.Chroma") as MockChroma:
            _get_vectorstore.cache_clear()
            _get_vectorstore()
            MockChroma.assert_called_once()


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
    def test_noop_when_not_pinecone(self):
        # Chroma provider: rerank is skipped, list truncated to top_n.
        s = MagicMock(RERANK_ENABLED=True, VECTOR_STORE_PROVIDER="chroma")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs[:2]

    def test_noop_when_disabled(self):
        s = MagicMock(RERANK_ENABLED=False, VECTOR_STORE_PROVIDER="pinecone")
        docs = [_doc("a"), _doc("b")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=5)
        assert out == docs

    def test_reorders_by_pinecone_result(self):
        s = MagicMock(RERANK_ENABLED=True, VECTOR_STORE_PROVIDER="pinecone",
                      RERANK_MODEL="bge-reranker-v2-m3")
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
        s = MagicMock(RERANK_ENABLED=True, VECTOR_STORE_PROVIDER="pinecone",
                      RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        client = MagicMock()
        client.inference.rerank.side_effect = RuntimeError("network down")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs[:2]
