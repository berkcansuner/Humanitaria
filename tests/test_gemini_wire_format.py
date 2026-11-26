"""Gemini's OpenAI-compatible endpoint only speaks Chat Completions. langchain-openai
1.x can switch ChatOpenAI to the Responses API on its own (model name, certain
params), which Gemini rejects — every client here must build a Chat Completions
payload."""
from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage


def _settings():
    s = MagicMock()
    s.GEMINI_API_KEY = "dummy"
    s.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    s.GEMINI_LLM_MODEL = "gemini-2.5-flash"
    s.REPORT_LLM_MODEL = "report-model-x"
    s.GEMINI_QUERY_MODEL = "gemini-2.5-flash"
    s.GEMINI_REASONING_EFFORT = "low"
    s.CHAT_LLM_TIMEOUT = 45
    s.REPORT_REASONING_EFFORT = "medium"
    s.REPORT_LLM_TIMEOUT = 150
    return s


def _assert_chat_completions(llm):
    payload = llm._get_request_payload([HumanMessage("hi")])
    assert "messages" in payload and "input" not in payload
    assert llm.use_responses_api is False


def _llm_of(runnable):
    """The ChatOpenAI inside a prompt|llm|parser chain or a structured-output wrapper."""
    from langchain_openai import ChatOpenAI
    for step in getattr(runnable, "steps", None) or [getattr(runnable, "first", runnable)]:
        if isinstance(step, ChatOpenAI):
            return step
        bound = getattr(step, "bound", None)
        if isinstance(bound, ChatOpenAI):
            return bound
    raise AssertionError(f"no ChatOpenAI in {runnable!r}")


def test_chat_and_report_chains_use_chat_completions():
    from rag import chain
    with patch.object(chain, "get_settings", return_value=_settings()):
        chain._chain = None
        chain._report_chains.clear()
        _assert_chat_completions(_llm_of(chain.build_chain()))
        _assert_chat_completions(_llm_of(chain.build_report_chain("situation")))
        chain._chain = None
        chain._report_chains.clear()


def test_query_llms_use_chat_completions():
    from rag import query_processor as qp
    with patch("config.get_settings", return_value=_settings()):
        qp._llm_extractor = None
        qp._llm_planner = None
        _assert_chat_completions(_llm_of(qp._get_llm_extractor()))
        _assert_chat_completions(_llm_of(qp._get_llm_planner()))
        qp._llm_extractor = None
        qp._llm_planner = None
