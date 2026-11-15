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
    s.REPORT_LLM_MODEL = "report-model-x"
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


def test_chat_thinks_at_medium_with_room_for_it():
    """Chat moved to medium (2026-11-16, owner's decision). The first token comes
    only after the thinking (up to 8,192 tokens), so 45 s could time out and retry."""
    from config import Settings
    s = Settings(_env_file=None)
    assert s.GEMINI_REASONING_EFFORT == "medium"
    assert s.CHAT_LLM_TIMEOUT >= 90


def test_render_blueprint_sets_chat_to_medium():
    """render.yaml pins the production value; it must not undo the default."""
    import re
    from pathlib import Path
    text = Path(__file__).resolve().parent.parent.joinpath("render.yaml").read_text(encoding="utf-8")
    m = re.search(r"key: GEMINI_REASONING_EFFORT\s*\n\s*value:\s*(\S+)", text)
    assert m and m.group(1).strip('"') == "medium"


def test_report_chain_uses_its_own_model():
    """Reports (few, quality-critical) and chat (many) may run on different models."""
    chat, report = _build(_settings())
    assert report.model_name == "report-model-x"
    assert chat.model_name == "gemini-2.5-flash"


def test_comparison_checker_uses_the_report_model():
    from langchain_openai import ChatOpenAI
    from rag import report_compare as rc
    with patch("config.get_settings", return_value=_settings()):
        rc._checker_llm = None
        try:
            runnable = rc._get_checker_llm()
            llm = next(s for s in (getattr(runnable, "first", None), runnable)
                       if isinstance(getattr(s, "bound", s), ChatOpenAI))
            llm = getattr(llm, "bound", llm)
            assert llm.model_name == "report-model-x"
        finally:
            rc._checker_llm = None
