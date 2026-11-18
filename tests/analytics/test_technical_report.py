import json
from pathlib import Path
from unittest.mock import patch

import requests

from analytics.technical_report import (
    compute_findings, findings_to_context, assemble_section_images,
    Findings, ReportSection,
)
from analytics.indicators import INDICATORS


def _rows_for(key):
    # 4 dönemlik artan ulusal seri, tek bölge — trend testini tetikler.
    if key == "idps":
        return [
            {"population": v, "reference_period_start": p, "admin1_name": "North",
             "admin1_code": "AF01"}
            for v, p in [(100, "2025-01-01"), (200, "2025-04-01"),
                         (300, "2025-07-01"), (400, "2025-10-01")]
        ]
    return []   # diğer indikatörler boş → gaps


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_compute_findings_builds_trend_section(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31")
    assert isinstance(f, Findings)
    assert "idps" in f.indicators_covered
    # Boş dönen indikatörler gaps'e düştü:
    assert any("humanitarian_needs" in g or "İnsani" in g for g in f.gaps)
    trend_sections = [s for s in f.sections if s.stat_result.get("kind") == "trend"]
    assert trend_sections and trend_sections[0].stat_result["direction"] == "increasing"
    assert trend_sections[0].chart is not None


@patch("analytics.technical_report.fetch_rows", side_effect=lambda *a, **k: [])
def test_all_empty_yields_only_gaps(_mock):
    f = compute_findings("XYZ", None, None)
    assert f.indicators_covered == []
    assert len(f.gaps) == len(__import__("analytics.indicators", fromlist=["INDICATORS"]).INDICATORS)
    assert f.sections == []


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_findings_to_context_is_string_with_numbers(_mock):
    f = compute_findings("AFG", None, None)
    ctx = findings_to_context(f)
    assert isinstance(ctx, str)
    assert "idps" in ctx.lower() or "IDP" in ctx
    assert "p=" in ctx or "p-value" in ctx.lower()


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_assemble_section_images_shape(_mock):
    f = compute_findings("AFG", None, None)
    imgs = assemble_section_images(f)
    assert all(set(d.keys()) == {"heading", "image", "image_dark"} for d in imgs)
    assert all(d["image"].startswith("data:image/png;base64,") for d in imgs)
    # The dark-theme chart is a separate drawing, not the light one again.
    assert all(d["image_dark"].startswith("data:image/png;base64,") for d in imgs)
    assert all(d["image_dark"] != d["image"] for d in imgs)


def _multi_region_rows(key):
    # idps için ≥4 dönem × 2 ayrı admin1 bölgesi → regional_series ≥2 bölge döndürür,
    # by_region analiz yolu (len(reg) >= 2) tetiklenir.
    if key == "idps":
        rows = []
        for region, code, base in [("North", "AF01", 100), ("South", "AF02", 50)]:
            for i, p in enumerate(["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]):
                rows.append({"population": base + i * 40, "reference_period_start": p,
                             "admin1_name": region, "admin1_code": code})
        return rows
    return []


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _multi_region_rows(
    "idps" if ep.endswith("idps") else "other"))
def test_by_region_section_for_multi_region_indicator(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31")
    region_sections = [s for s in f.sections if s.stat_result.get("kind") == "region"]
    assert region_sections, "≥2 bölgeli indikatör bölgesel analiz bölümü üretmeli"
    assert region_sections[0].chart is not None
    assert region_sections[0].stat_result["ranking"], "ranking dolu olmalı"


_EIGHT_QUARTERS = ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01",
                   "2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]


def _two_indicator_rows(ep, periods=_EIGHT_QUARTERS):
    # idps ve food_security için ortak dönemli, ilişkili iki seri → korelasyon
    # (en az CORRELATION_MIN_POINTS = 8 ortak dönem gerekir).
    base = {
        "idps": [(100 * (i + 1), p) for i, p in enumerate(periods)],
        "food_security": [(120 * (i + 1) + (7 if i % 2 else 0), p) for i, p in enumerate(periods)],
    }
    key = "idps" if ep.endswith("idps") else ("food_security" if "food-security" in ep else None)
    if key is None:
        return []
    value_field = "population" if key == "idps" else "population_fraction_in_phase"
    return [{value_field: v, "reference_period_start": p, "admin1_name": "North",
             "admin1_code": "AF01"} for v, p in base[key]]


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _two_indicator_rows(ep))
def test_correlation_section_for_two_indicators(_mock):
    f = compute_findings("AFG", "2024-01-01", "2025-12-31")
    corr = [s for s in f.sections if s.stat_result.get("kind") == "correlation"]
    assert corr, "iki ilişkili indikatör korelasyon bölümü üretmeli"
    assert corr[0].stat_result["coefficient"] is not None
    assert corr[0].chart is not None


def test_network_error_on_one_indicator_becomes_gap_not_abort():
    # HAPI ağ kesintisi (ConnectionError) yalnızca ilgili indikatörü gaps'e
    # düşürmeli; tüm raporu iptal etmemeli — diğer indikatörler işlenmeye devam eder.
    def _side_effect(ep, iso3, **k):
        if ep.endswith("idps"):
            raise requests.exceptions.ConnectionError("network down")
        return _rows_for("other")

    with patch("analytics.technical_report.fetch_rows", side_effect=_side_effect):
        f = compute_findings("AFG", None, None)

    assert any("idps" in g or "yerinden edilmiş" in g for g in f.gaps)
    assert "idps" not in f.indicators_covered
    # Diğer indikatörler (hepsi boş döner) yine de işlendi → kendi gaps'lerine düştü.
    assert len(f.gaps) == len(__import__("analytics.indicators", fromlist=["INDICATORS"]).INDICATORS)


# --- FIX I1: findings_to_context şimdi her bölümün başlığını verbatim '## ' satırı olarak taşımalı ---

@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_findings_to_context_contains_verbatim_section_headings(_mock):
    # Grafik-eşleme (assemble_section_images) s.heading'e göre yapılır; LLM context'inde
    # AYNI başlık '## ' satırı olarak yer almazsa render tarafı grafiği asla eşleştiremez.
    f = compute_findings("AFG", "2025-01-01", "2025-12-31")
    ctx = findings_to_context(f)
    assert f.sections, "test verisi en az bir bölüm üretmeli"
    for s in f.sections:
        assert f"## {s.heading}" in ctx


# --- FIX I2: bir indikatörün analiz aşamasındaki hata (örn. kruskal ValueError) rapor
# genelini iptal etmemeli; yalnızca o indikatör gap'e düşmeli, diğerleri işlenmeye devam etmeli. ---

def test_indicator_analysis_error_becomes_gap_not_abort():
    def _side_effect(ep, iso3, **k):
        # idps: ≥2 bölge → regional_series len(reg)>=2 → by_region tetiklenir.
        if ep.endswith("idps"):
            return _multi_region_rows("idps")
        return _rows_for("other")

    # by_region (stat_tests) bu ortamdaki scipy sürümünde artık sabit değerlerde
    # ValueError fırlatmıyor (nan/nan döner) — bu yüzden fix'in koruduğu davranışı
    # (ANY exception → gap + continue, tüm rapor iptal olmaz) doğrudan by_region'ı
    # ValueError ile patch'leyerek, senaryodan bağımsız şekilde doğruluyoruz.
    with patch("analytics.technical_report.by_region",
               side_effect=ValueError("All numbers are identical in kruskal")):
        with patch("analytics.technical_report.fetch_rows", side_effect=_side_effect):
            f = compute_findings("AFG", "2025-01-01", "2025-12-31")

    assert isinstance(f, Findings)
    assert any("analiz hatası" in g for g in f.gaps)
    # idps hatalı indikatör kapsanmadı olarak sayılmamalı (region aşamasında patladı):
    idps_gap = [g for g in f.gaps if "analiz hatası" in g]
    assert idps_gap
    # Diğer tüm indikatörler (boş veri) yine işlendi → kendi gaps'lerine düştü, rapor
    # tam INDICATORS sayısı kadar gap/section üretti (abort olmadı):
    assert len(f.gaps) == len(INDICATORS)


# --- Orkestratör fetch_rows'a Indicator.query_params + admin_level'i geçirmeli
# (double-counting koruması artık server-side query_params + datasets category-dedup
# ile sağlanıyor; has_required_filter_columns client-side guard'ı KALDIRILDI). ---

def test_orchestrator_passes_query_params_and_admin_level(monkeypatch):
    calls = []
    def fake_fetch(endpoint, iso3, extra_params=None, admin_level=None, location_param="location_code"):
        calls.append((endpoint, extra_params, admin_level, location_param))
        return []   # boş → hepsi gap, ama çağrı imzası doğrulanır
    monkeypatch.setattr("analytics.technical_report.fetch_rows", fake_fetch)
    from analytics.technical_report import compute_findings
    compute_findings("AFG", None, None)
    by_ep = {c[0]: c for c in calls}
    assert by_ep["food/food-security"][1] == {"ipc_type": "current", "ipc_phase": "3+"}
    assert by_ep["food/food-security"][2] == 0
    assert by_ep["affected-people/refugees"][3] == "origin_location_code"
    assert "coordination-context/conflict-event" not in by_ep


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _two_indicator_rows(ep, _EIGHT_QUARTERS[:7]))
def test_no_correlation_section_below_eight_common_periods(_mock):
    f = compute_findings("AFG", None, None)
    assert not [s for s in f.sections if s.stat_result.get("kind") == "correlation"]


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _two_indicator_rows(ep))
def test_holm_adjusts_all_tests_together_and_code_decides_significance(_mock):
    f = compute_findings("AFG", None, None)
    tested = [s for s in f.sections if s.stat_result.get("p_value") is not None]
    assert len(tested) >= 3                       # two trends + one correlation
    for s in tested:
        r = s.stat_result
        assert r["p_adjusted"] >= r["p_value"]
        assert r["significant"] == (r["p_adjusted"] < 0.05)
        verdict = "NOT SIGNIFICANT" if not r["significant"] else "SIGNIFICANT"
        assert f"→ {verdict} (α=0.05)" in s.findings_text
        assert "Holm-adjusted p" in s.findings_text


