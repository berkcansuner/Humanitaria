import pytest
import pandas as pd
from analytics.datasets import national_series, regional_series
from analytics.indicators import Indicator, by_key

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
    # conflict_events indikatörü rapordan kaldırıldı (Task 6); regional_series'in
    # admin1 üzerinden çoklu-satır toplama davranışı yine de conflict-şekilli veriyle
    # sınanır (event_type'lar toplanır) — ad-hoc Indicator, by_key üzerinden değil.
    rows = [
        {"reference_period_start": "2024-01-01", "fatalities": 5, "admin1_name": "Kabul", "event_type": "battles"},
        {"reference_period_start": "2024-01-01", "fatalities": 3, "admin1_name": "Kabul", "event_type": "civilian_targeting"},
        {"reference_period_start": "2024-01-01", "fatalities": 2, "admin1_name": "Herat", "event_type": "battles"},
    ]
    ind = Indicator("conflict_events", "Çatışma kaynaklı ölüm",
                    "coordination-context/conflict-event", "fatalities", "sum", 2)
    reg = regional_series(rows, ind)
    assert reg["Kabul"] == [8]   # event_type'lar toplandı
    assert reg["Herat"] == [2]

def test_regional_empty_when_no_admin1_name():
    rows = [{"reference_period_start": "2024-01-01", "population": 100, "asylum_location_code": "PAK"}]
    assert regional_series(rows, by_key("refugees")) == {}

def test_regional_empty_when_admin1_name_all_none():
    # M-2: admin1_name kolonu VAR ama tüm değerler None — kolon-yok testinden ayrık yol.
    rows = [
        {"reference_period_start": "2024-01-01", "population": 100, "admin1_name": None},
        {"reference_period_start": "2024-01-01", "population": 50, "admin1_name": None},
    ]
    assert regional_series(rows, by_key("refugees")) == {}

def test_national_series_empty_rows():
    # M-1: boş rows sanity — regresyona karşı.
    assert national_series([], by_key("idps")) == ([], [])

def test_regional_series_empty_rows():
    # M-1: boş rows sanity — regresyona karşı.
    assert regional_series([], by_key("idps")) == {}

def test_humanitarian_needs_dedup_picks_true_total_over_leaked_subrow():
    # I-1: sabitlenmemiş bir boyuttan sızan category="" alt-küme satırı, gerçek
    # sektörler-arası toplamı EZMEMELİ — en büyük değer (= toplam) seçilmeli.
    rows = [
        {"reference_period_start": "2024-01-01", "population": 5000, "category": ""},
        {"reference_period_start": "2024-01-01", "population": 23666389, "category": ""},
    ]
    periods, values = national_series(rows, by_key("humanitarian_needs"))
    assert periods == ["2024-01-01"]
    assert values == [23666389]

def test_humanitarian_needs_dedup_survives_null_first_row():
    # I-2: dönemin ilk-listelenen agregat satırı population=None olsa da, sonraki
    # geçerli category="total" satırı sayesinde dönem KAYBOLMAMALI.
    rows = [
        {"reference_period_start": "2024-01-01", "population": None, "category": ""},
        {"reference_period_start": "2024-01-01", "population": 23666389, "category": "total"},
    ]
    periods, values = national_series(rows, by_key("humanitarian_needs"))
    assert periods == ["2024-01-01"]
    assert values == [23666389]


# --- IDPs (live check, Sudan 2026-11-16): HAPI mixes several DTM operations that
# count displacement differently ('Overview' totals vs event-based 'Armed Clashes'
# vs the old 'Darfur conflict' caseload), and rounds cover different regions; summing
# everything per date gave n=165 and a +83,144% change. ---

from analytics.datasets import consistent_snapshots   # noqa: E402


def _snap(op, date, regions, value=10):
    return [{"operation": op, "reference_period_start": date, "admin1_name": r, "population": value}
            for r in regions]


R18 = [f"R{i}" for i in range(18)]


def test_the_broadest_operation_is_kept_and_ties_go_to_the_latest():
    rows = (_snap("Event", "2024-04-17", R18) + _snap("Event", "2024-03-01", R18)
            + _snap("Overview", "2026-08-31", R18) + _snap("Darfur", "2025-01-01", R18[:7]))
    kept, note = consistent_snapshots(rows)
    assert {r["operation"] for r in kept} == {"Overview"}
    assert "Overview" in note


def test_breadth_beats_recency():
    # Yemen: the narrow, recent 'West Coast' event must not replace the countrywide series.
    rows = _snap("Yemen conflict", "2026-06-30", R18) + _snap("West Coast", "2026-10-03", R18[:10])
    kept, _ = consistent_snapshots(rows)
    assert {r["operation"] for r in kept} == {"Yemen conflict"}


def test_incomplete_rounds_are_left_out():
    rows = (_snap("Op", "2025-01-31", R18) + _snap("Op", "2025-02-28", R18[:14])
            + _snap("Op", "2025-03-31", R18[:15]))
    kept, note = consistent_snapshots(rows)
    assert sorted({r["reference_period_start"] for r in kept}) == ["2025-01-31", "2025-03-31"]
    assert "1 incomplete" in note


def test_rows_without_operations_are_untouched():
    rows = [{"reference_period_start": "2025-01-01", "population": 5, "asylum_location_code": "PAK"}]
    assert consistent_snapshots(rows) == (rows, None)


def test_a_single_complete_operation_needs_no_note():
    rows = _snap("Op", "2025-01-31", R18) + _snap("Op", "2025-02-28", R18)
    kept, note = consistent_snapshots(rows)
    assert kept == rows and note is None


# --- Food security (Yemen, 2026-11-16): the analysed population alternates between
# the whole country (~35M) and government-held areas (~10M), so people in IPC 3+ read
# 17.4M -> 3.2M -> 4.6M -> 17.1M -> 5.0M while the share stayed 34-55%. ---

from analytics.datasets import ipc_coverage_note   # noqa: E402

_YEMEN_IPC = [  # (start, people in phase 3+, share)
    ("2022-01-01", 17365500, 0.55), ("2023-01-01", 3234000, 0.34), ("2024-07-01", 4647925, 0.46),
    ("2025-05-01", 17145484, 0.49), ("2026-03-01", 4980505, 0.47),
]


def _ipc_rows(data=_YEMEN_IPC):
    return [{"reference_period_start": s, "population_in_phase": n, "population_fraction_in_phase": f}
            for s, n, f in data]


def test_food_security_series_is_the_share_in_percent():
    periods, values = national_series(_ipc_rows(), by_key("food_security"))
    assert values == pytest.approx([55.0, 34.0, 46.0, 49.0, 47.0])


def test_coverage_note_when_the_analysed_population_changes():
    note = ipc_coverage_note(_ipc_rows())
    assert note is not None
    assert "9.5" in note and "35.0" in note and "share" in note


def test_no_coverage_note_when_the_analysed_population_is_stable():
    stable = [("2024-01-01", 10_000_000, 0.20), ("2025-01-01", 11_000_000, 0.21)]
    assert ipc_coverage_note(_ipc_rows(stable)) is None
    assert ipc_coverage_note([{"reference_period_start": "2024-01-01", "population": 5}]) is None
