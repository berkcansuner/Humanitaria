"""Several countries in one chat question ("Sudan ve Çad'daki mülteci durumu").

Eval 2026-11-17 (9 multi-country + 2 single-country questions, live extraction and
retrieval): before, the filter kept only the first country (the json_mode validator
took a list's first element; the rule-based fallback stopped at the first match) and
every top-5 document came from it: 0/9 questions had all their countries in the
context. After: 9/9 filters complete, 9/9 contexts cover every named country; the
single-country controls are unchanged."""
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
from langchain_core.documents import Document

from api.routes import chat as chat_mod
from rag.chain import describe_filters
from rag.query_processor import QueryFilters, _extract_filters_rule_based, _normalize_llm_filters
from rag.retriever import build_sql_filter


# --- extraction ------------------------------------------------------------------

def test_llm_country_list_is_kept_and_canonicalised():
    result = QueryFilters(country=["sudan", "Chad", "Sudan"])
    assert _normalize_llm_filters(result) == {"country": ["Sudan", "Chad"]}


def test_llm_single_element_list_becomes_a_string():
    assert QueryFilters(country=["Somalia"]).country == "Somalia"
    assert QueryFilters(country=[]).country is None


def test_country_list_is_capped():
    result = QueryFilters(country=["Yemen", "Sudan", "Chad", "Somalia", "Haiti"])
    assert _normalize_llm_filters(result)["country"] == ["Yemen", "Sudan", "Chad", "Somalia"]


def test_rule_based_collects_every_country():
    assert set(_extract_filters_rule_based("Yemen, Somali ve Sudan'da gıda")["country"]) == {
        "Yemen", "Somalia", "Sudan"}


def test_rule_based_south_sudan_alone_is_not_also_sudan():
    assert _extract_filters_rule_based("Güney Sudan'da kolera")["country"] == "South Sudan"
    assert set(_extract_filters_rule_based("Sudan ve Güney Sudan")["country"]) == {"Sudan", "South Sudan"}


# --- filters downstream ----------------------------------------------------------

def test_sql_filter_matches_every_country_and_its_alias():
    clauses, params = build_sql_filter({"country": ["Iran", "Iraq"]})
    assert clauses == ["country = ANY(:countries)"]
    assert params == {"countries": ["Iran", "Iran (Islamic Republic of)", "Iraq"]}


def test_unknown_country_is_dropped_from_a_list():
    with patch.object(chat_mod, "corpus_countries", return_value=frozenset({"sudan", "chad"})):
        assert chat_mod._drop_unknown_country({"country": ["Sudan", "Narnia", "Chad"]}) == {
            "country": ["Sudan", "Chad"]}
        assert chat_mod._drop_unknown_country({"country": ["Sudan", "Narnia"]}) == {"country": "Sudan"}
        assert chat_mod._drop_unknown_country({"country": ["Narnia", "Oz"], "theme": "Health"}) == {
            "theme": "Health"}


def test_country_list_is_described_and_named_in_the_no_docs_message():
    assert "country: Sudan, Chad" in describe_filters({"country": ["Sudan", "Chad"]})
    msg = chat_mod.no_docs_message({"country": ["Sudan", "Chad"]}, "en")
    assert "**Sudan**" in msg and "**Chad**" in msg


# --- retrieval -------------------------------------------------------------------

def _docs(country, n):
    return [Document(page_content=f"{country}{i}", metadata={"doc_id": f"{country}{i}", "date": "2026-11-01"})
            for i in range(n)]


def _run(filters, per_country, boost=False):
    def retriever_for(filter, k, lambda_mult):
        r = MagicMock()
        r.ainvoke = AsyncMock(return_value=per_country[filter["country"]])
        return r

    with patch.object(chat_mod, "build_retriever", side_effect=retriever_for) as build, \
         patch.object(chat_mod, "apply_date_filter", side_effect=lambda docs, df: docs), \
         patch.object(chat_mod, "rerank_by_relevance", side_effect=lambda q, docs, n: docs[:n]) as rel, \
         patch.object(chat_mod, "rerank_by_recency", side_effect=lambda docs, decay_factor=None: docs), \
         patch.object(chat_mod, "should_boost_recency", return_value=boost):
        out = anyio.run(chat_mod._retrieve_docs, "refugees", filters)
    return out, build, rel


def test_each_country_is_searched_separately_and_takes_turns_in_the_result():
    per_country = {"Sudan": _docs("S", 10), "Chad": _docs("C", 10)}
    out, build, rel = _run({"country": ["Sudan", "Chad"], "theme": "Health"}, per_country)
    searched = [call.kwargs["filter"] for call in build.call_args_list]
    assert sorted(f["country"] for f in searched) == ["Chad", "Sudan"]
    assert all(f["theme"] == "Health" for f in searched)
    assert rel.call_count == 1                      # the union is reranked once
    assert [d.page_content for d in out] == ["S0", "C0", "S1", "C1", "S2", "C2"]


def test_a_country_with_few_documents_leaves_its_slots_to_the_others():
    per_country = {"Sudan": _docs("S", 10), "Chad": _docs("C", 1)}
    out, _, _ = _run({"country": ["Sudan", "Chad"]}, per_country)
    assert [d.page_content for d in out] == ["S0", "C0", "S1", "S2", "S3", "S4"]


def test_single_country_keeps_the_original_pipeline():
    per_country = {"Sudan": _docs("S", 10)}
    out, build, _ = _run({"country": "Sudan"}, per_country)
    assert build.call_count == 1 and len(out) == 5