def _uneven_rows(ep):
    # 2023 is missing: four yearly values 100, 200, 300, 500 at 2021, 2022, 2024, 2025.
    if not ep.endswith("idps"):
        return []
    return [{"population": v, "reference_period_start": p, "admin1_name": "North",
             "admin1_code": "AF01"}
            for v, p in [(100, "2021-01-01"), (200, "2022-01-01"),
                         (300, "2024-01-01"), (500, "2025-01-01")]]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _uneven_rows(ep))
def test_trend_slope_is_per_year_on_real_dates(_mock):
    f = compute_findings("AFG", "2020-01-01", None)
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    # Pairwise slopes per year: 100, 66.7, 100, 50, 100, 200 (missing 2023 kept as a gap)
    # -> median 100 per year; an index axis would have said 125 per "period".
    assert abs(tr.stat_result["slope"] - 100.0) < 0.1     # days / 365.25, not whole years
    assert "per year" in tr.findings_text


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_context_carries_method_notes_and_no_half_split_test(_mock):
    f = compute_findings("AFG", None, None)
    assert not [s for s in f.sections if "Dönem Karşılaştırması" in s.heading]
    ctx = findings_to_context(f)
    assert "METHOD NOTES:" in ctx and "Holm correction" in ctx
    assert "serial correlation" in ctx


# --- Live check 2026-11-16 (Sudan): funding ran to 2029 (future appeal years) and
# the current year's partial total, so the last point faked a -95% drop; with no
# period chosen the report spanned 2000 onwards. ---

def _funding_rows(ep):
    if not ep.endswith("funding"):
        return []
    from datetime import date
    y = date.today().year
    rows = [{"funding_usd": 100 + 10 * i, "reference_period_start": f"{y - 4 + i}-01-01",
             "reference_period_end": f"{y - 4 + i}-12-31"} for i in range(4)]   # 4 complete years
    rows.append({"funding_usd": 5, "reference_period_start": f"{y}-01-01",
                 "reference_period_end": f"{y}-12-31"})                          # this year, partial
    rows.append({"funding_usd": 1, "reference_period_start": f"{y + 3}-01-01",
                 "reference_period_end": f"{y + 3}-12-31"})                      # future plan
    rows.append({"funding_usd": 999, "reference_period_start": f"{y - 9}-01-01",
                 "reference_period_end": f"{y - 9}-12-31"})                      # outside 5 years
    return rows


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _funding_rows(ep))
def test_future_unfinished_and_old_periods_are_left_out_by_default(_mock):
    f = compute_findings("SDN", None, None)
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert tr.stat_result["n_points"] == 4                  # only the complete years in range
    assert tr.stat_result["pct_change"] > 0                 # no fake drop at the end


def test_stock_indicators_keep_the_current_period():
    # A stock (IDPs, refugees) reported this year is a real current figure; only
    # flows that accumulate over the period (funding) wait for the period to end.
    from analytics.indicators import by_key
    assert by_key("funding").complete_periods_only is True
    assert by_key("idps").complete_periods_only is False


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _funding_rows(ep))
def test_context_states_the_period_analysed(_mock):
    from datetime import date, timedelta
    f = compute_findings("SDN", None, None)
    ctx = findings_to_context(f)
    today = date.today()
    assert f"PERIOD ANALYSED: {today.replace(year=today.year - 5).isoformat()} to {today.isoformat()}" in ctx
    assert "last 5 years" in ctx


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _funding_rows(ep))
def test_a_chosen_period_is_kept_but_capped_at_today(_mock):
    from datetime import date
    y = date.today().year
    f = compute_findings("SDN", f"{y - 10}-01-01", f"{y + 5}-12-31")
    ctx = findings_to_context(f)
    assert f"PERIOD ANALYSED: {y - 10}-01-01 to {date.today().isoformat()}" in ctx
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert tr.stat_result["n_points"] == 5                  # the 999 year joins; future/partial do not


