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
    assert all(set(d.keys()) == {"heading", "image"} for d in imgs)
    assert all(d["image"].startswith("data:image/png;base64,") for d in imgs)


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

    assert any("idps" in g or "Yerinden edilmiş" in g for g in f.gaps)
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
    assert "=+" in tr.findings_text and "%, n=" in tr.findings_text
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
