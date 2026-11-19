"""technical_monitoring rapor türünün /reports/stream route'una bağlanması.

Kritik sözleşme: technical_monitoring, HAPI+istatistik pipeline'ına (analytics.
technical_report) dallanır ve DÖNER — asla belge-retrieval yoluna
(retrieve_for_report / _build_context_and_sources) düşmemelidir; aksi halde
_TECHNICAL_SYSTEM_PROMPT'un narrate-only sözleşmesi bozulur.
"""
import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analytics.countries import iso3_for


def test_iso3_mapping_known_countries():
    assert iso3_for("Afghanistan") == "AFG"
    assert iso3_for("Iran") == "IRN"
    assert iso3_for("Nonexistent Country") is None


def test_report_request_accepts_technical_type():
    from api.routes.reports import ReportRequest
    req = ReportRequest(country="Afghanistan", report_type="technical_monitoring")
    assert req.report_type == "technical_monitoring"


def _parse_sse_events(raw_text: str) -> list[dict]:
    events = []
    for block in re.split(r"\r?\n\r?\n", raw_text):
        block = block.strip()
        if not block:
            continue
        event_type = "message"
        data_lines = []
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


def _findings_with_sections():
    """One decreasing, untested-as-significant trend (refugees, 2.67 million in 2025)."""
    from tests.analytics import samples
    findings = samples.findings(samples.trend(heading="İnsani ihtiyaç — Eğilim Analizi"),
                                indicators_covered=["humanitarian_needs"])
    findings.sections[0].chart = "data:image/png;base64,ZZZ"
    return findings