def _sudan_like_idp_rows(ep):
    # Two DTM operations over the same months: an 'Overview' stock (~8M) and an
    # event-based count (~6M). Mixed per date they would zig-zag between definitions.
    if not ep.endswith("idps"):
        return []
    from datetime import date
    y = date.today().year
    regions = [f"R{i}" for i in range(10)]
    rows = []
    for m, (overview, event) in enumerate([(800, 600), (810, 610), (820, 620), (830, 630)], start=1):
        for r in regions:
            rows.append({"operation": "Overview", "admin1_name": r, "population": overview,
                         "reference_period_start": f"{y - 1}-{m:02d}-28"})
            rows.append({"operation": "Armed Clashes", "admin1_name": r, "population": event,
                         "reference_period_start": f"{y - 1}-{m:02d}-15"})
    return rows


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _sudan_like_idp_rows(ep))
def test_idp_series_uses_one_operation_and_says_so(_mock):
    f = compute_findings("SDN", None, None)
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert tr.stat_result["n_points"] == 4                  # not 8 interleaved points
    assert tr.stat_result["pct_change"] > 0
    ctx = findings_to_context(f)
    assert "DATA NOTES:" in ctx and "only the DTM operation 'Overview' is used" in ctx


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _sudan_like_idp_rows(ep))
def test_change_is_written_with_the_sign_before_the_number(_mock):
    # The context said "%-24.1" and the Turkish report copied "%-24,1" (should be -%24,1).
    tr = next(s for s in compute_findings("SDN", None, None).sections if s.stat_result["kind"] == "trend")
    assert "=+" in tr.findings_text and "%, observed first value" in tr.findings_text
    assert "%-" not in tr.findings_text and "=%" not in tr.findings_text


def _yemen_ipc_rows(ep):
    if "food-security" not in ep:
        return []
    from datetime import date
    y = date.today().year
    data = [(y - 4, 17365500, 0.55), (y - 3, 3234000, 0.34), (y - 2, 4647925, 0.46),
            (y - 1, 17145484, 0.49), (y, 4980505, 0.47)]
    return [{"reference_period_start": f"{yr}-01-01", "reference_period_end": f"{yr}-03-31",
             "population_in_phase": n, "population_fraction_in_phase": f} for yr, n, f in data]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _yemen_ipc_rows(ep))
def test_food_security_trend_is_on_the_share_with_a_coverage_note(_mock):
    f = compute_findings("YEM", None, None)
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert "percentage points per year" in tr.findings_text
    assert tr.stat_result["n_points"] == 5
    ctx = findings_to_context(f)
    assert "DATA NOTES:" in ctx and "analysed population" in ctx


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_english_report_names_sections_in_english(_mock):
    # An English report used to get Turkish headings ("— Trend Analizi") and chart text.
    f = compute_findings("AFG", "2025-01-01", "2025-12-31", language="en")
    headings = [s.heading for s in f.sections]
    assert "Internally displaced people (IDPs) — Trend Analysis" in headings
    assert not any("Analizi" in h or "Yerinden" in h for h in headings)
    trend_sections = [s for s in f.sections if s.stat_result.get("kind") == "trend"]
    assert trend_sections[0].stat_result["indicator"] == "Internally displaced people (IDPs)"


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _rows_for(
    "idps" if ep.endswith("idps") else "other"))
def test_turkish_report_keeps_turkish_headings(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31", language="tr")
    assert "Ülke içinde yerinden edilmiş kişiler (IDP) — Eğilim Analizi" in [s.heading for s in f.sections]


def test_every_indicator_has_an_english_name():
    assert all(ind.label_en and ind.name("en") != ind.name("tr") for ind in INDICATORS)


def test_source_line_names_the_publishers_then_hdx_hapi():
    from analytics.technical_report import _source_line
    assert _source_line(["IOM DTM"], "en") == "Source: IOM DTM · HDX HAPI"
    assert _source_line(["IOM DTM", "OCHA FTS"], "tr") == "Kaynak: IOM DTM; OCHA FTS · HDX HAPI"
    assert _source_line(["UNHCR", "UNHCR"], "en") == "Source: UNHCR · HDX HAPI"
    assert _source_line([""], "en") == "Source: HDX HAPI"


def test_every_indicator_names_its_publisher():
    assert all(ind.source for ind in INDICATORS)


def test_plain_keeps_three_significant_digits_for_large_values():
    from analytics.technical_report import _plain
    assert _plain(-931170.92) == "-931000"
    assert _plain(1_794_000.4) == "1790000"
    assert _plain(4.7923) == "4.79"
    assert _plain(45.27) == "45.3"
    assert _plain(0) == "0"


def test_trend_text_does_not_quote_slopes_to_the_cent():
    from analytics.technical_report import _trend_text
    text = _trend_text({
        "indicator": "IDPs", "direction": "decreasing", "slope": -931170.92,
        "ci_low": -1153344.92, "ci_high": -603416.78, "tau": -0.34, "p_value": 0.002,
        "p_adjusted": 0.012, "significant": True, "pct_change": -24.9,
        "first_period": "2023-08-31", "last_period": "2026-09-30", "n_points": 40, "unit": "",
        "first_value": 9_100_000.4, "latest_value": 6_800_000.6, "value_unit": "people",
    })
    assert "Sen slope=-931000 per year" in text
    assert "95% CI -1150000 to -603000" in text
    assert ".92" not in text and ".78" not in text


def test_dtm_charts_carry_iom_required_credit_line():
    # IOM's terms require "International Organization for Migration (IOM), [month, year],
    # Displacement Tracking Matrix (DTM)" plus the source URL wherever DTM data is shown.
    from analytics.indicators import by_key
    from analytics.technical_report import _credit, _source_line
    idps = by_key("idps")
    en = _source_line([_credit(idps, "2026-09-30T00:00:00", "en")], "en")
    assert en == ("Source: International Organization for Migration (IOM), September 2026, "
                  "Displacement Tracking Matrix (DTM), https://dtm.iom.int · HDX HAPI")
    tr = _credit(idps, "2026-09-30", "tr")
    assert tr.startswith("International Organization for Migration (IOM), Eylül 2026, ")
    # Indicators without a required credit keep the short publisher name.
    assert _credit(by_key("funding"), "2025-01-01", "en") == "OCHA FTS"


def test_indicators_are_named_in_turkish_only_for_turkish_reports():
    # A report in another language takes the English names, like its English headings.
    assert all(ind.name("fr") == ind.name("en") for ind in INDICATORS)


# --- Sector reports (2026-11-18, Afghanistan "Food and Nutrition": the report analysed
# IDPs by region; the sector never reached the indicator selection). ---

def _recording_fetch(calls, rows_for=lambda ep, params: []):
    def fake_fetch(endpoint, iso3, extra_params=None, admin_level=None, location_param="location_code"):
        calls.append((endpoint, dict(extra_params or {})))
        return rows_for(endpoint, extra_params or {})
    return fake_fetch


def test_all_sectors_fetches_the_six_overview_indicators(monkeypatch):
    calls = []
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch(calls))
    compute_findings("AFG", None, None, language="en", theme=None)
    assert len(calls) == len(INDICATORS)
    assert ("affected-people/humanitarian-needs",
            {"population_status": "INN", "sector_code": "Intersectoral"}) in calls


