"""A report's fixed labels follow the REPORT's language end to end: the PDF, the
technical report's headings and chart text, and the "What changed" fallback. English
stays as it was; a language other than en/tr keeps falling back to English labels."""
import io
from unittest.mock import patch

import pytest
from pypdf import PdfReader

from analytics import technical_report
from analytics.indicators import INDICATORS, by_key
from rag.report_compare import remove_sentences
from rag.report_pdf import render_report_pdf

_SOURCES = [{"index": 1, "title": "Sudan: Access Snapshot", "url": "https://reliefweb.int/r/1",
             "source": "OCHA", "date": "2026-10-21"}]


def _pdf_text(report: dict) -> str:
    reader = PdfReader(io.BytesIO(render_report_pdf(report)))
    # pypdf extracts some lines with spaces between words collapsed; normalise them.
    return " ".join(" ".join(p.extract_text().split()) for p in reader.pages)


def _report(language, **extra):
    return {"country": "Sudan", "theme": "Health", "date_from": "2026-08-01",
            "date_to": "2026-10-31", "content": "## Özet\n\nMetin [1].", "sources": _SOURCES,
            "report_type": "situation", "language": language, **extra}


class TestPdfLabels:
    def test_turkish_pdf_has_turkish_labels_and_no_english_ones(self):
        text = _pdf_text(_report("tr"))
        assert "İzleme ve Değerlendirme (M&E) Durum Raporu" in text
        assert "Kaynaklar" in text
        assert "Sağlık" in text                       # the sector, in the report language
        assert "01.08.2026 – 31.10.2026" in text      # the period, written the Turkish way
        for label in ("Dönem", "Sektörler", "Kaynak raporlar", "Oluşturma tarihi", "Sayfa"):
            assert label in text
        for english in ("Sources", "Situation Report", "Period", "Sectors", "Generated",
                        "Page", "Health"):
            assert english not in text
        # Source titles and publishers are never translated.
        assert "Sudan: Access Snapshot" in text and "OCHA" in text

    def test_turkish_pdf_names_all_sectors_and_each_report_type_in_turkish(self):
        text = _pdf_text(_report("tr", theme=None, report_type="technical_monitoring"))
        assert "Teknik İzleme Raporu" in text and "Tüm sektörler" in text
        assert "All sectors" not in text

    def test_turkish_pdf_spells_the_generation_date_with_a_turkish_month(self):
        import datetime as real

        class Fixed(real.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 18, 12, 0, tzinfo=tz)

        with patch("rag.report_pdf.datetime", Fixed):
            assert "18 Kasım 2026" in _pdf_text(_report("tr"))
            assert "18 Nov 2026" in _pdf_text(_report("en"))

    def test_english_pdf_keeps_its_english_labels(self):
        text = _pdf_text(_report("en", content="## Summary\n\nText [1]."))
        assert "M&E Situation Report" in text and "Sources" in text and "Health" in text
        assert "Kaynaklar" not in text

    @pytest.mark.parametrize("language", ["fr", None, ""])
    def test_unknown_or_missing_language_falls_back_to_english(self, language):
        text = _pdf_text(_report(language, content="## Summary\n\nText [1]."))
        assert "Sources" in text and "Kaynaklar" not in text

    def test_every_form_sector_has_a_turkish_name(self):
        from api.routes.reports import THEMES
        from rag.report_pdf import _SECTORS_TR
        assert set(THEMES) <= set(_SECTORS_TR)

    def test_sector_names_match_the_interface(self):
        # The PDF and the interface name each sector the same way: the English
        # interface names are the form's themes, and each Turkish name is the PDF's.
        # (frontend/src/utils/reportTypes.test.js checks the frontend's theme keys.)
        import json
        from pathlib import Path
        from api.routes.reports import THEMES
        from rag.report_pdf import _SECTORS_TR
        locales = Path(__file__).resolve().parents[1] / "frontend" / "src" / "locales"
        en = json.loads((locales / "en.json").read_text(encoding="utf-8"))["reports"]["sectors"]
        tr = json.loads((locales / "tr.json").read_text(encoding="utf-8"))["reports"]["sectors"]
        assert sorted(en.values()) == sorted(THEMES)
        assert {theme: tr[key] for key, theme in en.items()} == _SECTORS_TR


