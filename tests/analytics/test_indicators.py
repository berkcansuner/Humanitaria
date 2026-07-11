from analytics.indicators import INDICATORS, Indicator, by_key


def test_registry_nonempty_and_typed():
    assert len(INDICATORS) >= 5
    assert all(isinstance(i, Indicator) for i in INDICATORS)


def test_each_indicator_has_endpoint_and_value_field():
    for i in INDICATORS:
        assert "/" in i.endpoint            # theme/subcategory
        assert i.value_field
        assert i.aggregation in ("sum", "mean", "latest")


def test_by_key_lookup():
    idps = by_key("idps")
    assert idps is not None
    assert idps.endpoint == "affected-people/idps"
    assert idps.value_field == "population"
    assert by_key("nonexistent") is None


def test_humanitarian_needs_has_dedup_filter():
    # HNO sektör satırlarını üst üste toplamamak için population_status filtresi.
    hn = by_key("humanitarian_needs")
    assert hn is not None
    assert hn.filters.get("population_status") == "INN"