def test_food_and_nutrition_fetches_only_its_indicators(monkeypatch):
    calls = []
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch(calls))
    compute_findings("AFG", None, None, language="en", theme="Food and Nutrition")
    assert [(ep, p.get("sector_code") or p.get("ipc_phase")) for ep, p in calls] == [
        ("affected-people/humanitarian-needs", "FSC"),
        ("affected-people/humanitarian-needs", "NUT"),
        ("food/food-security", "3+"),
    ]


def test_a_sector_without_series_fetches_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch(calls))
    f = compute_findings("AFG", None, None, language="en", theme="Logistics and Telecommunications")
    assert calls == [] and f.sections == [] and f.indicators_covered == []


def _sector_pin_rows(endpoint, params):
    # HNO rows as HAPI returns them: each year twice (category '' and 'total'), plus
    # a demographic breakdown that must not be added in.
    if params.get("sector_code") != "FSC":
        return []
    rows = []
    for year, value in [(2022, 14_000_000), (2023, 15_000_000), (2024, 15_800_000),
                        (2025, 14_800_000), (2026, 17_400_000)]:
        for category in ("", "total"):
            rows.append({"population": value, "category": category,
                         "reference_period_start": f"{year}-01-01",
                         "reference_period_end": f"{year}-12-31"})
        rows.append({"population": value // 2, "category": "Children",
                     "reference_period_start": f"{year}-01-01",
                     "reference_period_end": f"{year}-12-31"})
    return rows


def test_sector_people_in_need_is_one_value_a_year(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _sector_pin_rows))
    f = compute_findings("AFG", "2021-01-01", "2026-11-18", language="en",
                         theme="Food and Nutrition")
    assert f.indicators_covered == ["pin_food_security"]
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert tr.heading == "Food security: people in need — Trend Analysis"
    assert tr.stat_result["n_points"] == 5          # not ten (duplicates) or more (breakdowns)
    assert "(n=" not in "".join(f.gaps)


# --- A one-year period starved the statistics (2026-11-18): annual and half-yearly
# series held one observation, so no trend could be tested. A trend now looks back
# over the default window ending at the chosen end date, and says so. ---

def _yearly_ipc_rows(ep, years_back=4):
    # One IPC share a year, 1 January of each of the last five years (rising).
    if "food-security" not in ep:
        return []
    from datetime import date
    y = date.today().year
    return [{"reference_period_start": f"{y - k}-01-01", "reference_period_end": f"{y - k}-03-31",
             "population_in_phase": 1000, "population_fraction_in_phase": 0.40 - 0.02 * k}
            for k in range(years_back, -1, -1)]


def _last_year():
    from datetime import date
    today = date.today()
    return today.replace(year=today.year - 1).isoformat(), today.isoformat()


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _yearly_ipc_rows(ep))
def test_a_short_period_takes_its_trend_from_a_longer_look_back(_mock):
    from datetime import date
    date_from, date_to = _last_year()
    today = date.today()
    f = compute_findings("AFG", date_from, date_to, language="en")
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    look_back_from = today.replace(year=today.year - 5).isoformat()
    assert tr.stat_result["n_points"] == 5
    assert tr.stat_result["look_back"] == {"date_from": look_back_from, "date_to": date_to,
                                          "chosen_points": 1}
    assert (f"the chosen period {date_from} to {date_to} holds 1 observation, too few for a "
            f"trend test, so the trend is computed over {look_back_from} to {date_to}"
            in tr.findings_text)
    assert f"Latest value as of the chosen period: 40.0% ({today.year}-01-01)" in tr.findings_text
    assert f.look_backs == [{"indicator": tr.stat_result["indicator"], "chosen_points": 1,
                             "date_from": look_back_from, "date_to": date_to}]
    ctx = findings_to_context(f)
    assert f"PERIOD ANALYSED: {date_from} to {date_to}" in ctx
    assert (f"LONGER LOOK-BACK: the chosen period holds too few observations for a trend for "
            f"{tr.stat_result['indicator']} (1 observation); its trend is computed over "
            f"{look_back_from} to {date_to}.") in ctx
    assert not [g for g in f.gaps if "trend" in g]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _yearly_ipc_rows(ep))
def test_a_period_with_enough_points_is_not_extended(_mock):
    from datetime import date
    y = date.today().year
    f = compute_findings("AFG", f"{y - 4}-01-01", None, language="en")
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    assert tr.stat_result["look_back"] is None and f.look_backs == []
    assert "look-back" not in tr.findings_text.lower()
    assert "LONGER LOOK-BACK" not in findings_to_context(f)


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _yearly_ipc_rows(ep, years_back=2))
def test_no_chosen_period_is_never_extended(_mock):
    f = compute_findings("AFG", None, None, language="en")
    assert f.look_backs == []
    assert not [s for s in f.sections if s.stat_result["kind"] == "trend"]


def _ten_year_idp_rows(ep):
    # Two regions, one DTM round a year for ten years: the chosen year holds one round.
    if not ep.endswith("idps"):
        return []
    from datetime import date
    y = date.today().year
    return [{"population": base + 10 * k, "admin1_name": region, "operation": "Overview",
             "reference_period_start": f"{y - 9 + k}-01-01"}
            for k in range(10) for region, base in (("North", 1000), ("South", 500))]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _ten_year_idp_rows(ep))
def test_the_regional_ranking_stays_on_the_chosen_period(_mock):
    date_from, date_to = _last_year()
    f = compute_findings("AFG", date_from, date_to, language="en")
    region = next(s for s in f.sections if s.stat_result["kind"] == "region")
    assert dict(region.stat_result["ranking"]) == {"North": 1090.0, "South": 590.0}


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _two_indicator_rows(
    ep, [f"{y}-{m:02d}-01" for y in range(__import__('datetime').date.today().year - 4,
                                           __import__('datetime').date.today().year + 1)
         for m in (1, 2)]))
