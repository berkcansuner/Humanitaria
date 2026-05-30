import pytest
from unittest.mock import patch, MagicMock
from rag.retriever import build_retriever, _get_vectorstore, _build_chroma_filter, _build_pinecone_filter
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
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(filter={"country": "Iran", "date": {"$gte": "2024-01-01"}})
            call_kwargs = mock_vs.as_retriever.call_args[1]
            chroma_filter = call_kwargs["search_kwargs"]["filter"]
            # Only country remains; date is applied in Python post-retrieval
            assert chroma_filter == {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}}

    def test_get_vectorstore_caches_chroma(self):
        with patch("rag.retriever.Chroma") as MockChroma:
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
