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


class TestLlmCacheEviction:
    def test_cache_is_lru_not_fifo(self):
        # Accessing an old entry must protect it from eviction (LRU), unlike the
        # previous FIFO behaviour which always dropped the oldest-inserted key.
        from rag.query_processor import _cached_llm_extract
        _clear_llm_cache()
        with patch("rag.query_processor._MAX_LLM_CACHE", 2), \
             patch("rag.query_processor._extract_filters_llm", side_effect=lambda q: {"q": q}):
            _cached_llm_extract("k1")
            _cached_llm_extract("k2")
            _cached_llm_extract("k1")   # hit → k1 becomes most-recently-used
            _cached_llm_extract("k3")   # inserting k3 evicts the LRU entry (k2)
        assert "k1" in _llm_cache
        assert "k2" not in _llm_cache
        assert "k3" in _llm_cache
        _clear_llm_cache()

    def test_cache_hit_skips_llm_call(self):
        from rag.query_processor import _cached_llm_extract
        _clear_llm_cache()
        with patch("rag.query_processor._extract_filters_llm", side_effect=lambda q: {"q": q}) as ex:
            _cached_llm_extract("same")
            _cached_llm_extract("same")
        assert ex.call_count == 1
        _clear_llm_cache()


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
        # relativedelta(months=1): minimum 28 days (February), maximum 31 days
        assert (date.today() - parsed).days >= 27

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


class TestWordBoundaryMatching:
    """Tests for the substring-matching bug fix (issue: 'su' matched 'Sudan' etc.)."""

    def test_su_does_not_match_sudan(self):
        # Old code: "su" in "sudan" → True (bug). New: word boundary → no match.
        f = _extract_filters_rule_based("Sudan'da gıda durumu")
        assert f.get("theme") != "Water Sanitation Hygiene", (
            "'su' in Sudan should NOT trigger Water theme — word boundary fix"
        )
        assert f.get("country") == "Sudan"
        assert f.get("theme") == "Food and Nutrition"

    def test_su_matches_as_whole_word(self):
        f = _extract_filters_rule_based("su sektörü raporları")
        assert f.get("theme") == "Water Sanitation Hygiene"

    def test_su_matches_wash(self):
        f = _extract_filters_rule_based("wash programları")
        assert f.get("theme") == "Water Sanitation Hygiene"

    def test_irak_does_not_match_characteristic(self):
        # "irak" should not match inside longer words
        f = _extract_filters_rule_based("characteristic analysis")
        assert f.get("country") is None

    def test_somali_matches_somaliland(self):
        # "somali" (6 chars) uses prefix matching so "somaliland" triggers Somalia.
        # Somaliland is a territory within Somalia's humanitarian context — match is acceptable.
        f = _extract_filters_rule_based("somaliland bölgesi")
        assert f.get("country") == "Somalia"


class TestRuleBasedFallback:
    def test_rule_based_country(self):
        f = _extract_filters_rule_based("Irak'taki durum")
        assert f.get("country") is not None

    def test_rule_based_theme_health(self):
        f = _extract_filters_rule_based("sağlık raporları")
        assert f.get("theme") == "Health"

    def test_rule_based_theme_protection(self):
        # Canonical ReliefWeb taxonomy name is "Protection and Human Rights",
        # not "Protection" — theme filter is $eq so the name must match exactly.
        f = _extract_filters_rule_based("koruma faaliyetleri")
        assert f.get("theme") == "Protection and Human Rights"

    def test_rule_based_theme_shelter(self):
        # Canonical name is "Shelter and Non-Food Items", not "Shelter and NFI".
        f = _extract_filters_rule_based("barınma yardımı")
        assert f.get("theme") == "Shelter and Non-Food Items"

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
        # relativedelta(months=1): minimum 28 days (February)
        assert (datetime.now().date() - parsed).days >= 27

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
        # relativedelta(months=1): minimum 28 days (February)
        assert (datetime.now().date() - parsed).days >= 27

    def test_guncel_turkish(self):
        f = _extract_filters_rule_based("guncel durum")
        assert "date" in f


