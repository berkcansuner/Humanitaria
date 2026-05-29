import pytest
from unittest.mock import patch, MagicMock
from rag.retriever import build_retriever, _get_vectorstore, _build_chroma_filter
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

    def test_operator_field_passed_through(self):
        result = _build_chroma_filter({"date": {"$gte": "2024-01-01"}})
        assert result == {"date": {"$gte": "2024-01-01"}}

    def test_multi_field_uses_and(self):
        result = _build_chroma_filter({"country": "Iran", "theme": "Health"})
        assert result == {"$and": [
            {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}},
            {"theme": {"$eq": "Health"}},
        ]}

    def test_multi_field_with_operator(self):
        result = _build_chroma_filter({"country": "Iran", "date": {"$gte": "2024-01-01"}})
        assert result == {"$and": [
            {"country": {"$in": ["Iran", "Iran (Islamic Republic of)"]}},
            {"date": {"$gte": "2024-01-01"}},
        ]}


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

    def test_build_retriever_multi_field_filter_uses_and(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            settings = get_settings()
            mock_vs = MagicMock()
            mock_vs.as_retriever.return_value = MagicMock()
            mock_get_vs.return_value = mock_vs
            build_retriever(filter={"country": "Iran", "date": {"$gte": "2024-01-01"}})
            call_kwargs = mock_vs.as_retriever.call_args[1]
            chroma_filter = call_kwargs["search_kwargs"]["filter"]
            assert "$and" in chroma_filter
            assert len(chroma_filter["$and"]) == 2

    def test_get_vectorstore_caches_chroma(self):
        with patch("rag.retriever.Chroma") as MockChroma:
            mock_vs1 = MagicMock()
            MockChroma.return_value = mock_vs1
            vs1 = _get_vectorstore()
            vs2 = _get_vectorstore()
            assert vs1 is vs2
            MockChroma.assert_called_once()
