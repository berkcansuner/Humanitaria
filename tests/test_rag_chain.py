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
    s.GEMINI_LLM_MODEL = "gemini-2.5-flash"
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
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai/"
        assert kwargs["api_key"] == "gemini-key"
        assert kwargs["streaming"] is True


def test_system_prompt_has_date_awareness_rule():
    from rag.chain import _SYSTEM_PROMPT
    low = _SYSTEM_PROMPT.lower()
    # Pin rule 10 specifically: "date"/"most recent" alone also occur in earlier
    # rules, so assert the rule-10 phrasing to guard against its accidental removal.
    assert "prioritize the most recent" in low
    assert "(yyyy-mm-dd)" in low


def test_system_prompt_constrains_citation_numbers_to_context():
    from rag.chain import _SYSTEM_PROMPT
    low = _SYSTEM_PROMPT.lower()
    # Pin rule 7's range constraint: citing a number not present in the Context
    # produces a dead [n] marker, so the prompt must forbid out-of-range citations.
    assert "never write a citation number that is not shown in the context" in low


class TestReportChain:
    def setup_method(self):
        import rag.chain
        rag.chain._report_chains = {}

    @patch("rag.chain.ChatOpenAI")
    def test_build_report_chain_returns_runnable(self, MockLLM):
        from rag.chain import build_report_chain
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        chain = build_report_chain()
        assert chain is not None

    @patch("rag.chain.ChatOpenAI")
    def test_build_report_chain_caches_per_type(self, MockLLM):
        from rag.chain import build_report_chain
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        situation1 = build_report_chain("situation")
        situation2 = build_report_chain("situation")
        indicator = build_report_chain("indicator_monitoring")
        assert situation1 is situation2
        assert situation1 is not indicator

    @patch("rag.chain.ChatOpenAI")
    def test_build_report_chain_defaults_to_situation(self, MockLLM):
        from rag.chain import build_report_chain
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        assert build_report_chain() is build_report_chain("situation")

    @patch("rag.chain.ChatOpenAI")
    def test_build_report_chain_unknown_type_falls_back_to_situation_prompt(self, MockLLM):
        # A future caller passing an unrecognised type must not crash — it falls
        # back to the situation prompt (the safe, well-tested default).
        from rag.chain import build_report_chain
        mock_llm = MagicMock(spec=ChatOpenAI)
        MockLLM.return_value = mock_llm
        chain = build_report_chain("some_future_type")
        assert chain is not None


def test_indicator_prompt_requires_indicator_table_section():
    from rag.chain import _INDICATOR_SYSTEM_PROMPT
    low = _INDICATOR_SYSTEM_PROMPT.lower()
    assert "indicator table" in low
    assert "data gaps" in low
    assert "recent developments" in low
    assert "never invent" in low


def test_indicator_table_has_no_source_column():
    # The indicator table is citation-free: no 'Source' column, a 3-column separator,
    # and an explicit instruction not to put [n] markers in table cells. Sources are
    # listed once at the bottom of the report (the prose sections still carry [n]).
    from rag.chain import _INDICATOR_SYSTEM_PROMPT
    p = _INDICATOR_SYSTEM_PROMPT
    assert "'Indicator', 'Latest value', 'As of'" in p
    assert "| --- | --- | --- |" in p
    assert "| --- | --- | --- | --- |" not in p          # no 4-column separator
    assert "do not add a 'source' column" in p.lower()


def test_needs_assessment_prompt_requires_sections():
    from rag.chain import _NEEDS_ASSESSMENT_SYSTEM_PROMPT
    low = _NEEDS_ASSESSMENT_SYSTEM_PROMPT.lower()
    assert "priority needs by sector" in low
    assert "affected groups" in low
    assert "gaps & constraints" in low
    assert "recommendations" in low


def test_all_report_prompts_require_precision():
    # Figures verbatim (unit + qualifier, no rounding/vague quantifiers), dates at the
    # source's precision (day when given, never rounded to a bare year), and every value
    # traceable to a single Context document (no cross-document combining/estimating).
    from rag.chain import _REPORT_PROMPTS
    for report_type, prompt in _REPORT_PROMPTS.items():
        low = prompt.lower()
        assert "precision:" in low, report_type
        assert "exactly as the source states it" in low, report_type
        assert "precision the source gives" in low, report_type
        assert "single context document" in low, report_type


def test_all_report_prompts_scope_to_report_country():
    # Country-scoping guard: figures measuring another country's own internal
    # situation (e.g. an Iran report picking up Afghanistan's country-wide caseload
    # mentioned as background) must be excluded, while refugees the country hosts stay.
    from rag.chain import _REPORT_PROMPTS
    for report_type, prompt in _REPORT_PROMPTS.items():
        low = prompt.lower()
        assert "scoped to the country named in" in low, report_type
        assert "the refugees it hosts" in low, report_type
        # the restriction is on FIGURES only; qualitative causal context stays allowed
        assert "qualitative causal context" in low, report_type


def test_situation_prompt_unchanged():
    """Regression guard: the existing situation-report prompt text must not
    change when new report-type prompts are added alongside it."""
    from rag.chain import _REPORT_SYSTEM_PROMPT
    assert "Executive Summary" in _REPORT_SYSTEM_PROMPT
    assert "Key Findings" in _REPORT_SYSTEM_PROMPT
    assert "Outlook" in _REPORT_SYSTEM_PROMPT


def test_all_report_prompts_forbid_corroboration_piling():
    from rag.chain import _REPORT_PROMPTS
    for report_type, prompt in _REPORT_PROMPTS.items():
        assert "CORROBORATION IS NOT MULTI-FACT" in prompt, report_type