def test_look_back_series_are_not_correlated(_mock):
    # Correlations need eight common periods inside the chosen period; a look-back
    # extends a trend, it does not widen the report's other tests.
    date_from, date_to = _last_year()
    f = compute_findings("AFG", date_from, date_to, language="en")
    assert f.look_backs
    assert not [s for s in f.sections if s.stat_result["kind"] == "correlation"]


# --- A series too short for any trend (HNO sector figures start in 2024) is reported
# as its values, never only as a gap line: the sector's headline figure must reach
# the report. ---

def _three_year_pin_rows(ep, params):
    if params.get("sector_code") != "FSC":
        return []
    from datetime import date
    y = date.today().year
    return [{"population": v, "category": "", "reference_period_start": f"{y - k}-01-01",
             "reference_period_end": f"{y - k}-12-31"}
            for k, v in ((2, 15_823_677), (1, 14_764_729), (0, 17_412_653))]


def test_a_series_too_short_for_a_trend_is_reported_as_its_values(monkeypatch):
    from datetime import date
    y = date.today().year
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _three_year_pin_rows))
    date_from, date_to = _last_year()
    f = compute_findings("AFG", date_from, date_to, language="en", theme="Food and Nutrition")
    snap = next(s for s in f.sections if s.stat_result["kind"] == "snapshot")
    assert snap.heading == "Food security: people in need — Latest Values"
    assert snap.stat_result["p_value"] is None and snap.chart and snap.chart_dark
    text = snap.findings_text
    assert "3 observations" in text and "too few for a trend test" in text
    assert "no trend or statistical test is reported" in text
    assert (f"Values: {y - 2}-01-01 15800000 people; {y - 1}-01-01 14800000 people; "
            f"{y}-01-01 17400000 people.") in text
    assert f"Latest value as of the chosen period: 17400000 people ({y}-01-01)." in text
    # The chosen year held one of the three values: the window is named.
    assert "the values cover" in text and date_from in text
    assert "SIGNIFICANT" not in text and "p=" not in text
    assert any("(n=3)" in g for g in f.gaps)               # still listed as a data gap
    assert f.indicators_covered == ["pin_food_security"]


def test_turkish_snapshot_heading(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _three_year_pin_rows))
    f = compute_findings("AFG", None, None, language="tr", theme="Food and Nutrition")
    assert [s.heading for s in f.sections] == [
        "Gıda güvenliği: insani yardıma ihtiyaç duyan kişiler — Son Değerler"]


def test_snapshots_do_not_count_toward_the_holm_family(monkeypatch):
    def rows(ep, params):
        return _three_year_pin_rows(ep, params) or _yearly_ipc_rows(ep)
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], rows))
    f = compute_findings("AFG", None, None, language="en", theme="Food and Nutrition")
    kinds = sorted(s.stat_result["kind"] for s in f.sections)
    assert kinds == ["snapshot", "trend"]
    trend_section = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    # One test in the family: its Holm-adjusted p is its own p.
    assert trend_section.stat_result["p_adjusted"] == trend_section.stat_result["p_value"]
    assert "Holm correction across all 1 tests" in findings_to_context(f)


# --- Untestable comparisons are snapshots, not negative results (2026-11-18: "H of n/a,
# a p-value of n/a … the difference between regions is not statistically significant"). ---

def _one_round_idp_rows(ep):
    if not ep.endswith("idps"):
        return []
    from datetime import date
    y = date.today().year
    return [{"population": v, "admin1_name": r, "reference_period_start": f"{y}-03-31"}
            for r, v in (("Herat", 443_000), ("Balkh", 363_000), ("Kabul", 310_000),
                         ("Kandahar", 120_000))]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _one_round_idp_rows(ep))
def test_an_untestable_regional_comparison_is_a_ranking_snapshot(_mock):
    from datetime import date
    y = date.today().year
    f = compute_findings("AFG", f"{y}-01-01", None, language="en")
    region = next(s for s in f.sections if s.stat_result["kind"] == "region")
    text = region.findings_text
    assert text == (
        f"Internally displaced people (IDPs): ranking snapshot as of {y}-03-31 — highest "
        "regions: Herat (443000), Balkh (363000), Kabul (310000); a statistical comparison "
        "between regions was not possible: one observation per region.")
    assert region.stat_result["tested"] is False and region.stat_result["significant"] is False
    ctx = findings_to_context(f)
    assert "No statistical test was possible" in ctx and "Holm correction" not in ctx


def test_a_partly_testable_regional_comparison_names_why():
    from analytics.technical_report import _region_text
    text = _region_text({"indicator": "IDPs", "ranking": [("A", 10.0), ("B", 5.0)],
                         "p_value": None, "kruskal_h": None, "max_obs": 2,
                         "first_period": "2025-01-01", "last_period": "2025-07-01"})
    assert text == ("IDPs: ranking snapshot, mean per region over 2025-01-01 to 2025-07-01 — "
                    "highest regions: A (10.0), B (5.00); a statistical comparison between "
                    "regions was not possible: fewer than two regions have two or more "
                    "observations.")


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _multi_region_rows(
    "idps" if ep.endswith("idps") else "other"))
def test_a_tested_regional_comparison_keeps_its_verdict(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31", language="en")
    region = next(s for s in f.sections if s.stat_result["kind"] == "region")
    assert region.stat_result["tested"] is True
    assert "Kruskal-Wallis H=" in region.findings_text and "(α=0.05)" in region.findings_text


def test_all_sectors_reports_keep_short_series_as_gaps_only(monkeypatch):
    # "All sectors" stays as it was (its output is pinned byte for byte): a series too
    # short for a trend is a data gap there, not a Latest Values section.
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], lambda ep, p: _three_year_pin_rows(
                            ep, {"sector_code": "FSC"}) if p.get("sector_code") == "Intersectoral" else []))
    f = compute_findings("AFG", None, None, language="en", theme=None)
    assert f.sections == []
    assert any("(n=3)" in g for g in f.gaps)


# --- Review 2026-11-18: AFG IPC 3+ read "relative change along the trend line … =-48.3%"
# beside a latest value of 32.0% (observed 47% → 32%): a relative change of a percentage,
# measured to the end of a Sen line. Shares now change in percentage points, and every
# trend gives its observed first and latest values. ---