class TestTechnicalMonitoringRoute:
    def test_technical_branch_never_calls_doc_retrieval(self):
        """Kritik veri-sözleşmesi: technical_monitoring dalı retrieve_for_report'u
        hiç çağırmamalı (çağrılırsa modele ReliefWeb metni sızar, narrate-only bozulur)."""
        async def mock_astream(*a, **k):
            yield "## İnsani ihtiyaç\n"
            yield "Trend yukarı yönlü."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.technical_report.compute_findings",
                   return_value=_findings_with_sections()), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain), \
             patch("api.routes.reports.retrieve_for_report",
                   new=AsyncMock(side_effect=AssertionError(
                       "doc-retrieval path must be unreachable for technical_monitoring"))):
            resp = _client().post("/reports/stream", json={
                "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            })
            assert resp.status_code == 200
            events = _parse_sse_events(resp.text)
            kinds = [e["event"] for e in events]
            assert "error" not in kinds
            assert "token" in kinds
            assert "saved" in kinds
            assert kinds[-1] == "done"

            rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
            rep = _client().get(f"/reports/{rid}").json()
            assert rep["report_type"] == "technical_monitoring"
            assert rep["section_images"] == [
                {"heading": "İnsani ihtiyaç — Eğilim Analizi", "image": "data:image/png;base64,ZZZ"}
            ]

    def test_technical_unknown_iso3_country_message(self):
        with patch("api.routes.reports.retrieve_for_report",
                   new=AsyncMock(side_effect=AssertionError("must not fall through"))):
            resp = _client().post("/reports/stream", json={
                "country": "Atlantis", "report_type": "technical_monitoring",
            })
            events = _parse_sse_events(resp.text)
            assert events[0]["event"] == "token"
            assert "ISO3" in events[0]["data"]["content"] or "HAPI" in events[0]["data"]["content"]
            assert events[-1]["event"] == "done"
            assert "saved" not in [e["event"] for e in events]

    def test_technical_empty_findings_message(self):
        # FIX #7: boş-bulgu mesajı belge-retrieval yolunun _no_docs_message'ını (yanlış
        # şekilde "belge bulunamadı" diyen) DEĞİL, HDX HAPI istatistik pipeline'ına özgü
        # bir mesajı kullanmalı.
        from analytics.technical_report import Findings
        empty = Findings(sections=[], gaps=["İnsani ihtiyaç: veri çekilemedi"], indicators_covered=[])
        with patch("api.routes.reports.technical_report.compute_findings", return_value=empty), \
             patch("api.routes.reports.retrieve_for_report",
                   new=AsyncMock(side_effect=AssertionError("must not fall through"))):
            resp = _client().post("/reports/stream", json={
                "country": "Sudan", "report_type": "technical_monitoring",
            })
            events = _parse_sse_events(resp.text)
            assert events[0]["event"] == "token"
            content = events[0]["data"]["content"]
            assert "HDX HAPI" in content
            assert "document" not in content.lower()
            assert "Sudan" in content
            assert "saved" not in [e["event"] for e in events]
            assert events[-1]["event"] == "done"

    def test_technical_empty_findings_message_turkish(self):
        from analytics.technical_report import Findings
        empty = Findings(sections=[], gaps=["İnsani ihtiyaç: veri çekilemedi"], indicators_covered=[])
        with patch("api.routes.reports.technical_report.compute_findings", return_value=empty), \
             patch("api.routes.reports.retrieve_for_report",
                   new=AsyncMock(side_effect=AssertionError("must not fall through"))):
            resp = _client().post("/reports/stream", json={
                "country": "Sudan", "report_type": "technical_monitoring", "language": "tr",
            })
            events = _parse_sse_events(resp.text)
            content = events[0]["data"]["content"]
            assert "HDX HAPI" in content
            assert "belge bulunamadı" not in content
            assert "Sudan" in content


_HEADING = "İnsani ihtiyaç — Eğilim Analizi"
_FACT = "The latest value is 2.67 million people (2025)"


def _technical(language="en", chain=None):
    chain = chain or MagicMock()
    with patch("api.routes.reports.technical_report.compute_findings",
               return_value=_findings_with_sections()), \
         patch("api.routes.reports.build_report_chain", return_value=chain) as build:
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": language})
    events = _parse_sse_events(resp.text)
    saved = next((e for e in events if e["event"] == "saved"), None)
    content = _client().get(f"/reports/{saved['data']['report_id']}").json()["content"] if saved else None
    return events, content, build


def test_a_technical_report_is_written_in_code_without_calling_a_model():
    """Every sentence comes from the computed findings; no model is called for it."""
    events, content, build = _technical()
    build.assert_not_called()
    assert content.startswith("## Executive Summary\n\nPeriod analysed:")
    assert f"## {_HEADING}\n\n{_FACT}" in content
    assert "## Data Coverage & Limitations" in content
    assert content.rstrip().endswith("its text is generated from them in code. No part of it is written by an AI model.")
    kinds = [e["event"] for e in events]
    assert "error" not in kinds and kinds[-2:] == ["saved", "done"]


def test_the_stream_carries_the_same_text_as_the_saved_report():
    events, content, _ = _technical()
    streamed = "".join(e["data"]["content"] for e in events if e["event"] == "token")
    assert streamed.startswith("## Executive Summary\n\nPeriod analysed:")
    assert " ".join(streamed.split()) == " ".join(content.split())


def test_a_turkish_report_is_written_in_turkish_by_the_code():
    _, content, _ = _technical(language="tr")
    assert content.startswith("## Yönetici Özeti\n\nAnaliz edilen dönem:")
    assert "Son değer 2,67 milyon kişi (2025)" in content
    assert "## Veri Kapsamı ve Sınırlılıklar" in content and "## Yöntem" in content
    assert content.rstrip().endswith("metin koddan üretildi. Hiçbir bölümü yapay zekâ modeli yazmadı.")


# --- Sector reports (2026-11-18): the chosen sector reaches the analysis, and a sector
# without HDX HAPI series is answered with a clear error, never with unrelated figures. ---

def test_the_chosen_sector_reaches_compute_findings():
    seen = {}

    def fake_compute(iso3, date_from, date_to, language="tr", theme=None):
        seen["theme"] = theme
        return _findings_with_sections()

    async def mock_astream(*a, **k):
        yield "## Executive Summary\n\nText."

    chain = MagicMock()
    chain.astream = mock_astream
    with patch("api.routes.reports.technical_report.compute_findings", side_effect=fake_compute), \
         patch("api.routes.reports.build_report_chain", return_value=chain):
        _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            "theme": "Food and Nutrition",
        })
    assert seen["theme"] == "Food and Nutrition"


def test_a_sector_without_series_is_a_clear_error_before_any_hapi_call():
    with patch("api.routes.reports.technical_report.compute_findings",
               side_effect=AssertionError("no HAPI call for an unmapped sector")):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            "theme": "Logistics and Telecommunications",
        })
    events = _parse_sse_events(resp.text)
    error = next(e for e in events if e["event"] == "error")
    assert error["data"]["code"] == "no_sector_data"
    assert "All sectors" in error["data"]["message"]
    assert "saved" not in [e["event"] for e in events] and events[-1]["event"] == "done"


def test_a_sector_whose_series_are_empty_for_the_country_is_the_same_error():
    from analytics.technical_report import Findings
    empty = Findings(sections=[], gaps=["Food security: people in need: dönem içinde veri yok"],
                     indicators_covered=[])
    with patch("api.routes.reports.technical_report.compute_findings", return_value=empty):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "tr",
            "theme": "Food and Nutrition",
        })
    events = _parse_sse_events(resp.text)
    assert next(e for e in events if e["event"] == "error")["data"]["code"] == "no_sector_data"
    assert "token" not in [e["event"] for e in events]


def test_options_name_the_sectors_with_technical_monitoring_series():
    with patch("ingestion.analytics.distinct_countries", return_value=["Sudan"]):
        body = _client().get("/reports/options").json()
    assert "Food and Nutrition" in body["technical_themes"]
    assert "Logistics and Telecommunications" not in body["technical_themes"]
    assert set(body["technical_themes"]) <= set(body["themes"])


