"""Tests for conversational query rewriting (rag/query_rewriter.py)."""
from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage, AIMessage

from rag.query_rewriter import rewrite_query


def _llm_returning(text):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=text)
    return llm


def test_no_history_returns_original_without_calling_llm():
    llm = MagicMock()
    assert rewrite_query("ya kuzeyde?", [], llm=llm) == "ya kuzeyde?"
    llm.invoke.assert_not_called()


def test_with_history_returns_rewritten_query():
    history = [HumanMessage(content="Sudan'da durum nedir?"), AIMessage(content="...")]
    llm = _llm_returning("Sudan'ın kuzeyindeki insani durum nedir?")
    out = rewrite_query("ya kuzeyde?", history, llm=llm)
    assert out == "Sudan'ın kuzeyindeki insani durum nedir?"
    llm.invoke.assert_called_once()


def test_strips_whitespace_from_llm_output():
    history = [HumanMessage(content="x"), AIMessage(content="y")]
    llm = _llm_returning("  standalone query  \n")
    assert rewrite_query("follow up", history, llm=llm) == "standalone query"


def test_llm_error_falls_back_to_original():
    history = [HumanMessage(content="x"), AIMessage(content="y")]
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("timeout")
    assert rewrite_query("ya kuzeyde?", history, llm=llm) == "ya kuzeyde?"


def test_empty_llm_output_falls_back_to_original():
    history = [HumanMessage(content="x"), AIMessage(content="y")]
    llm = _llm_returning("   ")
    assert rewrite_query("orig question", history, llm=llm) == "orig question"
