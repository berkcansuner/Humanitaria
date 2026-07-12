from analytics.datasets import national_series, regional_series, has_required_filter_columns
from analytics.indicators import by_key


def _row(value, period, admin1="North", status=None, admin1_code="AF01"):
    r = {"population": value, "reference_period_start": period,
         "admin1_name": admin1, "admin1_code": admin1_code}
    if status is not None:
        r["population_status"] = status
    return r


def test_national_series_sorts_and_sums_by_period():
    idps = by_key("idps")
    rows = [
        _row(100, "2025-01-01", "North"),
        _row(50, "2025-01-01", "South"),
        _row(200, "2025-06-01", "North"),
    ]
    periods, values = national_series(rows, idps)
    assert periods == ["2025-01-01", "2025-06-01"]
    assert values == [150.0, 200.0]      # ilk dönem North+South toplandı


def test_national_series_applies_filter():
    # humanitarian_needs yalnızca population_status='INN' satırlarını sayar.
    hn = by_key("humanitarian_needs")
    rows = [
        _row(300, "2025-01-01", status="INN"),
        _row(999, "2025-01-01", status="AFF"),   # farklı status → dışarıda
    ]
    periods, values = national_series(rows, hn)
    assert values == [300.0]


def test_regional_series_groups_by_admin1():
    idps = by_key("idps")
    rows = [
        _row(100, "2025-01-01", "North"),
        _row(200, "2025-06-01", "North"),
        _row(30, "2025-01-01", "South"),
    ]
    reg = regional_series(rows, idps)
    assert reg["North"] == [100.0, 200.0]
    assert reg["South"] == [30.0]


def test_empty_rows_yield_empty():
    idps = by_key("idps")
    assert national_series([], idps) == ([], [])
    assert regional_series([], idps) == {}


def test_has_required_filter_columns_true_when_indicator_has_no_filters():
    idps = by_key("idps")
    assert has_required_filter_columns([_row(100, "2025-01-01")], idps) is True


def test_has_required_filter_columns_true_when_column_present():
    hn = by_key("humanitarian_needs")
    rows = [_row(300, "2025-01-01", status="INN")]
    assert has_required_filter_columns(rows, hn) is True


def test_has_required_filter_columns_false_when_column_missing():
    # population_status alanı hiç gelmemiş → filtre sessizce no-op olup tüm
    # sektörleri toplamamalı; çağıran bunu gap'e düşürmeli.
    hn = by_key("humanitarian_needs")
    rows = [_row(300, "2025-01-01")]   # status=None → population_status alanı yok
    assert has_required_filter_columns(rows, hn) is False


def test_has_required_filter_columns_true_when_rows_empty():
    hn = by_key("humanitarian_needs")
    assert has_required_filter_columns([], hn) is True
