import pandas as pd
from analytics.datasets import national_series, regional_series
from analytics.indicators import by_key

def test_humanitarian_needs_dedup_aggregate_row():
    # Intersectoral+INN server-side geldi varsay; category kırılımı client'ta dedup edilmeli.
    rows = [
        {"reference_period_start": "2024-01-01", "population": 23666389, "category": ""},
        {"reference_period_start": "2024-01-01", "population": 23666389, "category": "total"},
        {"reference_period_start": "2024-01-01", "population": 5000, "category": "Adult - Female"},
        {"reference_period_start": "2025-01-01", "population": 22887726, "category": ""},
    ]
    periods, values = national_series(rows, by_key("humanitarian_needs"))
    assert periods == ["2024-01-01", "2025-01-01"]
    assert values == [23666389, 22887726]  # kategori-toplamı DEĞİL, agregat satır

def test_refugees_sums_asylum_countries_per_period():
    rows = [
        {"reference_period_start": "2024-01-01", "population": 100, "asylum_location_code": "PAK"},
        {"reference_period_start": "2024-01-01", "population": 200, "asylum_location_code": "IRN"},
        {"reference_period_start": "2025-01-01", "population": 300, "asylum_location_code": "PAK"},
    ]
    periods, values = national_series(rows, by_key("refugees"))
    assert values == [300, 300]

def test_conflict_regional_rollup_admin1():
    rows = [
        {"reference_period_start": "2024-01-01", "fatalities": 5, "admin1_name": "Kabul", "event_type": "battles"},
        {"reference_period_start": "2024-01-01", "fatalities": 3, "admin1_name": "Kabul", "event_type": "civilian_targeting"},
        {"reference_period_start": "2024-01-01", "fatalities": 2, "admin1_name": "Herat", "event_type": "battles"},
    ]
    reg = regional_series(rows, by_key("conflict_events"))
    assert reg["Kabul"] == [8]   # event_type'lar toplandı
    assert reg["Herat"] == [2]

def test_regional_empty_when_no_admin1_name():
    rows = [{"reference_period_start": "2024-01-01", "population": 100, "asylum_location_code": "PAK"}]
    assert regional_series(rows, by_key("refugees")) == {}
