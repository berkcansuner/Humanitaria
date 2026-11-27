"""A report's fixed labels follow the REPORT's language in its PDF. English stays as it
was; a language other than en/tr keeps falling back to English labels."""
import io
from unittest.mock import patch

import pytest
from pypdf import PdfReader

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
        text = _pdf_text(_report("tr", theme=None, report_type="needs_assessment"))
        assert "İhtiyaç Değerlendirmesi Özeti" in text and "Tüm sektörler" in text
        assert "All sectors" not in text

    def test_the_generation_date_is_day_month_year_in_both_languages(self):
        import datetime as real

        class Fixed(real.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 18, 12, 0, tzinfo=tz)

        with patch("rag.report_pdf.datetime", Fixed):
            for language in ("tr", "en"):
                text = _pdf_text(_report(language))
                assert "18.11.2026" in text
                assert "2026-08-01" not in text and "01.08.2026" in text      # the period too
            assert "Generated from ReliefWeb reports by Humanitaria" in _pdf_text(_report("en"))

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