def _afg_ipc_rows(ep):
    if "food-security" not in ep:
        return []
    shares = [("2022-03-01", .47), ("2022-09-01", .41), ("2023-04-01", .40), ("2023-10-01", .29),
              ("2024-03-01", .32), ("2024-09-01", .25), ("2025-03-01", .27), ("2025-09-01", .28),
              ("2026-09-01", .32)]
    return [{"reference_period_start": p, "reference_period_end": p, "population_in_phase": 1,
             "population_fraction_in_phase": f} for p, f in shares]


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _afg_ipc_rows(ep))
def test_a_share_trend_changes_in_percentage_points_with_observed_values(_mock):
    f = compute_findings("AFG", "2022-01-01", "2026-11-18", language="en")
    tr = next(s for s in f.sections if s.stat_result["kind"] == "trend")
    r = tr.stat_result
    span = (__import__("datetime").date(2026, 9, 1) - __import__("datetime").date(2022, 3, 1)).days / 365.25
    assert abs(r["line_change"] - r["slope"] * span) < 1e-9
    text = tr.findings_text
    assert f"change along the trend line 2022-03-01 → 2026-09-01={r['line_change']:+.1f} percentage points" in text
    assert "relative change" not in text
    assert "observed first value 47.0% (2022-03-01), latest value 32.0% (2026-09-01)" in text


@patch("analytics.technical_report.fetch_rows", side_effect=lambda ep, iso3, **k: _sudan_like_idp_rows(ep))
def test_a_count_trend_keeps_its_relative_change_and_gives_observed_values(_mock):
    tr = next(s for s in compute_findings("SDN", None, None, language="en").sections
              if s.stat_result["kind"] == "trend")
    assert "relative change along the trend line" in tr.findings_text
    assert "observed first value 8000 people (" in tr.findings_text
    assert "latest value 8300 people (" in tr.findings_text
    assert tr.stat_result["line_change"] is None


# --- Review 2026-11-18, minor items. ---

def test_a_constant_series_says_its_values_do_not_vary(monkeypatch):
    def rows(ep, params):
        if params.get("sector_code") != "NUT":
            return []
        return [{"population": 7_000_000, "category": "", "reference_period_start": f"{y}-01-01",
                 "reference_period_end": f"{y}-12-31"} for y in (2021, 2022, 2023, 2024, 2025)]
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], rows))
    f = compute_findings("AFG", "2021-01-01", None, language="en", theme="Food and Nutrition")
    text = next(s for s in f.sections if s.stat_result["kind"] == "snapshot").findings_text
    assert "5 observations from 2021-01-01 to 2025-01-01 — the values do not vary" in text
    assert "too few" not in text


def test_a_report_of_snapshots_only_names_no_test_methods(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _three_year_pin_rows))
    ctx = findings_to_context(compute_findings("AFG", None, None, language="en",
                                               theme="Food and Nutrition"))
    assert "- No statistical test was possible: every finding is reported as its observed values." in ctx
    for ran_never in ("Holm correction", "Kruskal-Wallis", "Pearson", "Mann-Kendall"):
        assert ran_never not in ctx


def test_fetch_failures_are_recorded_apart_from_missing_data():
    def fetch(ep, iso3, **k):
        raise requests.exceptions.ConnectionError("down")
    with patch("analytics.technical_report.fetch_rows", side_effect=fetch):
        f = compute_findings("AFG", None, None, language="en", theme="Food and Nutrition")
    assert f.failed == ["pin_food_security", "pin_nutrition", "food_security"]
    with patch("analytics.technical_report.fetch_rows", side_effect=lambda *a, **k: []):
        assert compute_findings("AFG", None, None, theme="Food and Nutrition").failed == []


def _dtm_rows_with_an_old_partial_round(ep):
    # Chosen year: two operations (one is left out). Look-back years: one round covers
    # only two of ten regions (left out). The two windows leave out different things.
    if not ep.endswith("idps"):
        return []
    from datetime import date
    y = date.today().year
    regions = [f"R{i}" for i in range(10)]
    rows = [{"operation": "Overview", "admin1_name": r, "population": 100 + k,
             "reference_period_start": f"{y - 4 + k}-01-01"} for k in range(5) for r in regions]
    rows += [{"operation": "Overview", "admin1_name": r, "population": 50,
              "reference_period_start": f"{y - 3}-06-01"} for r in regions[:2]]
    rows += [{"operation": "Flood", "admin1_name": r, "population": 7,
              "reference_period_start": f"{y}-01-01"} for r in regions[:3]]
    return rows


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _dtm_rows_with_an_old_partial_round(ep))
def test_look_back_keeps_the_chosen_period_notes_too(_mock):
    date_from, date_to = _last_year()
    f = compute_findings("AFG", date_from, date_to, language="en")
    lb = f.look_backs[0]
    name = "Internally displaced people (IDPs)"
    chosen = [n for n in f.notes if n.startswith(f"{name} (chosen period {date_from} to {date_to}): ")]
    looked = [n for n in f.notes if n.startswith(f"{name} (trend look-back {lb['date_from']} to {date_to}): ")]
    assert chosen and "1 other operation(s)" in chosen[0]
    assert looked and "incomplete round(s)" in looked[0]


# --- Round 2 (owner): "it would be good if the other reports had sources too". A
# technical report lists the HDX HAPI series it used. ---

def _sourced_rows(ep, params):
    if params.get("sector_code") == "FSC":
        return [{"population": v, "category": "", "resource_hdx_id": f"hno-{y}",
                 "reference_period_start": f"{y}-01-01", "reference_period_end": f"{y}-12-31"}
                for y, v in ((2024, 15_823_677), (2025, 14_764_729), (2026, 17_412_653))]
    return []


def test_findings_record_each_series_used_for_the_sources(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], _sourced_rows))
    f = compute_findings("AFG", "2021-01-01", "2026-11-18", language="en",
                         theme="Food and Nutrition")
    assert f.data_sources == [{
        "key": "pin_food_security", "title": "Food security: people in need",
        "source": "OCHA HNO", "first_period": "2024-01-01", "last_period": "2026-01-01",
        "resource_hdx_id": "hno-2026"}]


