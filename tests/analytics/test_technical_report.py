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


def _two_indicator_rows(ep):
    # idps ve food_security için ortak dönemli, ilişkili iki seri → korelasyon.
    base = {
        "idps": [(100, "2025-01-01"), (200, "2025-04-01"), (300, "2025-07-01"),
                 (400, "2025-10-01")],
        "food_security": [(120, "2025-01-01"), (240, "2025-04-01"), (360, "2025-07-01"),
                          (480, "2025-10-01")],
    }
    key = "idps" if ep.endswith("idps") else ("food_security" if "food-security" in ep else None)
    if key is None:
        return []
    return [{"population": v, "reference_period_start": p, "admin1_name": "North",
             "admin1_code": "AF01"} for v, p in base[key]]


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _two_indicator_rows(ep))
def test_correlation_section_for_two_indicators(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31")
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


# --- FIX I3: filtre alanı (örn. population_status) veride yoksa unfiltered toplam
# yerine gap'e düşmeli — double-counting koruması sessizce devre dışı kalmamalı. ---

def _humanitarian_needs_rows_without_filter_column(ep):
    if not ep.endswith("humanitarian-needs"):
        return []
    return [
        {"population": v, "reference_period_start": p, "admin1_name": "North",
         "admin1_code": "AF01"}   # population_status YOK
        for v, p in [(1000, "2025-01-01"), (2000, "2025-04-01"),
                     (3000, "2025-07-01"), (4000, "2025-10-01")]
    ]


@patch("analytics.technical_report.fetch_rows",
       side_effect=lambda ep, iso3, **k: _humanitarian_needs_rows_without_filter_column(ep))
def test_missing_filter_column_becomes_gap_not_unfiltered_sum(_mock):
    f = compute_findings("AFG", "2025-01-01", "2025-12-31")
    assert "humanitarian_needs" not in f.indicators_covered
    assert any("population_status" in g for g in f.gaps)
    # Hiçbir bölüm İnsani ihtiyaç indikatörü için üretilmemeli (unfiltered sum yok):
    assert not any(s.stat_result.get("indicator") == "İnsani ihtiyaç (kişi)" for s in f.sections)
