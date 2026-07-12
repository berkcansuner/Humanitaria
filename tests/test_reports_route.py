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
    from analytics.technical_report import Findings, ReportSection
    section = ReportSection(
        heading="İnsani ihtiyaç — Trend Analizi",
        stat_result={"kind": "trend"},
        chart="data:image/png;base64,ZZZ",
        findings_text="İnsani ihtiyaç: yön=artış, eğim=1.00/dönem, p=0.010, n=6.",
    )
    return Findings(sections=[section], gaps=[], indicators_covered=["humanitarian_needs"])


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
                {"heading": "İnsani ihtiyaç — Trend Analizi", "image": "data:image/png;base64,ZZZ"}
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
