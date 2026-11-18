"""Indicator Table rows carry their [n] markers (round 2): the citation pipeline and the
PDF handle markers inside table cells, and the saved report lists only cited sources."""
from unittest.mock import AsyncMock, MagicMock, patch

from rag.citations import normalize_citations, normalize_table_delimiters
from rag.report_pdf import _body_html

REPORT = (
    "## Overview\n\nNeeds are rising across the east [4].\n\n"
    "## Indicator Table\n\n"
    "| Indicator | Latest value | As of |\n"
    "| --- | --- | --- |\n"
    "| People in need | 21.9 million [2] | 1 January 2026 |\n"
    "| IPC Phase 3+ | 9.5 million (20%) [5] [4] | March–May 2026 |\n"
    "| IDPs | 3.1 million [7] | 31 January 2026 |\n\n"
    "## Data Gaps\n\nNo WASH figures.\n"
)


def _sources(n=7):
    return [{"index": i, "url": f"https://reliefweb.int/report/{i}", "title": f"Doc {i}"}
            for i in range(1, n + 1)]


def test_table_markers_are_renumbered_and_sorted_with_the_prose():
    content, sources = normalize_citations(REPORT, _sources())
    assert "| People in need | 21.9 million [2] | 1 January 2026 |" in content
    assert "| IPC Phase 3+ | 9.5 million (20%) [1] [3] | March–May 2026 |" in content
    assert "| IDPs | 3.1 million [4] | 31 January 2026 |" in content
    assert [s["title"] for s in sources] == ["Doc 4", "Doc 2", "Doc 5", "Doc 7"]
    assert normalize_table_delimiters(content) == content


def test_pdf_tints_markers_inside_table_cells():
    content, _ = normalize_citations(REPORT, _sources())
    html = _body_html(content)
    assert '<td>21.9 million <span class="cite">[2]</span></td>' in html
    assert '<span class="cite">[1]</span> <span class="cite">[3]</span></td>' in html


def _doc(i):
    from langchain_core.documents import Document
    return Document(page_content=f"Content {i}", metadata={
        "title": f"Doc {i}", "url": f"https://reliefweb.int/report/{i}", "date": "2026-05-01",
        "country": "Mali", "source": "OCHA", "doctype": "report"})


def test_an_indicator_report_lists_the_sources_its_table_and_prose_cite():
    from api.main import app
    from fastapi.testclient import TestClient

    async def astream(*a, **k):
        yield ("## Overview\n\nNeeds rise [3].\n\n## Indicator Table\n\n"
               "| Indicator | Latest value | As of |\n| --- | --- | --- |\n"
               "| People in need | 7.1 million [1] | 2026 |\n")

    chain = MagicMock()
    chain.astream = astream
    with patch("api.routes.reports.retrieve_for_report",
               new=AsyncMock(return_value=[_doc(1), _doc(2), _doc(3)])), \
         patch("api.routes.reports.build_report_chain", return_value=chain), \
         patch("api.routes.reports.settings_images_enabled", return_value=False):
        client = TestClient(app)
        resp = client.post("/reports/stream", json={
            "country": "Mali", "report_type": "indicator_monitoring", "language": "en"})
        rid = next(line for line in resp.text.splitlines() if '"report_id"' in line)
        rid = rid.split('"report_id": "')[1].split('"')[0]
        rep = client.get(f"/reports/{rid}").json()
    assert "| People in need | 7.1 million [2] | 2026 |" in rep["content"]
    # Cited sources first, in marker order; an uncited document stays listed after them
    # (a row the model left without its marker keeps its source).
    assert [s["title"] for s in rep["sources"]] == ["Doc 3", "Doc 1", "Doc 2"]
    assert [s["index"] for s in rep["sources"]] == [1, 2, 3]
