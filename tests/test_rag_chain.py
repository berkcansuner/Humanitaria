from unittest.mock import patch, MagicMock
from langchain_openai import ChatOpenAI
from rag.chain import build_chain


class TestChain:
    def setup_method(self):
        import rag.chain
        rag.chain._chain = None

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_returns_runnable(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        chain = build_chain()
        assert chain is not None

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_singleton(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        chain1 = build_chain()
        chain2 = build_chain()
        assert chain1 is chain2

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_passes_api_key(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        build_chain()
        _, kwargs = MockLLM.call_args
        assert "api_key" in kwargs

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_streaming_enabled(self, MockLLM):
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        build_chain()
        _, kwargs = MockLLM.call_args
        assert kwargs.get("streaming") is True

    @patch("rag.chain.ChatOpenAI")
    def test_build_chain_no_runnablewithmessagehistory(self, MockLLM):
        """Chain is a plain LCEL runnable, not wrapped in RunnableWithMessageHistory."""
        from langchain_core.runnables.history import RunnableWithMessageHistory
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        chain = build_chain()
        assert not isinstance(chain, RunnableWithMessageHistory)
