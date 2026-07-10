"""Unit tests for rag.report_service pure helpers: title dedup + language filtering."""
from unittest.mock import patch

from langchain_core.documents import Document

from rag.report_service import (
    _norm_title,
    _is_prefix_title_dup,
    _prefer_english,
    _collapse_near_duplicates,
    _build_filters,
)


def _doc(body="text", **md):
    return Document(page_content=body, metadata=md)


class TestNormTitle:
    def test_lowercases_and_collapses_nonalnum(self):
        assert _norm_title("WFP: Sudan Report (2026)!") == "wfp sudan report 2026"

    def test_empty(self):
        assert _norm_title("") == ""


class TestIsPrefixTitleDup:
    def test_equal_titles(self):
        assert _is_prefix_title_dup("Sudan Food Security", "sudan food security") is True

    def test_companion_prefix_over_min_length(self):
        base = "Sudan Food Security Situation Report May"
        companion = base + " : Insights and recommendations"
        assert _is_prefix_title_dup(base, companion) is True

    def test_short_shared_prefix_not_dup(self):
        # Below the 25-char prefix guard → not treated as a companion.
        assert _is_prefix_title_dup("Sudan brief", "Sudan brief extended edition") is False

    def test_monthly_series_not_dup(self):
        # Same series, different month — neither is a prefix of the other.
        a = "Market Monitoring ICSM Mars 2026 bulletin"
        b = "Market Monitoring ICSM Avril 2026 bulletin"
        assert _is_prefix_title_dup(a, b) is False


class TestPreferEnglish:
    def test_filters_to_english_when_dominant(self):
        docs = [_doc(body=f"d{i}") for i in range(5)]
        langs = {"d0": "en", "d1": "en", "d2": "en", "d3": "en", "d4": "fr"}
        with patch("rag.report_service._detect_lang", side_effect=lambda t: langs[t]):
            out = _prefer_english(docs)
        assert len(out) == 4  # the 4 English docs (0.8 >= 0.6 dominance)
        assert all(d.page_content != "d4" for d in out)

    def test_keeps_all_when_francophone_majority(self):
        docs = [_doc(body=f"d{i}") for i in range(5)]
        langs = {"d0": "en", "d1": "en", "d2": "fr", "d3": "fr", "d4": "fr"}
        with patch("rag.report_service._detect_lang", side_effect=lambda t: langs[t]):
            out = _prefer_english(docs)
        assert len(out) == 5  # 0.4 English < 0.6 → keep the French-majority set

    def test_empty(self):
        assert _prefer_english([]) == []


class TestCollapseNearDuplicates:
    def test_collapses_translation_pair_prefers_english(self):
        # Same source + same date, different language → one representative (English).
        docs = [
            _doc(body="fr", source="WFP", date="2026-05-01", title="Communiqué"),
            _doc(body="en", source="WFP", date="2026-05-01", title="Press release"),
        ]
        with patch("rag.report_service._detect_lang", side_effect=lambda t: {"fr": "fr", "en": "en"}[t]):
            out = _collapse_near_duplicates(docs)
        assert len(out) == 1
        assert out[0].page_content == "en"

    def test_collapses_companion_prefix(self):
        base = "Sudan Food Security Situation Report May"
        docs = [
            _doc(body="a", source="OCHA", date="2026-05-01", title=base),
            _doc(body="b", source="OCHA", date="2026-05-02", title=base + " : Insights"),
        ]
        with patch("rag.report_service._detect_lang", return_value="en"):
            out = _collapse_near_duplicates(docs)
        assert len(out) == 1

    def test_distinct_same_source_reports_survive(self):
        docs = [
            _doc(body="a", source="FEWS", date="2026-03-01", title="Market Monitoring Mars 2026"),
            _doc(body="b", source="FEWS", date="2026-04-01", title="Market Monitoring Avril 2026"),
        ]
        with patch("rag.report_service._detect_lang", return_value="en"):
            out = _collapse_near_duplicates(docs)
        assert len(out) == 2

    def test_different_sources_never_collapse(self):
        docs = [
            _doc(body="a", source="WFP", date="2026-05-01", title="Same Title"),
            _doc(body="b", source="OCHA", date="2026-05-01", title="Same Title"),
        ]
        with patch("rag.report_service._detect_lang", return_value="en"):
            out = _collapse_near_duplicates(docs)
        assert len(out) == 2


class TestLangDetectedOncePerDoc:
    def test_language_cached_across_both_filters(self):
        # _prefer_english then _collapse_near_duplicates must detect each doc's
        # language ONCE total (cached on metadata), not once per function.
        docs = [_doc(body=f"d{i}", source="WFP", date=f"2026-05-0{i}", title=f"T{i}") for i in range(1, 4)]
        with patch("rag.report_service._detect_lang", return_value="en") as detect:
            kept = _prefer_english(docs)
            _collapse_near_duplicates(kept)
        assert detect.call_count == 3  # once per original doc, not 6


class TestBuildFilters:
    def test_scopes_to_report_doctype(self):
        filters = _build_filters("Sudan", None, None, None)
        assert filters == {"country": "Sudan", "doctype": "report"}

    def test_theme_and_date_still_included(self):
        filters = _build_filters("Sudan", "Health", "2026-01-01", "2026-06-30")
        assert filters == {
            "country": "Sudan",
            "doctype": "report",
            "theme": "Health",
            "date": {"$gte": "2026-01-01", "$lte": "2026-06-30"},
        }