class TestQueryFiltersCoercion:
    def test_list_values_coerced_to_string(self):
        # Gemini json_mode may return single-element lists; they must coerce.
        f = QueryFilters(country=["Somalia"], theme=["Education"])
        assert f.country == "Somalia"
        assert f.theme == "Education"

    def test_empty_list_coerced_to_none(self):
        f = QueryFilters(country=[])
        assert f.country is None

    def test_plain_string_unchanged(self):
        f = QueryFilters(country="Sudan")
        assert f.country == "Sudan"


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


class TestVagueTemporalWords:
    """Tests that vague temporal qualifiers ('şu anda', 'en güncel', etc.) do not
    trigger a date filter.  Root cause: LLM was mapping these to date_from=today."""

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_su_anda_no_date_filter(self, _mock):
        _llm_cache.clear()
        f = extract_filters("şu anda iran ile ilgili en güncel insani yardım bilgileri nelerdir")
        assert "date" not in f
        assert f.get("country") == "Iran"

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_en_guncel_no_date_filter(self, _mock):
        _llm_cache.clear()
        f = extract_filters("en güncel Yemen raporları")
        assert "date" not in f

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_mevcut_no_date_filter(self, _mock):
        _llm_cache.clear()
        f = extract_filters("mevcut insani yardım durumu Sudan")
        assert "date" not in f

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_currently_no_date_filter(self, _mock):
        _llm_cache.clear()
        f = extract_filters("currently what is the humanitarian situation in Yemen")
        assert "date" not in f


class TestNormalizeLlmFilters:
    """Tests for _normalize_llm_filters safety checks."""

    def test_rejects_date_from_today(self):
        from rag.query_processor import _normalize_llm_filters
        today = datetime.now().strftime("%Y-%m-%d")
        result = QueryFilters(country="Iran", date_from=today)
        f = _normalize_llm_filters(result)
        assert "date" not in f, "date_from = today should be rejected (no docs are created today)"

    def test_rejects_date_from_future(self):
        from rag.query_processor import _normalize_llm_filters
        future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = QueryFilters(country="Iran", date_from=future)
        f = _normalize_llm_filters(result)
        assert "date" not in f, "date_from in the future should be rejected"

    def test_accepts_date_from_past(self):
        from rag.query_processor import _normalize_llm_filters
        past = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        result = QueryFilters(country="Iran", date_from=past)
        f = _normalize_llm_filters(result)
        assert "date" in f, "date_from in the past should be accepted"
        assert f["date"]["$gte"] == past

    def test_country_misclassified_as_source_becomes_country(self):
        # Small LLM (qwen2.5:0.5b) sometimes dumps a country name into `source`.
        # A source that is actually a known country must be reclassified, not used
        # as a source filter (which would return zero documents).
        from rag.query_processor import _normalize_llm_filters
        result = QueryFilters(source="Sudan")
        f = _normalize_llm_filters(result)
        assert f.get("country") == "Sudan"
        assert "source" not in f, "a known country must not survive as a source filter"

    def test_source_acronym_becomes_the_stored_name(self):
        # chunks.source holds ReliefWeb's full name; an equality filter on the
        # acronym the model extracts ("WFP") matched no document at all.
        from rag.query_processor import _normalize_llm_filters
        f = _normalize_llm_filters(QueryFilters(source="WFP"))
        assert f.get("source") == "World Food Programme"
        assert "country" not in f

    @pytest.mark.parametrize("given, stored", [
        ("OCHA", "UN Office for the Coordination of Humanitarian Affairs"),
        ("unhcr", "UN High Commissioner for Refugees"),
        ("FEWS NET", "Famine Early Warning System Network"),
        ("world food programme", "World Food Programme"),
        ("MSF", "Médecins Sans Frontières"),
    ])
    def test_known_sources_take_the_stored_name(self, given, stored):
        from rag.query_processor import _normalize_llm_filters
        assert _normalize_llm_filters(QueryFilters(source=given)).get("source") == stored

    @pytest.mark.parametrize("given", ["IPC", "ipc", "Integrated Food Security Phase Classification",
                                       "Cadre Harmonisé"])
    def test_classification_system_is_not_a_source(self, given):
        # "IPC figures" are quoted by WFP, FAO, OCHA and others; the IPC itself
        # publishes few documents, so a source filter would hide most of them.
        from rag.query_processor import _normalize_llm_filters
        f = _normalize_llm_filters(QueryFilters(country="Sudan", source=given))
        assert "source" not in f
        assert f.get("country") == "Sudan"

    def test_unknown_source_is_kept_as_given(self):
        from rag.query_processor import _normalize_llm_filters
        assert _normalize_llm_filters(QueryFilters(source="Acme Relief")).get("source") == "Acme Relief"

    def test_country_as_source_does_not_override_existing_country(self):
        from rag.query_processor import _normalize_llm_filters
        result = QueryFilters(country="Yemen", source="Sudan")
        f = _normalize_llm_filters(result)
        assert f.get("country") == "Yemen", "explicit country must not be overwritten"
        assert "source" not in f


