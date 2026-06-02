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


def _settings():
    s = MagicMock()
    s.GEMINI_LLM_MODEL = "gemini-2.5-pro"
    s.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    s.GEMINI_API_KEY = "gemini-key"
    return s


class TestChainProvider:
    def setup_method(self):
        import rag.chain
        rag.chain._chain = None

    @patch("rag.chain.get_settings")
    @patch("rag.chain.ChatOpenAI")
    def test_gemini_provider_uses_gemini_config(self, MockLLM, mock_settings):
        mock_settings.return_value = _settings()
        MockLLM.return_value = MagicMock(spec=ChatOpenAI)
        build_chain()
        _, kwargs = MockLLM.call_args
        assert kwargs["model"] == "gemini-2.5-pro"
        assert kwargs["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai/"
        assert kwargs["api_key"] == "gemini-key"
        assert kwargs["streaming"] is True


def test_system_prompt_has_date_awareness_rule():
    from rag.chain import _SYSTEM_PROMPT
    low = _SYSTEM_PROMPT.lower()
    # Pin rule 9 specifically: "date"/"most recent" alone also occur in earlier
    # rules, so assert the rule-9 phrasing to guard against its accidental removal.
    assert "prioritize the most recent" in low
    assert "(yyyy-mm-dd)" in low
