from analytics.indicators import INDICATORS, by_key


def test_food_security_config():
    i = by_key("food_security")
    assert i.endpoint == "food/food-security"
    # Share of the analysed population, not people: IPC analyses cover different parts
    # of a country in different periods (Yemen: 9.5 vs 35 million analysed).
    assert i.value_field == "population_fraction_in_phase"
    assert i.aggregation == "mean" and i.scale == 100 and i.unit == "percentage points"
    assert i.admin_level == 0
    assert i.query_params == {"ipc_type": "current", "ipc_phase": "3+"}


def test_conflict_events_removed():
    assert by_key("conflict_events") is None


def test_refugees_origin_semantics():
    i = by_key("refugees")
    assert i.query_params == {"gender": "all", "age_range": "all", "population_group": "REF"}
    assert i.admin_level == 0


def test_returnees_config():
    i = by_key("returnees")
    assert i.query_params["population_group"] == "RET"


def test_refugees_uses_origin_location():
    i = by_key("refugees")
    assert i.location_param == "origin_location_code"
    assert i.query_params == {"gender": "all", "age_range": "all", "population_group": "REF"}


def test_returnees_uses_origin_location():
    assert by_key("returnees").location_param == "origin_location_code"


def test_default_indicators_use_location_code():
    for key in ("humanitarian_needs", "food_security", "idps", "funding"):
        assert by_key(key).location_param == "location_code"


def test_indicator_count():
    assert len(INDICATORS) == 6
    assert {i.key for i in INDICATORS} == {
        "humanitarian_needs", "food_security", "idps", "funding", "refugees", "returnees"}


def test_humanitarian_needs_config():
    i = by_key("humanitarian_needs")
    assert i.endpoint == "affected-people/humanitarian-needs"
    assert i.value_field == "population"
    assert i.query_params == {"population_status": "INN", "sector_code": "Intersectoral"}
    assert i.admin_level == 0


def test_funding_value_field():
    assert by_key("funding").value_field == "funding_usd"


def test_all_indicators_have_admin_level():
    assert all(isinstance(i.admin_level, int) for i in INDICATORS)


# --- Sector reports (2026-11-18: an Afghanistan "Food and Nutrition" technical report
# analysed IDPs and funding — the sector never reached the indicator selection). ---

def test_all_sectors_keeps_the_six_overview_indicators():
    from analytics.indicators import indicators_for
    assert indicators_for(None) == INDICATORS


def test_food_and_nutrition_leads_with_its_people_in_need_and_ipc():
    from analytics.indicators import indicators_for
    keys = [i.key for i in indicators_for("Food and Nutrition")]
    assert keys == ["pin_food_security", "pin_nutrition", "food_security"]


def test_displacement_belongs_to_protection_and_camp_management():
    from analytics.indicators import indicators_for
    assert [i.key for i in indicators_for("Protection and Human Rights")] == [
        "pin_protection", "refugees", "returnees", "idps"]
    assert [i.key for i in indicators_for("Camp Coordination and Camp Management")] == [
        "pin_cccm", "idps"]


def test_funding_only_where_funding_is_the_subject():
    # FTS funding has no sector dimension in HDX HAPI: all-sector funding is not a
    # sector's funding, so it appears only in the financing themes.
    from analytics.indicators import THEME_INDICATORS
    with_funding = {t for t, keys in THEME_INDICATORS.items() if "funding" in keys}
    assert with_funding == {"Humanitarian Financing", "Contributions"}


def test_a_sector_without_hapi_series_gets_no_indicators():
    from analytics.indicators import indicators_for
    assert indicators_for("Logistics and Telecommunications") == []
    assert indicators_for("Agriculture") == []


def test_every_mapped_theme_is_a_form_theme_and_every_key_exists():
    from analytics.indicators import THEME_INDICATORS
    from api.routes.reports import THEMES
    assert set(THEME_INDICATORS) <= set(THEMES)
    assert all(by_key(k) for keys in THEME_INDICATORS.values() for k in keys)


def test_sector_people_in_need_series_ask_hapi_for_their_sector():
    pin = by_key("pin_food_security")
    assert pin.endpoint == "affected-people/humanitarian-needs"
    assert pin.query_params == {"population_status": "INN", "sector_code": "FSC"}
    assert pin.admin_level == 0 and pin.source == "OCHA HNO"
    assert by_key("pin_nutrition").query_params["sector_code"] == "NUT"
    assert by_key("pin_wash").query_params["sector_code"] == "WSH"


def test_sector_indicators_are_named_in_both_languages():
    from analytics.indicators import SECTOR_INDICATORS
    for ind in SECTOR_INDICATORS:
        assert ind.label_en and ind.label and ind.name("en") != ind.name("tr")
        assert ind.source
    assert by_key("pin_food_security").name("en") == "Food security: people in need"
    assert by_key("pin_food_security").name("tr") == (
        "Gıda güvenliği: insani yardıma ihtiyaç duyan kişiler")


def test_a_sector_has_a_general_line_name_in_both_languages():
    pro = by_key("pin_protection")
    assert pro.general_name("en") == "General protection: people in need"
    assert pro.general_name("tr") == "Genel koruma: insani yardıma ihtiyaç duyan kişiler"
    assert pro.sector_en == "protection"