class TestRuleBasedMergeBackstop:
    """When the unreliable LLM returns an empty/partial result, the deterministic
    rule-based extractor must still fill in the curated country/theme/doctype/date
    fields instead of being bypassed."""

    @patch("rag.query_processor._extract_filters_llm")
    def test_empty_llm_falls_back_to_rules(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {}  # LLM succeeded but extracted nothing
        f = extract_filters("Sudan reports")
        assert f.get("country") == "Sudan"
        assert f.get("doctype") == "report"

    @patch("rag.query_processor._extract_filters_llm")
    def test_empty_llm_fills_country_theme_date(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {}
        f = extract_filters("Yemen food crisis last 3 months")
        assert f.get("country") == "Yemen"
        assert f.get("theme") == "Food and Nutrition"
        assert "date" in f

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_values_win_over_rules_on_conflict(self, mock_llm):
        _clear_llm_cache()
        # LLM's explicit ISO date must take precedence over rule-based "last 3 months"
        mock_llm.return_value = {"country": "Syria", "date": {"$gte": "2026-04-07"}}
        f = extract_filters("food reports in Syria last 3 months")
        assert f["date"] == {"$gte": "2026-04-07"}
        assert f.get("country") == "Syria"

    @patch("rag.query_processor._extract_filters_llm")
    def test_partial_llm_keeps_its_fields_and_gains_rule_fields(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"source": "WFP"}
        f = extract_filters("WFP reports about Sudan")
        assert f.get("source") == "WFP"
        assert f.get("country") == "Sudan"
        assert f.get("doctype") == "report"


class TestShouldBoostRecency:
    def test_boost_on_for_current_english(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency(
            "What is the current humanitarian situation in Sudan?", {"country": "Sudan"}
        ) is True

    def test_boost_on_for_neutral_query(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency("Sudan humanitarian situation", {"country": "Sudan"}) is True

    def test_boost_on_for_latest(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency("latest situation in Ukraine", {"country": "Ukraine"}) is True

    def test_boost_on_for_empty_filters(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency("genel insani durum", {}) is True

    def test_boost_off_when_date_filter_present(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency(
            "Sudan reports last 3 months", {"country": "Sudan", "date": {"$gte": "2026-03-01"}}
        ) is False

    def test_boost_off_historical_evolve_english(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency(
            "how did the situation in Sudan evolve over 2024", {"country": "Sudan"}
        ) is False

    def test_boost_off_trend_english(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency(
            "humanitarian funding trend in Yemen", {"country": "Yemen"}
        ) is False

    def test_boost_off_historical_turkish_gelisti(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency(
            "Sudan'da durum yıllar içinde nasıl gelişti", {"country": "Sudan"}
        ) is False

    def test_boost_off_historical_turkish_tarihce(self):
        from rag.query_processor import should_boost_recency
        assert should_boost_recency("Yemen krizinin tarihçesi", {"country": "Yemen"}) is False

class TestExtractionPromptSchema:
    """json_mode carries no schema: when the prompt did not name the fields, the model
    invented keys ('countries', 'themes') that QueryFilters silently ignored, so the
    LLM extracted nothing and only the rule-based fallback ran."""

    def test_prompt_names_every_filter_field(self):
        from rag.query_processor import QueryFilters, _FILTER_EXTRACTION_PROMPT
        assert "fields: " + ", ".join(QueryFilters.model_fields) in _FILTER_EXTRACTION_PROMPT


class TestSouthSudan:
    def test_rule_based_south_sudan_is_not_sudan(self):
        assert _extract_filters_rule_based("cholera outbreak in South Sudan")["country"] == "South Sudan"
        assert _extract_filters_rule_based("Güney Sudan'da kolera")["country"] == "South Sudan"

    def test_rule_based_sudan_still_sudan(self):
        assert _extract_filters_rule_based("Sudan'da kolera")["country"] == "Sudan"

    def test_llm_south_sudan_is_kept(self):
        from rag.query_processor import QueryFilters, _normalize_llm_filters
        assert _normalize_llm_filters(QueryFilters(country="South Sudan"))["country"] == "South Sudan"

    def test_prompt_tells_south_sudan_apart(self):
        from rag.query_processor import _FILTER_RULES
        assert "South Sudan" in _FILTER_RULES


class TestInCountryIsNotADoctype:
    """'ülke içinde yerinden edilmiş' (internally displaced) says where, not which document
    type. Read as doctype=country it limited every Turkish IDP question to country-profile
    records, and the chat answered 'no documents found'."""

    IDP_QUESTION = ("Aralık 2024'ten bu yana kaç Suriyeli mülteci ve ülke içinde yerinden "
                    "edilmiş kişi evine döndü ve nerelere dönüyorlar?")

    def test_rule_based_idp_question_has_no_country_doctype(self):
        f = _extract_filters_rule_based(self.IDP_QUESTION)
        assert f.get("doctype") != "country"
        assert f.get("country") == "Syria"

    @pytest.mark.parametrize("text", [
        "ülke içinde", "Ülke İçinde Yerinden Edilmiş Kişiler", "ulke icinde yerinden edilenler",
        "ülke içi göç",
    ])
    def test_rule_based_bare_phrase_has_no_doctype(self, text):
        assert "doctype" not in _extract_filters_rule_based(text)

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_country_profile_still_sets_the_doctype(self, _mock):
        assert extract_filters("Suriye ülke profili").get("doctype") == "country"

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_country_doctype_for_the_idp_phrase_is_dropped(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Syria", "doctype": "country"}
        f = extract_filters(self.IDP_QUESTION)
        assert "doctype" not in f
        assert f["country"] == "Syria"
        _clear_llm_cache()

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_country_doctype_kept_when_a_profile_is_asked_for(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Syria", "doctype": "country"}
        f = extract_filters("Suriye ülke profili, ülke içinde yerinden edilmiş kişiler")
        assert f["doctype"] == "country"
        _clear_llm_cache()

    def test_follow_up_plan_drops_the_misread_doctype(self):
        from langchain_core.messages import AIMessage, HumanMessage
        from rag.query_processor import QueryPlan, plan_retrieval
        planner = MagicMock()
        planner.invoke.return_value = QueryPlan(
            standalone_query="Suriye'de ülke içinde yerinden edilmiş kişiler nereye dönüyor?",
            country="Syria", doctype="country")
        history = [HumanMessage(content="Suriye'de durum nedir?"), AIMessage(content="...")]
        _, f = plan_retrieval("ya yerinden edilmiş kişiler?", history, planner=planner)
        assert "doctype" not in f
        assert f["country"] == "Syria"


class TestCountryWideIsNotADoctype:
    """'ülke genelinde' / 'ülke çapında' (nationwide) also say where, not which document
    type; the bare 'ülke' key read them as doctype=country like 'ülke içinde' before."""

    @pytest.mark.parametrize("text", [
        "Suriye'de ülke genelinde gıda güvensizliği",
        "Sudan'da ülke çapında kolera salgını",
        "ULKE GENELINDE ASI KAMPANYASI",
        "ulke capinda sel",
        "Ülke Çapında Yerinden Edilme",
        "ülke geneli",
    ])
    def test_rule_based_nationwide_phrase_has_no_doctype(self, text):
        assert _extract_filters_rule_based(text).get("doctype") != "country"

    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_country_doctype_for_a_nationwide_phrase_is_dropped(self, mock_llm):
        _clear_llm_cache()
        mock_llm.return_value = {"country": "Sudan", "doctype": "country"}
        f = extract_filters("Sudan'da ülke çapında kolera salgını")
        assert "doctype" not in f
        assert f["country"] == "Sudan"
        _clear_llm_cache()

    @patch("rag.query_processor._extract_filters_llm", return_value=None)
    def test_country_profile_next_to_a_nationwide_phrase_keeps_the_doctype(self, _mock):
        f = extract_filters("Suriye ülke profili ve ülke genelinde gıda güvensizliği")
        assert f.get("doctype") == "country"


class TestCountryDoctypeOnlyOnProfileRequests:
    """doctype=country limits retrieval to country-profile records, so it is set only
    when the message asks for a profile by name; "ülke"/"country" alone says where."""

    NOT_PROFILE = [
        "Suriyeli mülteciler ülkelerine geri dönüyor mu?",
        "ülkeden kaçan Suriyeliler",
        "Suriye ülkesindeki son durum",
        "returns to the country Syria",
    ]
    PROFILE = [
        "Suriye ülke profili",
        "ülke bilgileri",
        "Ülke Profili: Irak",
        "ulke profilini goster",
        "Sudan country profile",
        "country overview for Yemen",
    ]

    @pytest.mark.parametrize("text", NOT_PROFILE)
    def test_rule_based_has_no_country_doctype(self, text):
        assert "doctype" not in _extract_filters_rule_based(text)

    @pytest.mark.parametrize("text", PROFILE)
    def test_rule_based_profile_request_sets_it(self, text):
        assert _extract_filters_rule_based(text).get("doctype") == "country"

    @pytest.mark.parametrize("text", NOT_PROFILE)
    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_merge_has_no_country_doctype(self, mock_llm, text):
        for llm_out in ({}, {"doctype": "country"}):
            _clear_llm_cache()
            mock_llm.return_value = dict(llm_out)
            assert "doctype" not in extract_filters(text)
        _clear_llm_cache()

    @pytest.mark.parametrize("text", PROFILE)
    @patch("rag.query_processor._extract_filters_llm")
    def test_llm_merge_keeps_a_profile_request(self, mock_llm, text):
        for llm_out in ({}, {"doctype": "country"}):
            _clear_llm_cache()
            mock_llm.return_value = dict(llm_out)
            assert extract_filters(text).get("doctype") == "country"
        _clear_llm_cache()

    @staticmethod
    def _plan(message, standalone):
        from langchain_core.messages import AIMessage, HumanMessage
        from rag.query_processor import QueryPlan, plan_retrieval
        planner = MagicMock()
        planner.invoke.return_value = QueryPlan(
            standalone_query=standalone, country="Syria", doctype="country")
        history = [HumanMessage(content="Suriye'de durum nedir?"), AIMessage(content="...")]
        return plan_retrieval(message, history, planner=planner)[1]

    def test_follow_up_is_judged_on_the_users_message(self):
        # The rewrite may add words the user never wrote; the user's message decides.
        f = self._plan("ya geri dönenler?", "Suriye ülke profili: ülkelerine geri dönenler")
        assert "doctype" not in f
        assert f["country"] == "Syria"

    def test_follow_up_profile_request_keeps_it(self):
        f = self._plan("ülke profilini göster", "Suriye ülke profili")
        assert f["doctype"] == "country"