def test_data_sources_are_listed_like_report_sources(monkeypatch):
    from analytics.technical_report import data_sources
    f = Findings(sections=[], gaps=[], indicators_covered=["pin_food_security", "idps"],
                 data_sources=[
                     {"key": "pin_food_security", "title": "Food security: people in need",
                      "source": "OCHA HNO", "first_period": "2024-01-01",
                      "last_period": "2026-01-01", "resource_hdx_id": "hno-2026"},
                     {"key": "idps", "title": "Internally displaced people (IDPs)",
                      "source": "International Organization for Migration (IOM), January 2026, "
                                "Displacement Tracking Matrix (DTM), https://dtm.iom.int",
                      "first_period": "2026-01-31", "last_period": "2026-01-31",
                      "resource_hdx_id": "dtm-1"}])
    meta = {"hno-2026": {"dataset_hdx_stub": "global-hpc-hno",
                         "dataset_hdx_title": "Global Humanitarian Programme Cycle, Humanitarian Needs"}}
    monkeypatch.setattr("analytics.technical_report.resource_metadata", lambda rid: meta.get(rid))
    assert data_sources(f, "Afghanistan", retrieved="2026-11-18") == [
        {"index": 1, "title": "Food security: people in need",
         "url": "https://data.humdata.org/dataset/global-hpc-hno", "source": "OCHA HNO",
         "date": "2026-01-01", "country": "Afghanistan", "doctype": "dataset",
         "dataset": "Global Humanitarian Programme Cycle, Humanitarian Needs",
         "period": "2024-01-01 – 2026-01-01", "retrieved": "2026-11-18"},
        {"index": 2, "title": "Internally displaced people (IDPs)",
         "url": "https://hapi.humdata.org/",
         "source": "International Organization for Migration (IOM), January 2026, "
                   "Displacement Tracking Matrix (DTM), https://dtm.iom.int",
         "date": "2026-01-31", "country": "Afghanistan", "doctype": "dataset",
         "period": "2026-01-31", "retrieved": "2026-11-18"},
    ]


# --- Round 2 decision: a parent sector's figure is named for the plan line it is. ---

def _protection_rows(parent, subs, years=(2025,)):
    def rows(ep, params):
        if params.get("sector_code") != "PRO":
            return []
        out = []
        for y in years:
            for cat, v in parent[y]:
                out.append({"sector_code": "PRO", "sector_name": "Protection", "population": v,
                            "category": cat, "resource_hdx_id": "r",
                            "reference_period_start": f"{y}-01-01",
                            "reference_period_end": f"{y}-12-31"})
            for code, name, v in subs.get(y, []):
                out.append({"sector_code": code, "sector_name": name, "population": v,
                            "category": "", "reference_period_start": f"{y}-01-01",
                            "reference_period_end": f"{y}-12-31"})
        return out
    return rows


def test_a_sector_without_sub_lines_has_no_plan_line_note(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _three_year_pin_rows))
    f = compute_findings("AFG", None, None, language="en", theme="Food and Nutrition")
    assert f.sections[0].heading == "Food security: people in need — Latest Values"
    assert not [n for n in f.notes if "separate lines" in n]


def test_a_source_period_has_no_english_word_in_a_turkish_report(monkeypatch):
    from analytics.technical_report import data_sources
    f = Findings(sections=[], gaps=[], indicators_covered=["food_security"], data_sources=[
        {"key": "food_security", "title": "Gıda güvensizliği", "source": "IPC",
         "first_period": "2022-03-01", "last_period": "2026-09-01", "resource_hdx_id": None}])
    monkeypatch.setattr("analytics.technical_report.resource_metadata", lambda rid: None)
    assert data_sources(f, "Afganistan", retrieved="2026-11-18")[0]["period"] == "2022-03-01 – 2026-09-01"


# --- Round 2 final (Critical): HAPI's rows cannot tell the plan's general protection line
# from another line (Haiti 2024: PRO = 250,000 in both rows is "Protection des migrants";
# the general line is 425,592, the total 1,595,141), so a protection figure is never called
# "general". Built from HAPI's real rows; published figures from the plans:
# HTI 2025 general 466,589, migrants 349,999, overall 2,160,007; AFG 2025 general
# 14,213,777, overall 22,258,295; COD 2025 overall 7,870,319; SDN 2025 general 11,725,110
# (no overall line). ---

_HERE = Path(__file__).parent
_REAL_2025 = json.loads((_HERE / "hapi_protection_2025.json").read_text(encoding="utf-8"))
_REAL_HTI_2024 = json.loads((_HERE / "hapi_protection_hti_2024.json").read_text(encoding="utf-8"))


def _real_protection(iso3, date_from="2025-01-01", date_to="2025-12-31", language="en",
                     with_hti_2024=False):
    rows = list(_REAL_2025.get(iso3, [])) + (_REAL_HTI_2024 if with_hti_2024 else [])

    def fetch(ep, i3, **k):
        return rows if (k.get("extra_params") or {}).get("sector_code") == "PRO" else []
    with patch("analytics.technical_report.fetch_rows", side_effect=fetch):
        return compute_findings(iso3, date_from, date_to, language=language,
                                theme="Protection and Human Rights")


def _protection_section(f):
    return next(s for s in f.sections if "people in need" in s.heading or "ihtiyaç" in s.heading)


_NOT_ADDED = "this report does not add the lines up, because people can be counted in more than one."


def test_haiti_2024_the_migrants_line_is_not_called_general():
    rows = _REAL_HTI_2024

    def fetch(ep, i3, **k):
        return rows if (k.get("extra_params") or {}).get("sector_code") == "PRO" else []
    with patch("analytics.technical_report.fetch_rows", side_effect=fetch):
        f = compute_findings("HTI", "2024-01-01", "2024-12-31", language="en",
                             theme="Protection and Human Rights")
    sec = _protection_section(f)
    assert sec.heading == "Protection: people in need — Latest Values"
    assert "Values: 2024-01-01 250000 people." in sec.findings_text
    assert [n for n in f.notes if "separate lines" in n] == [
        "Protection: people in need, 2024: the plan reports protection in separate lines "
        "(Child Protection 1,253,982, Gender Based Violence 1,171,183); this figure (250,000) is "
        "below one of the plan's protection lines, so it is not the plan's overall protection "
        "figure; HDX HAPI does not say which of the plan's lines it is; " + _NOT_ADDED]
    assert f.data_sources[0]["title"] == "Protection: people in need"


def test_haiti_2025_prints_466589_and_its_look_back_is_not_comparable():
    f = _real_protection("HTI", with_hti_2024=True)
    sec = _protection_section(f)
    assert sec.heading == "Protection: people in need — Latest Values"
    assert "Values: 2024-01-01 250000 people; 2025-01-01 467000 people." in sec.findings_text
    assert ("the values are not comparable across years (2024, 2025: one of the plan's separate "
            "protection lines, not its overall figure; HDX HAPI does not say which line each "
            "year's figure is), so no trend or statistical test is reported") in sec.findings_text
    notes = [n for n in f.notes if "separate lines" in n]
    assert notes[1] == (
        "Protection: people in need, 2025: the plan reports protection in separate lines (Child "
        "Protection 1,611,291, Gender Based Violence 1,535,819); this figure (466,589) is below one "
        "of the plan's protection lines, so it is not the plan's overall protection figure; HDX HAPI "
        "does not say which of the plan's lines it is; " + _NOT_ADDED)
    assert ("Protection: people in need: HDX HAPI holds two totals for 2025: 349,999 without a "
            "breakdown and 466,589 as the total of its breakdown (used); the HNO's published "
            "sector figure may differ") in f.notes


