from unittest.mock import patch, MagicMock
from langchain_community.chat_models import ChatOllama
from langchain_core.retrievers import BaseRetriever
from rag.retriever import build_retriever
from rag.memory import build_memory
from rag.chain import build_chain


class TestRetrieverAndMemory:
    def test_build_retriever_returns_callable(self):
        with patch("rag.retriever._get_vectorstore") as mock_get_vs:
            mock_vs = MagicMock()
            mock_retriever = MagicMock()
            mock_vs.as_retriever.return_value = mock_retriever
            mock_get_vs.return_value = mock_vs
            retriever = build_retriever(filter={"country": "Iran"})
            mock_vs.as_retriever.assert_called_once()
            assert retriever is mock_retriever

    def test_build_memory(self):
        mem = build_memory()
        assert mem is not None
        assert mem.k == 5


class TestChain:
    def test_build_chain(self):
        with patch("rag.chain.ChatOllama") as MockLLM, \
             patch("rag.chain.build_retriever") as mock_retriever_builder:
            mock_llm = MagicMock(spec=ChatOllama)
            MockLLM.return_value = mock_llm
            mock_retriever = MagicMock(spec=BaseRetriever)
            mock_retriever_builder.return_value = mock_retriever
            chain = build_chain(filter={"country": "Iran"})
            assert chain is not None

    def test_build_chain_passes_api_key(self):
        with patch("rag.chain.ChatOllama") as MockLLM, \
             patch("rag.chain.build_retriever") as mock_retriever_builder:
            mock_llm = MagicMock(spec=ChatOllama)
            MockLLM.return_value = mock_llm
            mock_retriever = MagicMock(spec=BaseRetriever)
            mock_retriever_builder.return_value = mock_retriever
            build_chain()
            args, kwargs = MockLLM.call_args
            assert "headers" in kwargs
            assert "Authorization" in kwargs["headers"]

    def test_build_chain_uses_provided_memory(self):
        with patch("rag.chain.ChatOllama") as MockLLM, \
             patch("rag.chain.build_retriever") as mock_retriever_builder, \
             patch("rag.chain.ConversationalRetrievalChain") as MockConvChain:
            mock_llm = MagicMock(spec=ChatOllama)
            MockLLM.return_value = mock_llm
            mock_retriever = MagicMock(spec=BaseRetriever)
            mock_retriever_builder.return_value = mock_retriever
            mock_memory = MagicMock()
            build_chain(memory=mock_memory)
            _, kwargs = MockConvChain.from_llm.call_args
            assert kwargs["memory"] is mock_memory
