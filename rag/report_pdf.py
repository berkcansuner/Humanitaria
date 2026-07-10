"""Render a saved M&E situation report to a styled, brand-green PDF.

Pure-Python (xhtml2pdf / reportlab) — no system libraries, so it builds on the
slim image and runs identically on Windows. Bitstream Vera (shipped with
reportlab) is registered as the document font: it covers full Turkish
(ç ş ğ ı İ ö ü …), which the reportlab default (Helvetica / Latin-1) does not.
"""
import html
import io
import logging
import os
import re
from datetime import datetime, timezone

import markdown as _markdown
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


# 1x1 transparent GIF — the inline stand-in for any blocked resource.
_BLANK_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


def _block_external_resources(uri, rel=None):
    """xhtml2pdf link_callback (see pisaFileObject.__init__: a truthy return REPLACES the
    original uri, a falsy one keeps it). Replace ANY http/https/file/relative resource URI
    with an inline 1x1 transparent data: image so LLM-generated report content can never
    trigger a server-side fetch (SSRF) or a local file read during PDF rendering — this
    covers both <img src> and CSS url() (both resolve through this callback). `data:` URIs
    are already inline (no network) and pass through unchanged. Audit P1-02."""
    if isinstance(uri, str) and uri.strip().lower().startswith("data:"):
        return uri
    logger.warning("PDF render replaced external resource with an inline blank: %s", uri)
    return _BLANK_DATA_URI


# Brand green (site --color-accent ≈ oklch(0.46 0.12 152)); print palette = dark ink on white.
_GREEN = "#2e7d4e"
_GREEN_DARK = "#21603a"
_GREEN_SOFT = "#eaf3ee"
_INK = "#1a1c1a"
_MUTED = "#5f5e5e"
_BORDER = "#d6e2da"

_REPORT_TYPE_LABELS = {
    "situation": "M&E Situation Report",
    "indicator_monitoring": "M&E Indicator Monitoring Report",
    "needs_assessment": "M&E Needs Assessment Brief",
}


def _type_label(report_type: str | None) -> str:
    return _REPORT_TYPE_LABELS.get(report_type or "situation", _REPORT_TYPE_LABELS["situation"])


_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
_fonts_ready = False


def _register_fonts() -> None:
    """Register Bitstream Vera (shipped with reportlab) with reportlab + xhtml2pdf so
    `font-family: Vera` resolves to a Unicode TTF with full Turkish coverage. Done by
    direct registration rather than CSS @font-face: xhtml2pdf's @font-face path copies
    the TTF to a temp file and fails on Windows (PermissionError); direct registration
    works on every platform and needs no font files in the repo."""
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONT_DIR, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(_FONT_DIR, "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Italic", os.path.join(_FONT_DIR, "VeraIt.ttf")))
    pdfmetrics.registerFontFamily(
        "Vera", normal="Vera", bold="Vera-Bold", italic="Vera-Italic", boldItalic="Vera-Bold"
    )
    try:
        from xhtml2pdf.default import DEFAULT_FONT
        DEFAULT_FONT["vera"] = "Vera"
    except Exception:  # pragma: no cover - defensive, version-dependent
        pass
    _fonts_ready = True


_CSS = f"""
@page {{
  size: a4 portrait;
  margin: 1.6cm 1.7cm 2.1cm 1.7cm;
  @frame footer {{ -pdf-frame-content: footerContent; bottom: 1cm; margin-left: 1.7cm; margin-right: 1.7cm; height: 1cm; }}
}}
body {{ font-family: "Vera"; font-size: 10pt; color: {_INK}; line-height: 1.4; }}

table.brandbar {{ background-color: {_GREEN}; }}
table.brandbar td {{ padding: 11pt 12pt; }}
table.brandbar .brand {{ font-size: 15pt; font-weight: bold; color: #ffffff; }}
table.brandbar .brandsub {{ font-size: 8.5pt; color: #d8ece0; }}

h1.reporttitle {{ font-size: 16pt; color: {_GREEN_DARK}; margin: 14pt 0 2pt 0; }}
.titlerule {{ border-bottom: 2pt solid {_GREEN}; margin-bottom: 10pt; }}

table.scopebox {{ background-color: {_GREEN_SOFT}; border: 0.5pt solid {_BORDER}; margin-bottom: 14pt; }}
table.scopebox td {{ padding: 7pt 9pt; font-size: 8.5pt; color: {_INK}; }}
table.scopebox .lbl {{ color: {_GREEN_DARK}; font-weight: bold; font-size: 7pt; text-transform: uppercase; }}

.body h2 {{ font-size: 12.5pt; color: {_GREEN_DARK}; border-bottom: 0.75pt solid {_BORDER}; padding-bottom: 2pt; margin: 14pt 0 6pt 0; }}
.body h3 {{ font-size: 10.5pt; color: {_GREEN}; margin: 10pt 0 3pt 0; }}
.body p {{ margin: 0 0 6pt 0; text-align: justify; }}
.body ul {{ margin: 2pt 0 8pt 0; }}
.body li {{ margin-bottom: 3pt; }}
.body table {{ width: 100%; border-collapse: collapse; margin: 4pt 0 10pt 0; }}
.body table th, .body table td {{ border: 0.5pt solid {_BORDER}; padding: 4pt 6pt; font-size: 8.5pt; text-align: left; }}
.body table th {{ background-color: {_GREEN_SOFT}; color: {_GREEN_DARK}; font-weight: bold; }}
.cite {{ color: {_GREEN}; font-weight: bold; }}

h2.sources-h {{ font-size: 11pt; color: {_GREEN_DARK}; border-bottom: 0.75pt solid {_BORDER}; padding-bottom: 2pt; margin: 16pt 0 6pt 0; }}
table.sources {{ table-layout: fixed; }}
table.sources td {{ padding: 3pt 4pt; font-size: 8pt; vertical-align: top; }}
table.sources .num {{ color: {_GREEN}; font-weight: bold; width: 24pt; }}
table.sources .title {{ color: {_INK}; }}
table.sources .meta {{ color: {_MUTED}; }}
table.sources .url {{ color: {_GREEN}; font-size: 7.5pt; -pdf-word-wrap: CJK; }}

#footerContent {{ color: {_MUTED}; font-size: 7.5pt; text-align: center; }}
"""


