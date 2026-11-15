"""Report series, step 2: /reports/stream with previous_report_id.

The route checks the previous report belongs to the user and shares the series key
(type + country + sector + language), adds the comparison block to the directive,
and stores the link on the new report.
"""
import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document
import pytest


@pytest.fixture(autouse=True)
def verify():
    """The comparison check (rag.report_compare) is stubbed: no network in tests.
    It marks the content so a test can see the stored report went through it."""
    async def mark(content, **kw):
        return content + "\n<!-- checked -->"
    with patch("api.routes.reports.verify_comparison", new=AsyncMock(side_effect=mark)) as m:
        yield m


def _parse_sse_events(raw_text: str) -> list[dict]:
    events = []
    for block in re.split(r"\r?\n\r?\n", raw_text):
        block = block.strip()
        if not block:
            continue
        event_type, data_lines = "message", []
        for line in re.split(r"\r?\n", block):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            events.append({"event": event_type, "data": json.loads("\n".join(data_lines))})
    return events


def _client():
    from api.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def _doc():
    return Document(page_content="Needs rose to 3 million.", metadata={
        "title": "OCHA update", "url": "https://reliefweb.int/report/9", "date": "2026-08-01",
        "country": "Sudan", "source": "OCHA", "doctype": "report"})


def _save_previous(rid="r-prev", user="test-user", **kw):
    from rag import reports as store
    fields = dict(country="Sudan", theme="Health", date_from="2026-04-01",
                  date_to="2026-06-30", language="en", title="Sudan · Health · Q2",
                  content="## Executive Summary\nNeeds stood at 2 million [1].",
                  sources=None, doc_count=1, report_type="situation")
    fields.update(kw)
    store.create_report(rid, user, **fields)


def _capturing_chain(seen: list):
    async def mock_astream(inputs, *a, **k):
        seen.append(inputs)
        yield "## Executive Summary\nNeeds rose [1]."
    chain = MagicMock()
    chain.astream = mock_astream
    return chain


_NEXT = {"country": "Sudan", "theme": "Health", "date_from": "2026-07-01",
         "date_to": "2026-09-30", "language": "en", "report_type": "situation"}


def _stream(body, seen):
    with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc()])), \
         patch("api.routes.reports.build_report_chain", return_value=_capturing_chain(seen)):
        return _client().post("/reports/stream", json=body)


def _saved_id(resp) -> str:
    events = _parse_sse_events(resp.text)
    return next(e for e in events if e["event"] == "saved")["data"]["report_id"]


def test_next_period_report_gets_comparison_and_stores_link():
    _save_previous()
    seen = []
    resp = _stream({**_NEXT, "previous_report_id": "r-prev"}, seen)
    assert resp.status_code == 200
    question = seen[0]["question"]
    assert "What changed since the last report" in question
    assert "Needs stood at 2 million" in question
    assert "2026-04-01 to 2026-06-30" in question
    assert "this report covers 2026-07-01 to 2026-09-30" in question  # the new period
    # the previous report is comparison material, not one of the [n] sources
    assert "Needs stood at 2 million" not in seen[0]["context"]
    rid = _saved_id(resp)
    assert _client().get(f"/reports/{rid}").json()["previous_report_id"] == "r-prev"


def test_one_off_report_has_no_comparison():
    seen = []
    resp = _stream(_NEXT, seen)
    assert resp.status_code == 200
    assert "What changed since the last report" not in seen[0]["question"]
    assert _client().get(f"/reports/{_saved_id(resp)}").json()["previous_report_id"] is None


def test_missing_previous_report_is_404_before_streaming():
    seen = []
    resp = _stream({**_NEXT, "previous_report_id": "gone"}, seen)
    assert resp.status_code == 404
    assert seen == []


def test_someone_elses_previous_report_is_404():
    _save_previous(user="other-user")
    seen = []
    resp = _stream({**_NEXT, "previous_report_id": "r-prev"}, seen)
    assert resp.status_code == 404
    assert seen == []


def test_previous_report_from_another_series_is_422():
    for field, value in (("country", "Yemen"), ("theme", "Education"), ("language", "tr"),
                         ("report_type", "needs_assessment")):
        _save_previous(rid=f"r-{field}", **{field: value})
        seen = []
        resp = _stream({**_NEXT, "previous_report_id": f"r-{field}"}, seen)
        assert resp.status_code == 422, field
        assert seen == []


def test_all_sectors_series_matches_on_null_theme():
    _save_previous(theme=None)
    seen = []
    body = {k: v for k, v in _NEXT.items() if k != "theme"}
    resp = _stream({**body, "previous_report_id": "r-prev"}, seen)
    assert resp.status_code == 200
    assert "What changed since the last report" in seen[0]["question"]


def test_technical_report_compares_and_stores_link():
    from analytics.technical_report import Findings, ReportSection
    findings = Findings(sections=[ReportSection(
        heading="Needs — Trend", stat_result={"kind": "trend"}, chart=None,
        findings_text="Needs: up, p=0.010, n=6.")], gaps=[], indicators_covered=["needs"])
    _save_previous(country="Afghanistan", theme=None, report_type="technical_monitoring")
    seen = []
    with patch("api.routes.reports.technical_report.compute_findings", return_value=findings), \
         patch("api.routes.reports.build_report_chain", return_value=_capturing_chain(seen)):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            "date_from": "2026-07-01", "date_to": "2026-09-30", "previous_report_id": "r-prev"})
    assert resp.status_code == 200
    assert "What changed since the last report" in seen[0]["question"]
    assert _client().get(f"/reports/{_saved_id(resp)}").json()["previous_report_id"] == "r-prev"


def test_comparative_report_is_checked_before_saving(verify):
    _save_previous()
    seen = []
    resp = _stream({**_NEXT, "previous_report_id": "r-prev"}, seen)
    assert resp.status_code == 200
    verify.assert_awaited_once()
    kwargs = verify.await_args.kwargs
    assert kwargs == {"heading": "What changed since the last report", "date_from": "2026-07-01",
                      "date_to": "2026-09-30", "language": "en"}
    stored = _client().get(f"/reports/{_saved_id(resp)}").json()["content"]
    assert stored.endswith("<!-- checked -->")


def test_turkish_comparative_report_checks_the_turkish_heading(verify):
    _save_previous(language="tr")
    seen = []
    resp = _stream({**_NEXT, "language": "tr", "previous_report_id": "r-prev"}, seen)
    assert resp.status_code == 200
    assert verify.await_args.kwargs["heading"] == "Son rapordan bu yana neler değişti"


def test_one_off_report_is_not_checked(verify):
    seen = []
    _stream(_NEXT, seen)
    verify.assert_not_awaited()


def test_technical_comparative_report_is_checked(verify):
    from analytics.technical_report import Findings, ReportSection
    findings = Findings(sections=[ReportSection(
        heading="Needs — Trend", stat_result={"kind": "trend"}, chart=None,
        findings_text="Needs: up, p=0.010, n=6.")], gaps=[], indicators_covered=["needs"])
    _save_previous(country="Afghanistan", theme=None, report_type="technical_monitoring")
    seen = []
    with patch("api.routes.reports.technical_report.compute_findings", return_value=findings),          patch("api.routes.reports.build_report_chain", return_value=_capturing_chain(seen)):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            "date_from": "2026-07-01", "date_to": "2026-09-30", "previous_report_id": "r-prev"})
    verify.assert_awaited_once()
    stored = _client().get(f"/reports/{_saved_id(resp)}").json()["content"]
    assert stored.endswith("<!-- checked -->")
