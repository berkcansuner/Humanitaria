import pytest
from unittest.mock import patch, MagicMock
from rag.retriever import build_retriever, _get_vectorstore
from config import get_settings


class TestRetriever:
    def setup_method(self):
        _get_vectorstore.cache_clear()

    def test_build_retriever_returns_retriever(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_retriever = MagicMock()
            mock_vs.as_retriever.return_value = mock_retriever
            mock_get_vs.return_value = mock_vs
            retriever = build_retriever(filter={"country": "Iran"})
            assert retriever is mock_retriever
            mock_vs.as_retriever.assert_called_once_with(
                search_type="mmr",
                search_kwargs={"k": get_settings().TOP_K_RETRIEVAL, "filter": {"country": "Iran"}}
            )

    def test_build_retriever_no_filter(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_retriever = MagicMock()
            mock_vs.as_retriever.return_value = mock_retriever
            mock_get_vs.return_value = mock_vs
            retriever = build_retriever()
            mock_vs.as_retriever.assert_called_once_with(
                search_type="mmr",
                search_kwargs={"k": get_settings().TOP_K_RETRIEVAL, "filter": None}
            )

    def test_get_vectorstore_caches_chroma(self):
        with patch("rag.retriever.Chroma") as MockChroma:
            mock_vs1 = MagicMock()
            MockChroma.return_value = mock_vs1
            vs1 = _get_vectorstore()
            vs2 = _get_vectorstore()
            assert vs1 is vs2
            MockChroma.assert_called_once()
