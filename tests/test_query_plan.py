"""Tests for the combined follow-up planner (rag.query_processor.plan_retrieval).

One LLM call resolves a follow-up into a standalone retrieval query AND the
filters extracted from it — replacing the sequential rewrite-then-extract pair.
"""
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from rag.query_processor import QueryPlan, plan_retrieval

_HISTORY = [
    HumanMessage(content="Sudan'daki insani durum nedir?"),
    AIMessage(content="Sudan'da durum ağır..."),
]


def _planner(plan: QueryPlan):
    m = MagicMock()
    m.invoke.return_value = plan
    return m


def test_no_history_delegates_to_extract_filters():
    """First turns skip the combined call: the message is already standalone."""
    with patch("rag.query_processor.extract_filters", return_value={"country": "Mali"}) as ef:
        query, filters = plan_retrieval("Mali'de durum?", [])
    assert query == "Mali'de durum?"
    assert filters == {"country": "Mali"}
    ef.assert_called_once_with("Mali'de durum?")


def test_combined_call_returns_rewrite_and_normalized_filters():
    plan = QueryPlan(standalone_query="Sudan'ın kuzeyinde insani durum", country="sudan")
    query, filters = plan_retrieval("ya kuzeyde?", _HISTORY, planner=_planner(plan))
    assert query == "Sudan'ın kuzeyinde insani durum"
    assert filters["country"] == "Sudan"   # _COUNTRY_MAP normalization applied


def test_rule_based_backstop_fills_llm_gaps():
    """The LLM left country empty but the rewritten query names one → the
    rule-based extractor (running on the REWRITTEN query) backstops it."""
    plan = QueryPlan(standalone_query="Yemen'de gıda krizi", country=None)
    query, filters = plan_retrieval("peki gıda?", _HISTORY, planner=_planner(plan))
    assert query == "Yemen'de gıda krizi"
    assert filters["country"] == "Yemen"
    assert filters["theme"] == "Food and Nutrition"


def test_empty_standalone_query_falls_back_to_message():
    plan = QueryPlan(standalone_query="   ")
    query, _ = plan_retrieval("ya kuzeyde?", _HISTORY, planner=_planner(plan))
    assert query == "ya kuzeyde?"


def test_planner_failure_falls_back_to_filters_on_original():
    """A planner error must not add more LLM calls: fall back to
    extract_filters on the ORIGINAL message."""
    broken = MagicMock()
    broken.invoke.side_effect = RuntimeError("boom")
    with patch("rag.query_processor.extract_filters", return_value={}) as ef:
        query, filters = plan_retrieval("ya kuzeyde?", _HISTORY, planner=broken)
    assert query == "ya kuzeyde?"
    assert filters == {}
    ef.assert_called_once_with("ya kuzeyde?")


def test_chat_helper_uses_combined_plan_for_follow_ups():
    """The chat route helper routes history turns through plan_retrieval and
    first turns through extract_filters."""
    from api.routes import chat as chat_mod

    with patch.object(chat_mod, "has_session", return_value=True), \
         patch.object(chat_mod, "get_session_history") as gh, \
         patch.object(chat_mod, "plan_retrieval",
                      return_value=("standalone", {"country": "Sudan"})) as pr:
        gh.return_value.messages = _HISTORY
        assert chat_mod._plan_retrieval("s1", "ya kuzeyde?") == ("standalone", {"country": "Sudan"})
        pr.assert_called_once_with("ya kuzeyde?", _HISTORY)

    with patch.object(chat_mod, "has_session", return_value=False), \
         patch.object(chat_mod, "extract_filters", return_value={}) as ef:
        assert chat_mod._plan_retrieval("s2", "Mali'de durum?") == ("Mali'de durum?", {})
        ef.assert_called_once_with("Mali'de durum?")
