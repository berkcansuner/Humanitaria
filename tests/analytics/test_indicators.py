from analytics.indicators import INDICATORS, by_key


def test_food_security_config():
    i = by_key("food_security")
    assert i.endpoint == "food/food-security"
    assert i.value_field == "population_in_phase"
    assert i.admin_level == 0
    assert i.query_params == {"ipc_type": "current", "ipc_phase": "3+"}


def test_conflict_events_config():
    i = by_key("conflict_events")
    assert i.endpoint == "coordination-context/conflict-event"
    assert i.value_field == "fatalities"
    assert i.admin_level == 2


def test_refugees_origin_semantics():
    i = by_key("refugees")
    assert i.query_params == {"gender": "all", "age_range": "all", "population_group": "REF"}
    assert i.admin_level == 0


def test_returnees_config():
    i = by_key("returnees")
    assert i.query_params["population_group"] == "RET"


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
