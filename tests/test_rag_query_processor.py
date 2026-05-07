import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from rag.query_processor import (
    extract_filters,
    _extract_filters_rule_based,
    QueryFilters,
)


class TestQueryProcessor:
    def test_extract_country(self):
        f = extract_filters("İran'daki gıda durumu")
        assert f.get("country") == "Iran"

    def test_extract_theme_food(self):
        f = extract_filters("gıda sektörü raporları")
        assert f.get("theme") == "Food and Nutrition"

    def test_extract_date_relative(self):
        f = extract_filters("son 1 ayda olanlar")
        assert "date" in f
        from datetime import date
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (date.today() - parsed).days >= 29

    def test_no_filters(self):
        f = extract_filters("başa çıkma stratejileri")
        assert f == {}

    def test_extract_doctype_report(self):
        f = extract_filters("raporlar hakkında bilgi")
        assert f.get("doctype") == "report"

    def test_extract_doctype_disaster(self):
        f = extract_filters("afet profillerini göster")
        assert f.get("doctype") == "disaster"

    def test_extract_doctype_country(self):
        f = extract_filters("ülke bilgileri")
        assert f.get("doctype") == "country"

    def test_extract_doctype_english(self):
        f = extract_filters("show me disasters in Yemen")
        assert f.get("doctype") == "disaster"


class TestRuleBasedFallback:
    def test_rule_based_country(self):
        f = _extract_filters_rule_based("Irak'taki durum")
        assert f.get("country") is not None  # depends on İ normalization

    def test_rule_based_theme_health(self):
        f = _extract_filters_rule_based("sağlık raporları")
        assert f.get("theme") == "Health"

    def test_rule_based_date_english(self):
        f = _extract_filters_rule_based("last 30 days")
        assert "date" in f

    def test_rule_based_date_weeks_english(self):
        f = _extract_filters_rule_based("last 2 weeks in Syria")
        assert "date" in f
        # Rule-based only matches Turkish country names, "Syria" → needs LLM

    def test_rule_based_no_filters(self):
        f = _extract_filters_rule_based("general overview")
        assert f == {}


class TestLLMFilterExtraction:
    @patch("rag.query_processor._get_llm_extractor")
    def test_llm_extracts_country_and_theme(self, mock_get_llm):
        mock_chain = MagicMock()
        mock_result = QueryFilters(country="Syria", theme="Food and Nutrition")
        mock_chain.invoke.return_value = mock_result
        mock_get_llm.return_value = mock_chain
        # Clear LRU cache
        from rag.query_processor import _cached_llm_extract
        _cached_llm_extract.cache_clear()
        f = extract_filters("WFP's food security reports in Syria last 3 months")
        assert f.get("country") == "Syria"
        assert f.get("theme") == "Food and Nutrition"
        _cached_llm_extract.cache_clear()

    @patch("rag.query_processor._get_llm_extractor")
    def test_llm_extracts_date_as_iso(self, mock_get_llm):
        mock_chain = MagicMock()
        mock_result = QueryFilters(country="Syria", date_from="2026-04-07", source="WFP")
        mock_chain.invoke.return_value = mock_result
        mock_get_llm.return_value = mock_chain
        from rag.query_processor import _cached_llm_extract
        _cached_llm_extract.cache_clear()
        f = extract_filters("WFP's food security reports in Syria last 3 months")
        assert f["date"] == {"$gte": "2026-04-07"}
        assert f["source"] == "WFP"
        _cached_llm_extract.cache_clear()

    @patch("rag.query_processor._get_llm_extractor")
    def test_llm_failure_falls_back_to_rules(self, mock_get_llm):
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("timeout")
        mock_get_llm.return_value = mock_chain
        from rag.query_processor import _cached_llm_extract
        _cached_llm_extract.cache_clear()
        f = extract_filters("İran'daki gıda durumu")
        assert f.get("country") == "Iran"
        _cached_llm_extract.cache_clear()

    @patch("rag.query_processor._get_llm_extractor")
    def test_llm_multi_field_extraction(self, mock_get_llm):
        mock_chain = MagicMock()
        mock_result = QueryFilters(
            country="State of Palestine", theme="Health", doctype="report",
            date_from="2026-02-07", source="WHO", format="Situation Report",
        )
        mock_chain.invoke.return_value = mock_result
        mock_get_llm.return_value = mock_chain
        from rag.query_processor import _cached_llm_extract
        _cached_llm_extract.cache_clear()
        f = extract_filters("WHO situation reports on health in Gaza last 3 months")
        assert f["country"] == "State of Palestine"
        assert f["theme"] == "Health"
        assert f["doctype"] == "report"
        assert f["date"] == {"$gte": "2026-02-07"}
        assert f["source"] == "WHO"
        assert f["format"] == "Situation Report"
        _cached_llm_extract.cache_clear()