def _valid_sources(sources) -> list:
    """The sources that actually render as a listed reference (have a title + url). The cover count
    and the Sources list are both derived from this, so the two can never disagree."""
    return [s for s in (sources or []) if s.get("title") and s.get("url")]


def _sources_rows(sources) -> str:
    rows = []
    for s in _valid_sources(sources):
        n = s.get("index", "")
        title = html.escape(str(s.get("title", "")))
        meta_bits = [b for b in (s.get("source"), s.get("date")) if b]
        meta = html.escape(" · ".join(str(b) for b in meta_bits))
        url = html.escape(str(s.get("url", "")))
        rows.append(
            f'<tr><td class="num">[{n}]</td>'
            f'<td class="ref"><span class="title">{title}</span>'
            + (f'<br/><span class="meta">{meta}</span>' if meta else "")
            + f'<br/><span class="url">{url}</span></td></tr>'
        )
    return "".join(rows)


def _body_html(markdown_text: str) -> str:
    """Markdown → HTML, then tint citation markers [n] green."""
    html_body = _markdown.markdown(markdown_text or "", extensions=["extra", "sane_lists"])
    return re.sub(r"\[(\d+)\]", r'<span class="cite">[\1]</span>', html_body)


def render_report_pdf(report: dict) -> bytes:
    """Render a stored report dict (content markdown + sources + metadata) to PDF bytes."""
    country = html.escape(str(report.get("country") or ""))
    sector = html.escape(str(report.get("theme") or "All sectors"))
    date_from = report.get("date_from") or "…"
    date_to = report.get("date_to") or "…"
    period = html.escape(f"{date_from} – {date_to}")
    # Cover count = the sources actually listed below, so the cover can never advertise more
    # reports than the reader can see (doc_count is the retrieved set; not all of it gets cited).
    source_count = len(_valid_sources(report.get("sources")))
    generated = datetime.now(timezone.utc).strftime("%d %b %Y")
    type_label = _type_label(report.get("report_type"))

    doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_CSS}</style></head><body>
<table class="brandbar" width="100%"><tr>
  <td class="brand">Humanitaria</td>
  <td class="brandsub" align="right" valign="middle">{html.escape(type_label)}</td>
</tr></table>

<h1 class="reporttitle">{country} &middot; {sector}</h1>
<div class="titlerule"></div>

<table class="scopebox" width="100%"><tr>
  <td width="32%"><span class="lbl">Period</span><br/>{period}</td>
  <td width="30%"><span class="lbl">Sectors</span><br/>{sector}</td>
  <td width="20%"><span class="lbl">Source reports</span><br/>{source_count}</td>
  <td width="18%"><span class="lbl">Generated</span><br/>{html.escape(generated)}</td>
</tr></table>

<div class="body">{_body_html(report.get("content"))}</div>

<h2 class="sources-h">Sources</h2>
<table class="sources" width="100%">{_sources_rows(report.get("sources"))}</table>

<div id="footerContent">Generated from ReliefWeb reports by Humanitaria &middot; {html.escape(generated)} &middot; Page <pdf:pagenumber> of <pdf:pagecount></div>
</body></html>"""

    _register_fonts()
    buf = io.BytesIO()
    status = pisa.CreatePDF(doc, dest=buf, encoding="utf-8", link_callback=_block_external_resources)
    if status.err:
        logger.error("PDF generation reported %d error(s)", status.err)
        raise RuntimeError("PDF generation failed")
    return buf.getvalue()
