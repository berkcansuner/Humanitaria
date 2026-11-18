"""Model-generated report content must not inject raw HTML into the PDF renderer
(security audit run-1: a <style> @font-face block replaced reportlab's
process-wide 'vera' font mapping for every later export)."""
import base64

from rag.report_pdf import _body_html, render_report_pdf


def test_raw_html_in_report_content_is_escaped():
    out = _body_html("## Summary\n\n<style>p{color:red}</style>\n\nText <b onclick=x>bold</b> [1].")
    assert "<style>" not in out and "<b " not in out
    assert "&lt;style&gt;" in out
    assert '<span class="cite">[1]</span>' in out   # markdown + citation styling still work


def test_markdown_tables_and_lists_still_render():
    out = _body_html("| A | B |\n|---|---|\n| 1 | 2 |\n\n- x\n- y")
    assert "<table>" in out and "<li>x</li>" in out


def test_font_face_in_content_does_not_touch_global_font_mapping():
    from reportlab.lib.fonts import tt2ps
    import os
    import reportlab
    ttf = open(os.path.join(os.path.dirname(reportlab.__file__), "fonts", "VeraBd.ttf"), "rb").read()
    payload = ("<style>@font-face { font-family: Vera; src: url(data:font/ttf;base64,"
               + base64.b64encode(ttf).decode() + "); }</style>\n\nHello")
    render_report_pdf({"country": "Sudan", "content": payload, "sources": None})
    assert tt2ps("vera", 0, 0) == "Vera"


def test_old_saved_reports_print_adjacent_citations_in_order():
    out = _body_html("Lean season [5][2]. Assistance [3][1].")
    assert '<span class="cite">[2]</span><span class="cite">[5]</span>' in out
    assert '<span class="cite">[1]</span><span class="cite">[3]</span>' in out


def test_citations_one_space_apart_print_in_order():
    out = _body_html("Lean season [5] [2].")
    assert '<span class="cite">[2]</span> <span class="cite">[5]</span>' in out


def test_pdf_lists_a_technical_report_data_source():
    from rag.report_pdf import _sources_rows
    rows = _sources_rows([{"index": 1, "title": "Food security: people in need",
                           "url": "https://data.humdata.org/dataset/global-hpc-hno",
                           "source": "OCHA HNO", "date": "2026-01-01", "doctype": "dataset",
                           "period": "2024-01-01 – 2026-01-01", "retrieved": "2026-11-18"}])
    assert "Food security: people in need" in rows
    assert "OCHA HNO · 2024-01-01 – 2026-01-01 · retrieved 2026-11-18" in rows
    assert "https://data.humdata.org/dataset/global-hpc-hno" in rows


def test_a_turkish_pdf_names_the_retrieval_day_in_turkish():
    from rag.report_pdf import _sources_rows
    rows = _sources_rows([{"index": 1, "title": "t", "url": "https://data.humdata.org/dataset/x",
                           "source": "IPC", "doctype": "dataset", "period": "2022-03-01 – 2026-09-01",
                           "retrieved": "2026-11-18"}], "tr")
    assert "IPC · 2022-03-01 – 2026-09-01 · erişim tarihi 2026-11-18" in rows



def test_a_technical_pdf_cover_counts_sources_not_source_reports():
    from rag.report_pdf import _cover_count_label
    assert _cover_count_label("technical_monitoring", "en") == "Sources"
    assert _cover_count_label("technical_monitoring", "tr") == "Kaynaklar"
    assert _cover_count_label("situation", "en") == "Source reports"
    assert _cover_count_label(None, "tr") == "Kaynak raporlar"