def test_sudan_2025_is_not_called_general_and_claims_nothing_about_an_unpublished_total():
    for language, heading in (("en", "Protection: people in need — Latest Values"),
                              ("tr", "Koruma: insani yardıma ihtiyaç duyan kişiler — Son Değerler")):
        f = _real_protection("SDN", language=language)
        assert _protection_section(f).heading == heading
    f = _real_protection("SDN")
    assert "Values: 2025-01-01 11700000 people." in _protection_section(f).findings_text
    note = next(n for n in f.notes if "separate lines" in n)
    assert ("this figure (11,725,110) is below one of the plan's protection lines, so it is not the "
            "plan's overall protection figure; HDX HAPI does not say which of the plan's lines it "
            "is;") in note
    assert "higher" not in note and "general" not in note


def test_afghanistan_and_congo_2025_may_be_one_of_the_lines():
    for iso3, figure, full in (("AFG", "14200000", "14,213,777"), ("COD", "7870000", "7,870,319")):
        f = _real_protection(iso3)
        sec = _protection_section(f)
        assert sec.heading == "Protection: people in need — Latest Values", iso3
        assert f"Values: 2025-01-01 {figure} people." in sec.findings_text, iso3
        note = next(n for n in f.notes if "separate lines" in n)
        assert (f"this figure ({full}) may be one of them rather than the overall protection "
                f"figure; " + _NOT_ADDED) in note, iso3
        assert "general" not in note and "higher" not in note, iso3


def test_no_general_name_anywhere():
    for iso3 in ("HTI", "AFG", "COD", "SDN"):
        for language in ("en", "tr"):
            f = _real_protection(iso3, language=language, with_hti_2024=iso3 == "HTI")
            text = " ".join([s.heading + " " + s.findings_text for s in f.sections] + f.notes
                            + [d["title"] for d in f.data_sources])
            assert "eneral protection" not in text and "Genel koruma" not in text, (iso3, language)


# --- Years not comparable: only protection years without sub-lines are comparable. ---

def _afg_like_rows():
    return _protection_rows({2024: [("", 14_809_904)], 2025: [("", 14_213_777)],
                             2026: [("", 14_988_378)]},
                            {2024: [("PRO-CPN", "Child Protection", 9_213_752)],
                             2025: [("PRO-CPN", "Child Protection", 9_352_775)]},
                            years=(2024, 2025, 2026))


def test_a_series_mixing_plan_lines_and_single_figures_says_so_in_its_section(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], _afg_like_rows()))
    f = compute_findings("AFG", None, None, language="en", theme="Protection and Human Rights")
    sec = f.sections[0]
    assert sec.stat_result["kind"] == "snapshot" and sec.stat_result["p_value"] is None
    assert ("Protection: people in need: 3 observations from 2024-01-01 to 2026-01-01 — the values "
            "are not comparable across years (2024, 2025: possibly one of the plan's separate "
            "protection lines rather than its overall figure; 2026: the plan's only protection "
            "figure; HDX HAPI does not say which line each year's figure is), so no trend or "
            "statistical test is reported.") in sec.findings_text


def test_no_trend_is_tested_across_years_that_are_not_comparable(monkeypatch):
    # Five years, enough for a trend, but 2022-2023 single figures and 2024-2026 lines.
    parent = {y: [("", 10_000_000 + 100_000 * k)] for k, y in enumerate(range(2022, 2027))}
    subs = {y: [("PRO-GBV", "Gender Based Violence", 20_000_000)] for y in (2024, 2025, 2026)}
    rows = _protection_rows(parent, subs, years=tuple(range(2022, 2027)))
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], rows))
    f = compute_findings("AFG", "2021-01-01", None, language="en", theme="Protection and Human Rights")
    assert [s.stat_result["kind"] for s in f.sections] == ["snapshot"]
    assert ("the values are not comparable across years (2022, 2023: the plan's only protection "
            "figure; 2024, 2025, 2026: one of the plan's separate protection lines, not its overall "
            "figure; HDX HAPI does not say which line each year's figure is)") in f.sections[0].findings_text
    assert "No statistical test was possible" in findings_to_context(f)


def test_years_that_all_have_sub_lines_are_not_comparable_either(monkeypatch):
    rows = _protection_rows({2024: [("", 14_809_904)], 2025: [("", 14_213_777)]},
                            {2024: [("PRO-CPN", "Child Protection", 9_213_752)],
                             2025: [("PRO-CPN", "Child Protection", 9_352_775)]},
                            years=(2024, 2025))
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], rows))
    f = compute_findings("AFG", None, None, language="en", theme="Protection and Human Rights")
    assert "not comparable across years (2024, 2025: possibly one of" in f.sections[0].findings_text


def test_years_without_sub_lines_stay_comparable(monkeypatch):
    rows = _protection_rows({2025: [("", 2_195_026)], 2026: [("", 2_300_000)]}, {}, years=(2025, 2026))
    monkeypatch.setattr("analytics.technical_report.fetch_rows", _recording_fetch([], rows))
    f = compute_findings("HTI", None, None, language="en", theme="Protection and Human Rights")
    assert "not comparable" not in f.sections[0].findings_text
    assert not [n for n in f.notes if "separate lines" in n]


def test_comparable_years_keep_the_usual_text(monkeypatch):
    monkeypatch.setattr("analytics.technical_report.fetch_rows",
                        _recording_fetch([], _three_year_pin_rows))
    f = compute_findings("AFG", None, None, language="en", theme="Food and Nutrition")
    assert "not comparable" not in f.sections[0].findings_text



# --- Review of round 2 (minor). ---

def test_data_sources_do_not_ask_twice_for_a_failed_lookup(monkeypatch):
    from analytics.technical_report import data_sources
    calls = []
    monkeypatch.setattr("analytics.technical_report.resource_metadata",
                        lambda rid: calls.append(rid) or None)
    used = {"source": "OCHA HNO", "first_period": "2024-01-01", "last_period": "2026-01-01",
            "resource_hdx_id": "same"}
    f = Findings(sections=[], gaps=[], indicators_covered=["a", "b"], data_sources=[
        {"key": "a", "title": "A", **used}, {"key": "b", "title": "B", **used}])
    assert len(data_sources(f, "Afghanistan", retrieved="2026-11-18")) == 2
    assert calls == ["same"]


def test_an_indicator_whose_analysis_failed_is_not_a_source():
    def side(ep, iso3, **k):
        return _multi_region_rows("idps") if ep.endswith("idps") else []
    with patch("analytics.technical_report.by_region", side_effect=ValueError("boom")), \
         patch("analytics.technical_report.fetch_rows", side_effect=side):
        f = compute_findings("AFG", "2025-01-01", "2025-12-31", language="en")
    assert any("analiz hatası" in g for g in f.gaps)
    assert [u["key"] for u in f.data_sources] == []