def test_technical_stream_says_which_indicators_were_computed_before_the_narrative():
    """After the HAPI statistics, one status event names the indicators that have
    data (in the report language) and the period analysed, before any token."""
    from analytics.indicators import indicators_for
    first, second = indicators_for(None)[:2]
    findings = _findings_with_sections()
    findings.indicators_covered = [second.key, first.key]
    findings.date_from, findings.date_to = "2021-11-18", "2026-11-18"

    async def mock_astream(*a, **k):
        yield "## Summary\n"
        yield "Text."

    mock_chain = MagicMock()
    mock_chain.astream = mock_astream
    for language in ("en", "tr"):
        with patch("api.routes.reports.technical_report.compute_findings", return_value=findings), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain):
            resp = _client().post("/reports/stream", json={
                "country": "Afghanistan", "report_type": "technical_monitoring", "language": language,
            })
        events = _parse_sse_events(resp.text)
        kinds = [e["event"] for e in events]
        assert kinds[0] == "status"
        rest = [k for k in kinds if k != "status"]
        assert rest[0] == "token" and rest[-2:] == ["saved", "done"]
        assert events[0]["data"] == {
            "stage": "computed",
            # In the order the report analyses them, named in the report language.
            "indicators": [first.name(language), second.name(language)],
            "date_from": "2021-11-18",
            "date_to": "2026-11-18",
        }


def test_technical_stream_without_findings_sends_no_status():
    from analytics.technical_report import Findings
    with patch("api.routes.reports.technical_report.compute_findings",
               return_value=Findings(sections=[], gaps=[], indicators_covered=[])):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
        })
    assert "status" not in [e["event"] for e in _parse_sse_events(resp.text)]


def test_a_hapi_outage_is_not_reported_as_a_sector_without_data():
    from analytics.technical_report import Findings
    down = Findings(sections=[], gaps=["Food security: people in need: veri çekilemedi"],
                    indicators_covered=[], failed=["pin_food_security"])
    for theme in ("Food and Nutrition", None):
        with patch("api.routes.reports.technical_report.compute_findings", return_value=down):
            resp = _client().post("/reports/stream", json={
                "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
                "theme": theme,
            })
        events = _parse_sse_events(resp.text)
        assert next(e for e in events if e["event"] == "error")["data"]["code"] == "report_failed"
        assert "token" not in [e["event"] for e in events]


def test_a_technical_report_is_saved_with_its_data_sources():
    from analytics.technical_report import Findings
    findings = _findings_with_sections()
    findings.data_sources = [{"key": "humanitarian_needs", "title": "People in need (people)",
                              "source": "OCHA HNO", "first_period": "2024-01-01",
                              "last_period": "2026-01-01", "resource_hdx_id": "r1"}]
    assert isinstance(findings, Findings)

    async def mock_astream(*a, **k):
        yield "## İnsani ihtiyaç — Eğilim Analizi\n\nThe trend has p=0.010."

    chain = MagicMock()
    chain.astream = mock_astream
    meta = {"dataset_hdx_stub": "global-hpc-hno", "dataset_hdx_title": "Global HNO"}
    with patch("api.routes.reports.technical_report.compute_findings", return_value=findings), \
         patch("api.routes.reports.build_report_chain", return_value=chain), \
         patch("analytics.technical_report.resource_metadata", return_value=meta):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en"})
        events = _parse_sse_events(resp.text)
        sources = next(e for e in events if e["event"] == "sources")["data"]["sources"]
        rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
        saved = _client().get(f"/reports/{rid}").json()["sources"]
    assert saved == sources
    assert saved[0]["doctype"] == "dataset" and saved[0]["source"] == "OCHA HNO"
    assert saved[0]["url"] == "https://data.humdata.org/dataset/global-hpc-hno"
    assert "app_identifier" not in saved[0]["url"]


def test_an_impossible_date_is_a_validation_error():
    resp = _client().post("/reports/stream", json={
        "country": "Afghanistan", "report_type": "technical_monitoring", "date_from": "2026-02-30"})
    assert resp.status_code == 422 and resp.json()["code"] == "validation_failed"


def test_a_capped_period_end_is_the_one_in_the_title_and_saved_report():
    findings = _findings_with_sections()
    findings.date_from, findings.date_to = "2025-01-01", "2026-11-18"
    with patch("api.routes.reports.technical_report.compute_findings", return_value=findings):
        resp = _client().post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
            "date_from": "2025-01-01", "date_to": "2030-12-31"})
    events = _parse_sse_events(resp.text)
    saved = next(e for e in events if e["event"] == "saved")["data"]
    assert "2026-11-18" in saved["title"] and "2030" not in saved["title"]
    assert _client().get(f"/reports/{saved['report_id']}").json()["date_to"] == "2026-11-18"
