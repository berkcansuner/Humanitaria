from unittest.mock import patch, MagicMock
from langchain_openai import ChatOpenAI
from rag.chain import build_chain


class TestChain:
    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_returns_runnable_with_history(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        # Reset singleton
        import rag.chain
        rag.chain._chain = None
        chain = build_chain()
        assert chain is not None

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_singleton(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        import rag.chain
        rag.chain._chain = None
        chain1 = build_chain()
        chain2 = build_chain()
        assert chain1 is chain2

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_passes_api_key(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        import rag.chain
        rag.chain._chain = None
        build_chain()
        args, kwargs = MockLLM.call_args
        assert "api_key" in kwargs

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_streaming_enabled(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        import rag.chain
        rag.chain._chain = None
        build_chain()
        args, kwargs = MockLLM.call_args
        assert kwargs.get("streaming") is True