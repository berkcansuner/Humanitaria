"""Reports think harder than chat.

Live checks (2026-11-15): at reasoning_effort=low the report model did not apply
the comparison rules (an August 2025 earthquake kept in "What changed"). Reports
get their own effort (default medium = 8,192 thinking tokens on Gemini 2.5) and a
longer timeout, since the first token arrives only after the thinking; chat keeps
its fast settings.
"""
from unittest.mock import MagicMock, patch


def _settings(report_effort="medium"):
    s = MagicMock()
    s.GEMINI_API_KEY = "dummy"
    s.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    s.GEMINI_LLM_MODEL = "gemini-2.5-flash"
    s.GEMINI_REASONING_EFFORT = "low"
    s.CHAT_LLM_TIMEOUT = 45
    s.REPORT_REASONING_EFFORT = report_effort
    s.REPORT_LLM_TIMEOUT = 150
    return s


def _llm(runnable):
    from langchain_openai import ChatOpenAI
    return next(s for s in runnable.steps if isinstance(s, ChatOpenAI))


def _build(settings):
    from rag import chain
    with patch.object(chain, "get_settings", return_value=settings):
        chain._chain = None
        chain._report_chains.clear()
        try:
            return _llm(chain.build_chain()), _llm(chain.build_report_chain("situation"))
        finally:
            chain._chain = None
            chain._report_chains.clear()


def test_report_chain_uses_report_effort_and_timeout():
    chat, report = _build(_settings())
    assert report.reasoning_effort == "medium"
    assert report.request_timeout == 150


def test_chat_chain_keeps_its_fast_settings():
    chat, report = _build(_settings())
    assert chat.reasoning_effort == "low"
    assert chat.request_timeout == 45


def test_empty_report_effort_sends_none():
    chat, report = _build(_settings(report_effort=""))
    assert report.reasoning_effort is None


def test_config_defaults():
    from config import Settings
    s = Settings(_env_file=None)
    assert s.REPORT_REASONING_EFFORT == "medium"
    assert s.REPORT_LLM_TIMEOUT >= 120
