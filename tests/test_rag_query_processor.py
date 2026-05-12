import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from rag.query_processor import (
    extract_filters,
    _extract_filters_rule_based,
    _llm_cache,
    QueryFilters,
)


def _clear_llm_cache():
    _llm_cache.clear()


class TestQueryProcessor:
    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_country(self, _mock):
        f = extract_filters("İran'daki gıda durumu")
        assert f.get("country") == "Iran"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_theme_food(self, _mock):
        f = extract_filters("gıda sektörü raporları")
        assert f.get("theme") == "Food and Nutrition"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_date_relative(self, _mock):
        f = extract_filters("son 1 ayda olanlar")
        assert "date" in f
        from datetime import date
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (date.today() - parsed).days >= 29

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_no_filters(self, _mock):
        f = extract_filters("başa çıkma stratejileri")
        assert f == {}

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_doctype_report(self, _mock):
        f = extract_filters("raporlar hakkında bilgi")
        assert f.get("doctype") == "report"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_doctype_disaster(self, _mock):
        f = extract_filters("afet profillerini göster")
        assert f.get("doctype") == "disaster"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_doctype_country(self, _mock):
        f = extract_filters("ülke bilgileri")
        assert f.get("doctype") == "country"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_extract_doctype_english(self, _mock):
        f = extract_filters("show me disasters in Yemen")
        assert f.get("doctype") == "disaster"


class TestRuleBasedFallback:
    def test_rule_based_country(self):
        f = _extract_filters_rule_based("Irak'taki durum")
        assert f.get("country") is not None

    def test_rule_based_theme_health(self):
        f = _extract_filters_rule_based("sağlık raporları")
        assert f.get("theme") == "Health"

    def test_rule_based_date_english(self):
        f = _extract_filters_rule_based("last 30 days")
        assert "date" in f

    def test_rule_based_date_weeks_english(self):
        f = _extract_filters_rule_based("last 2 weeks in Syria")
        assert "date" in f

    def test_rule_based_no_filters(self):
        f = _extract_filters_rule_based("general overview")
        assert f == {}


class TestRuleBasedDatePatterns:
    def test_last_week_no_number_english(self):
        f = _extract_filters_rule_based("last week in Iran")
        assert "date" in f
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (datetime.now().date() - parsed).days >= 6

    def test_son_hafta_turkish(self):
        f = _extract_filters_rule_based("son hafta İran'daki gelişmeler")
        assert "date" in f
        assert f.get("country") == "Iran"

    def test_gecen_hafta_turkish(self):
        f = _extract_filters_rule_based("gecen hafta raporları")
        assert "date" in f

    def test_last_month_no_number_english(self):
        f = _extract_filters_rule_based("last month updates")
        assert "date" in f
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (datetime.now().date() - parsed).days >= 28

    def test_son_ay_turkish(self):
        f = _extract_filters_rule_based("son ay Suriye")
        assert "date" in f

    def test_since_iso_date(self):
        f = _extract_filters_rule_based("since 2026-02-28 humanitarian situation")
        assert f["date"] == {"$gte": "2026-02-28"}

    def test_since_us_date(self):
        f = _extract_filters_rule_based("since 2/28/2026 in Iran")
        assert "date" in f
        assert f["date"]["$gte"] == "2026-02-28"

    def test_yesterday_english(self):
        f = _extract_filters_rule_based("yesterday reports")
        assert "date" in f
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (datetime.now().date() - parsed).days == 1

    def test_dun_turkish(self):
        f = _extract_filters_rule_based("dun olan gelişmeler")
        assert "date" in f

    def test_today_english(self):
        f = _extract_filters_rule_based("today updates from Yemen")
        assert "date" in f

    def test_bugun_turkish(self):
        f = _extract_filters_rule_based("bugun raporları")
        assert "date" in f

    def test_this_week_english(self):
        f = _extract_filters_rule_based("this week reports")
        assert "date" in f

    def test_bu_hafta_turkish(self):
        f = _extract_filters_rule_based("bu hafta Iran")
        assert "date" in f

    def test_this_month_english(self):
        f = _extract_filters_rule_based("this month situation reports")
        assert "date" in f

    def test_bu_ay_turkish(self):
        f = _extract_filters_rule_based("bu ay Yemen")
        assert "date" in f

    def test_recent_english(self):
        f = _extract_filters_rule_based("recent developments in Syria")
        assert "date" in f
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (datetime.now().date() - parsed).days >= 28

    def test_guncel_turkish(self):
        f = _extract_filters_rule_based("guncel durum")
        assert "date" in f


class TestLLMFilterExtraction:
    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_extracts_country_and_theme(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Syria", "theme": "Food and Nutrition"}
        f = extract_filters("WFP's food security reports in Syria last 3 months")
        assert f.get("country") == "Syria"
        assert f.get("theme") == "Food and Nutrition"

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_extracts_date_as_iso(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Syria", "date": {"$gte": "2026-04-07"}, "source": "WFP"}
        f = extract_filters("WFP's food security reports in Syria last 3 months")
        assert f["date"] == {"$gte": "2026-04-07"}
        assert f["source"] == "WFP"

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_failure_falls_back_to_rules(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = None
        f = extract_filters("İran'daki gıda durumu")
        assert f.get("country") == "Iran"

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_failure_not_cached(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = None
        f1 = extract_filters("İran'daki gıda durumu")
        assert mock_llm.call_count == 1
        # Second call should still try LLM (not cached as None)
        f2 = extract_filters("İran'daki gıda durumu")
        assert mock_llm.call_count == 2

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_success_is_cached(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Syria", "theme": "Health"}
        f1 = extract_filters("health situation in Syria")
        assert mock_llm.call_count == 1
        # Second call should use cache
        f2 = extract_filters("health situation in Syria")
        assert mock_llm.call_count == 1
        assert f1 == f2

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_multi_field_extraction(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {
            "country": "State of Palestine", "theme": "Health", "doctype": "report",
            "date": {"$gte": "2026-02-07"}, "source": "WHO", "format": "Situation Report",
        }
        f = extract_filters("WHO situation reports on health in Gaza last 3 months")
        assert f["country"] == "State of Palestine"
        assert f["theme"] == "Health"
        assert f["doctype"] == "report"
        assert f["date"] == {"$gte": "2026-02-07"}
        assert f["source"] == "WHO"
        assert f["format"] == "Situation Report"