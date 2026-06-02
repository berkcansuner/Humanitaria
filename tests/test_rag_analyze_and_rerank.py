import pytest
from unittest.mock import patch
from datetime import datetime
from rag.query_processor import extract_filters, analyze_query, _extract_filters_rule_based
from rag.retriever import rerank_by_recency
from langchain_core.documents import Document


def _clear_llm_cache():
    from rag.query_processor import _llm_cache
    _llm_cache.clear()


class TestAnalyzeQuery:
    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_vague_query_detected(self, _mock):
        _clear_llm_cache()
        result = analyze_query("insani yardim durumu")
        assert result["is_vague"] is True
        assert result["has_country"] is False
        assert result["has_date"] is False
        assert result["has_theme"] is False
        assert result["message"] != ""

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_query_with_country(self, _mock):
        _clear_llm_cache()
        result = analyze_query("Iran'daki gelismeler")
        assert result["is_vague"] is False
        assert result["has_country"] is True
        assert result["has_date"] is False

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_query_with_date(self, _mock):
        _clear_llm_cache()
        result = analyze_query("son 1 ay raporlari")
        assert result["is_vague"] is False
        assert result["has_date"] is True

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_specific_query_not_vague(self, _mock):
        _clear_llm_cache()
        result = analyze_query("Iran'da son 1 aydaki gıda durumu")
        assert result["is_vague"] is False
        assert result["has_country"] is True
        assert result["has_date"] is True
        assert result["has_theme"] is True

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_suggestions_provided_for_missing_dims(self, _mock):
        _clear_llm_cache()
        result = analyze_query("insani yardim")
        assert len(result["suggestions"]["countries"]) > 0
        assert len(result["suggestions"]["time_periods"]) > 0
        assert len(result["suggestions"]["themes"]) > 0

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_no_country_suggestions_when_country_present(self, _mock):
        _clear_llm_cache()
        result = analyze_query("Yemen'deki durum")
        assert result["has_country"] is True
        assert len(result["suggestions"]["countries"]) == 0


class TestRerankByRecency:
    def test_rerank_empty_list(self):
        assert rerank_by_recency([]) == []

    def test_rerank_preserves_all_docs(self):
        docs = [
            Document(page_content="a", metadata={"date": "2023-01-01", "title": "A"}),
            Document(page_content="b", metadata={"date": "2026-01-01", "title": "B"}),
            Document(page_content="c", metadata={"date": "2024-06-15", "title": "C"}),
        ]
        result = rerank_by_recency(docs)
        assert len(result) == 3

    def test_rerank_prioritizes_recent(self):
        docs = [
            Document(page_content="old", metadata={"date": "2022-01-01", "title": "Old"}),
            Document(page_content="recent", metadata={"date": "2026-04-01", "title": "Recent"}),
        ]
        result = rerank_by_recency(docs, decay_factor=0.5)
        # Recent doc should come first with high decay factor
        assert result[0].metadata["title"] == "Recent"

    def test_rerank_no_date_docs_get_low_score(self):
        docs = [
            Document(page_content="no-date", metadata={"date": "", "title": "NoDate"}),
            Document(page_content="recent", metadata={"date": datetime.now().strftime("%Y-%m-%d"), "title": "Recent"}),
            Document(page_content="old", metadata={"date": "2020-01-01", "title": "Old"}),
        ]
        result = rerank_by_recency(docs, decay_factor=0.5)
        # Recent doc should come first, no-date doc should be ranked lower
        assert result[0].metadata["title"] == "Recent"

    def test_rerank_disabled_by_config(self):
        docs = [
            Document(page_content="old", metadata={"date": "2022-01-01", "title": "Old"}),
            Document(page_content="recent", metadata={"date": "2026-01-01", "title": "Recent"}),
        ]
        with patch("rag.retriever.get_settings") as mock_settings:
            from config import Settings
            mock_settings.return_value = Settings(
                RERANK_BY_DATE=False,
            )
            result = rerank_by_recency(docs)
            # When disabled, order should be preserved
            assert result[0].metadata["title"] == "Old"
            assert result[1].metadata["title"] == "Recent"

    def test_rerank_all_same_date(self):
        docs = [
            Document(page_content="a", metadata={"date": "2026-01-01", "title": "A"}),
            Document(page_content="b", metadata={"date": "2026-01-01", "title": "B"}),
        ]
        result = rerank_by_recency(docs)
        assert len(result) == 2
        # Same dates, original order preserved (MMR rank dominates)
        assert result[0].metadata["title"] == "A"


class TestRerankByRecencyWithScores:
    """When docs carry a Pinecone _relevance_score, the blend uses the raw score
    (not the steep 1/(1+i) position decay), so recency can matter among
    comparably-relevant docs."""

    def _doc(self, title, score, days_ago):
        from datetime import timedelta
        now = datetime.now()
        return Document(page_content=title, metadata={
            "title": title,
            "_relevance_score": score,
            "date": (now - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
        })

    def test_raw_score_lets_recent_doc_at_depth_win(self):
        # Mirrors the real Ukraine case: a moderately-recent doc (97d) ranked
        # LOWER by relevance outranks an older (260d) top-relevance doc once the
        # compressed raw scores replace the steep position decay. The old
        # position-based blend kept the position-0 doc first.
        docs = [
            self._doc("A", 0.25, 260),    # pos 0, older, top relevance
            self._doc("F1", 0.22, 1000),
            self._doc("F2", 0.20, 1000),
            self._doc("D", 0.15, 97),     # pos 3, recent, lower relevance
        ]
        out = rerank_by_recency(docs, decay_factor=0.6)
        assert out[0].metadata["title"] == "D"

    def test_relevance_score_breaks_tie_for_same_date(self):
        # Same date → recency equal → the higher raw relevance score wins.
        # (Position-based would have kept the first-listed doc on top.)
        docs = [
            self._doc("low", 0.10, 10),
            self._doc("high", 0.95, 10),
        ]
        out = rerank_by_recency(docs, decay_factor=0.6)
        assert out[0].metadata["title"] == "high"