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


# --- Review 2026-11-18 (Critical): HAPI matches sector_code by prefix, so sector_code=PRO
# also returns PRO-CPN, PRO-GBV, PRO-HLP and PRO-MIN rows, and the largest row per year
# won: Sudan 2025 "Protection: people in need" printed PRO-MIN's 12,998,744. ---

def _pin_row(code, year, value, category=""):
    return {"sector_code": code, "reference_period_start": f"{year}-01-01",
            "population": value, "category": category}


def test_a_sector_people_in_need_keeps_only_its_own_sector_code():
    rows = [_pin_row("PRO", 2025, 11_725_110), _pin_row("PRO", 2025, 11_725_110, "total"),
            _pin_row("PRO-MIN", 2025, 12_998_744), _pin_row("PRO-CPN", 2025, 11_252_673),
            _pin_row("PRO", 2024, 7_740_348), _pin_row("PRO-GBV", 2024, 9_000_000)]
    periods, values = national_series(rows, by_key("pin_protection"))
    assert periods == ["2024-01-01", "2025-01-01"]
    assert values == [7_740_348, 11_725_110]


def test_every_query_param_column_is_matched_exactly():
    # The same guard for any other server-side filter HAPI might match loosely.
    rows = [_pin_row("Intersectoral", 2025, 20), _pin_row("Intersectoral-X", 2025, 99)]
    assert national_series(rows, by_key("humanitarian_needs")) == (["2025-01-01"], [20])


def test_two_published_totals_for_a_year_are_noted():
    from analytics.datasets import competing_totals_note
    rows = [_pin_row("PRO", 2025, 349_999), _pin_row("PRO", 2025, 466_589, "total"),
            _pin_row("PRO", 2024, 250_000), _pin_row("PRO", 2024, 250_000, "total"),
            _pin_row("PRO-CPN", 2023, 1, ""), _pin_row("PRO-CPN", 2023, 5, "total")]
    assert competing_totals_note(rows, by_key("pin_protection")) == (
        "HDX HAPI holds two totals for 2025: 349999 without a breakdown (used) and 466589 as "
        "the total of its breakdown; the HNO's published sector figure may differ")


def test_totals_that_differ_only_by_rounding_are_not_noted():
    from analytics.datasets import competing_totals_note
    rows = [_pin_row("FSC", 2024, 19_325_221), _pin_row("FSC", 2024, 19_325_222, "total")]
    assert competing_totals_note(rows, by_key("pin_food_security")) is None
    assert competing_totals_note([{"population": 1}], by_key("idps")) is None



# --- Round 2: which of the two totals is the published one. Checked against the plans'
# published caseloads (HPC Tools API, 2026-11-18): the undisaggregated row ('') is the
# published figure in 9 of 11 cases; in the other two it is a stray sub-line far smaller
# than the 'total' row (Nigeria CCCM 2024: 780 vs 2,487,269; Myanmar 2025: 1,957,173 vs
# 19,902,649), and there the 'total' row is the published figure. ---

def _hno(code, year, rows):
    return [{"sector_code": code, "reference_period_start": f"{year}-01-01", "population": v,
             "category": c} for c, v in rows]


@pytest.mark.parametrize("code,year,rows,published", [
    # Sudan mine action 2024: published 5,955,027 (HPC plan 1188); 'total' is 6,020,948.
    ("PRO-MIN", 2024, [("", 5_955_027), ("Hostcommunities", 790_357), ("IDPs", 2_082_052),
                       ("Non-Displaced", 3_082_618), ("total", 6_020_948)], 5_955_027),
    # South Sudan health 2025: published 5,657,327 (HPC plan 1223); 'total' is 4,843,460.
    ("HEA", 2025, [("", 5_657_327), ("total", 4_843_460)], 5_657_327),
    # Nigeria protection 2024: published 5,093,865 (HPC plan 1190); 'total' is 5,214,884.
    ("PRO", 2024, [("", 5_093_865), ("total", 5_214_884)], 5_093_865),
    # Nigeria CCCM 2024: published 2,487,269 ("TOTAL - CCCM", HPC plan 1190); '' is 780.
    ("CCM", 2024, [("", 780), ("total", 2_487_269)], 2_487_269),
    # Myanmar 2025 intersectoral: published 19.9 million; '' is 1,957,173.
    ("Intersectoral", 2025, [("", 1_957_173), ("total", 19_902_649)], 19_902_649),
])
def test_the_published_total_is_chosen(code, year, rows, published):
    ind = next(i for i in __import__("analytics.indicators", fromlist=["x"]).SECTOR_INDICATORS
               + __import__("analytics.indicators", fromlist=["x"]).INDICATORS
               if i.query_params.get("sector_code") == code)
    assert national_series(_hno(code, year, rows), ind)[1] == [published]


def test_the_note_names_the_total_used_when_it_is_the_breakdown_total():
    from analytics.datasets import competing_totals_note
    rows = _hno("CCM", 2024, [("", 780), ("total", 2_487_269)])
    assert competing_totals_note(rows, by_key("pin_cccm")) == (
        "HDX HAPI holds two totals for 2024: 780 without a breakdown and 2487269 as the total "
        "of its breakdown (used); the HNO's published sector figure may differ")


# --- Round 2 decision: when HAPI holds a parent sector's sub-lines (PRO-CPN, PRO-GBV …),
# the parent figure is one plan line, not necessarily the sector's overall figure. ---

def _pin(code, name, year, value, category=""):
    return {"sector_code": code, "sector_name": name, "reference_period_start": f"{year}-01-01",
            "population": value, "category": category}


def test_sub_sector_lines_are_listed_per_period_and_never_summed():
    from analytics.datasets import sub_sector_lines
    rows = [_pin("PRO", "Protection", 2025, 349_999), _pin("PRO", "Protection", 2025, 466_589, "total"),
            _pin("PRO-CPN", "Child Protection", 2025, 1_611_291),
            _pin("PRO-GBV", "Gender Based Violence", 2025, 1_535_819),
            _pin("PRO-GBV", "Gender Based Violence", 2025, 1_535_819, "total"),
            _pin("PRO", "Protection", 2026, 2_195_026),
            _pin("PROTECTION-X", "Not a sub-line", 2025, 9)]   # no "PRO-" prefix: not a sub-line
    assert sub_sector_lines(rows, by_key("pin_protection")) == {
        "2025-01-01": [("Child Protection", 1_611_291), ("Gender Based Violence", 1_535_819)]}
    assert sub_sector_lines(rows, by_key("pin_food_security")) == {}
    assert sub_sector_lines(rows, by_key("idps")) == {}


def test_a_much_lower_undisaggregated_row_beside_sub_lines_is_a_leaked_plan_line():
    # Haiti 2025: under PRO, '' = 349,999 is the migrants-protection line; the 'total'
    # 466,589 is the general line (its age/sex breakdown sums to it). Nigeria 2024: under
    # PRO beside its sub-lines, '' = 5,093,865 is the published overall figure ('total'
    # 5,214,884), so a small gap still keeps the undisaggregated row.
    hti = (_hno("PRO", 2025, [("", 349_999), ("Adult - Female", 133_535), ("total", 466_589)])
           + _hno("PRO-CPN", 2025, [("", 1_611_291)]))
    nga = _hno("PRO", 2024, [("", 5_093_865), ("total", 5_214_884)]) + _hno("PRO-GBV", 2024, [("", 2_103_352)])
    assert national_series(hti, by_key("pin_protection"))[1] == [466_589]
    assert national_series(nga, by_key("pin_protection"))[1] == [5_093_865]