def _syr_rows(ep, iso3, **_k):
    """Two regions of IDPs and an IPC share: trend + regional + correlation sections."""
    periods = [f"{y}-{m:02d}-01" for y in (2024, 2025) for m in (1, 4, 7, 10)]
    if ep.endswith("idps"):
        return [{"population": 1000 + 100 * i + (50 if r == "Aleppo" else 0),
                 "reference_period_start": p, "admin1_name": r, "admin1_code": r}
                for r in ("Aleppo", "Idlib") for i, p in enumerate(periods)]
    if ep.endswith("food-security"):
        return [{"population_fraction_in_phase": 0.30 + 0.01 * i, "reference_period_start": p,
                 "admin1_name": "Aleppo", "admin1_code": "Aleppo"}
                for i, p in enumerate(periods)]
    return []


class TestTechnicalReportLanguage:
    def _findings(self, language):
        calls = []

        def spy(name):
            def draw(*args, **kwargs):
                calls.append((name, args, kwargs))
                return "data:image/png;base64,AAA"
            return draw

        with patch("analytics.technical_report.fetch_rows", side_effect=_syr_rows), \
             patch("analytics.technical_report.trend_chart", spy("trend")), \
             patch("analytics.technical_report.comparison_chart", spy("region")), \
             patch("analytics.technical_report.correlation_chart", spy("correlation")):
            findings = technical_report.compute_findings("SYR", None, None, language=language)
        return findings, calls

    def test_turkish_sections_and_chart_text_are_turkish(self):
        findings, calls = self._findings("tr")
        headings = [s.heading for s in findings.sections]
        idps = "Ülke içinde yerinden edilmiş kişiler (IDP)"
        assert f"{idps} — Eğilim Analizi" in headings
        assert f"{idps} — Bölgesel Analiz" in headings
        assert any(h.startswith("Korelasyon — ") for h in headings)
        assert not any("Analysis" in h or "Correlation" in h for h in headings)
        trend_units = [kw["unit"] for name, _a, kw in calls if name == "trend"]
        assert "kişi" in trend_units and "people" not in trend_units
        assert all(kw["language"] == "tr" for _n, _a, kw in calls)
        assert all(kw["source"].startswith("Kaynak: ") for _n, _a, kw in calls)
        corr = next(kw for name, _a, kw in calls if name == "correlation")
        assert {corr["xlabel"], corr["ylabel"]} == {
            idps, "Gıda güvensizliği (IPC 3+, analiz edilen nüfusun yüzdesi)"}

    def test_english_sections_and_chart_text_stay_english(self):
        findings, calls = self._findings("en")
        headings = [s.heading for s in findings.sections]
        assert "Internally displaced people (IDPs) — Trend Analysis" in headings
        trend_units = [kw["unit"] for name, _a, kw in calls if name == "trend"]
        assert "people" in trend_units
        assert all(kw["source"].startswith("Source: ") for _n, _a, kw in calls)

    def test_turkish_indicator_names_follow_the_glossary(self):
        assert by_key("idps").name("tr") == "Ülke içinde yerinden edilmiş kişiler (IDP)"
        assert by_key("returnees").name("tr") == "Geri dönenler (kişi)"
        assert by_key("refugees").name("tr") == "Mülteciler (kişi)"
        assert by_key("funding").name("tr") == "İnsani yardım fonlaması (USD)"
        assert all(ind.name("en") == ind.label_en for ind in INDICATORS)

    def test_chart_numbers_use_turkish_typography(self):
        from analytics.charts import format_value
        assert format_value(45, "tr", percent=True) == "%45"
        assert format_value(8.6, "tr", percent=True) == "%8,6"
        assert format_value(2_500_000, "tr") == "2,5 mn"
        assert format_value(2_500_000, "en") == "2.5M"


@pytest.mark.parametrize("language,expected,foreign", [
    ("en", "No HDX HAPI country code (ISO3)", "bulunamadı"),
    ("tr", "HDX HAPI ülke kodu (ISO3) bulunamadı", "No HDX HAPI"),
])
def test_unknown_country_message_of_a_technical_report_follows_its_language(
        language, expected, foreign):
    from fastapi.testclient import TestClient
    from api.main import app
    from tests.test_reports_route import _parse_sse_events
    resp = TestClient(app).post("/reports/stream", json={
        "country": "Atlantis", "report_type": "technical_monitoring", "language": language})
    content = _parse_sse_events(resp.text)[0]["data"]["content"]
    assert expected in content and foreign not in content


def test_what_changed_fallback_follows_the_report_language():
    body = "Cases rose in 2025 [1]."
    assert remove_sentences(body, {1}, "tr").startswith("Kaynaklardan")
    assert remove_sentences(body, {1}, "en").startswith("No change")
    assert remove_sentences(body, {1}, "fr").startswith("No change")
