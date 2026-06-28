"""Tests for the M&E situation-report feature (store, retrieval helpers, endpoints)."""
import json
import re
from unittest.mock import patch, MagicMock, AsyncMock

import anyio
import pytest
from langchain_core.documents import Document


@pytest.fixture(autouse=True)
def _import_api():
    import api.routes.reports  # noqa: F401 — ensure module is loaded for patching


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


def _doc(i: int = 1) -> Document:
    return Document(
        page_content=f"Humanitarian content {i}",
        metadata={
            "title": f"WFP Report {i}",
            "url": f"https://reliefweb.int/report/{i}",
            "date": "2026-05-01",
            "country": "Sudan",
            "source": "WFP",
            "doctype": "report",
        },
    )


# --- persistence (rag/reports.py) -------------------------------------------

class TestReportStore:
    def _create(self, rid="r1", user="test-user"):
        from rag import reports as store
        store.create_report(
            rid, user, country="Sudan", theme=None, date_from="2026-01-01",
            date_to="2026-06-30", language="en", title="Sudan · All sectors · 2026",
            content="## Summary\nThings happened [1].", sources=[{"index": 1, "title": "A", "url": "u1"}],
            doc_count=3,
        )

    def test_create_get_roundtrip(self):
        from rag import reports as store
        self._create()
        rep = store.get_report("r1")
        assert rep["country"] == "Sudan"
        assert rep["content"].startswith("## Summary")
        assert rep["sources"] == [{"index": 1, "title": "A", "url": "u1"}]
        assert rep["doc_count"] == 3

    def test_list_newest_first_and_lean(self):
        from rag import reports as store
        self._create("r1")
        self._create("r2")
        rows = store.list_reports("test-user")
        assert {r["id"] for r in rows} == {"r1", "r2"}
        # lean rows: no body
        assert "content" not in rows[0]

    def test_ownership(self):
        from rag import reports as store
        self._create("r1", user="owner-A")
        assert store.is_owner("owner-A", "r1") is True
        assert store.is_owner("test-user", "r1") is False
        assert store.list_reports("test-user") == []

    def test_delete(self):
        from rag import reports as store
        self._create("r1")
        store.delete_report("r1")
        assert store.get_report("r1") is None

    def test_get_missing_returns_none(self):
        from rag import reports as store
        assert store.get_report("nope") is None


# --- retriever date range ($lte) --------------------------------------------

class TestDateRangeFilter:
    def test_build_filter_range(self):
        from rag.retriever import _build_pinecone_filter
        out = _build_pinecone_filter({"date": {"$gte": "2024-01-01", "$lte": "2024-06-30"}})
        assert out["date_ts"] == {"$gte": 20240101, "$lte": 20240630}

    def test_build_filter_gte_only_backcompat(self):
        from rag.retriever import _build_pinecone_filter
        out = _build_pinecone_filter({"date": {"$gte": "2024-01-01"}})
        assert out["date_ts"] == {"$gte": 20240101}

    def test_apply_date_filter_upper_bound(self):
        from rag.retriever import apply_date_filter
        docs = [
            Document(page_content="a", metadata={"date": "2024-03-01"}),
            Document(page_content="b", metadata={"date": "2024-08-01"}),
            Document(page_content="c", metadata={"date": "2023-12-31"}),
        ]
        out = apply_date_filter(docs, {"$gte": "2024-01-01", "$lte": "2024-06-30"})
        assert [d.page_content for d in out] == ["a"]


# --- report_service ----------------------------------------------------------

class TestReportService:
    def test_build_directive_language(self):
        from rag.report_service import build_report_directive
        tr = build_report_directive("Sudan", None, "2026-01-01", "2026-06-30", 5, "tr")
        en = build_report_directive("Sudan", "Health", "2026-01-01", "2026-06-30", 5, "en")
        assert "Turkish" in tr and "Sudan" in tr and "all sectors" in tr
        assert "English" in en and "Health" in en

    def test_report_title(self):
        from rag.report_service import report_title
        assert report_title("Sudan", None, "2026-01-01", "2026-06-30") == \
            "Sudan · All sectors · 2026-01-01 – 2026-06-30"
        assert "Health" in report_title("Sudan", "Health", "2026-01-01", "2026-06-30")

    def test_retrieve_builds_scoped_filter(self):
        from rag import report_service
        captured = {}

        def fake_build_retriever(filter=None, k=None):
            captured["filter"] = filter
            captured["k"] = k
            r = MagicMock()
            r.ainvoke = AsyncMock(return_value=[_doc(1)])
            return r

        with patch("rag.report_service.build_retriever", side_effect=fake_build_retriever), \
             patch("rag.report_service.rerank_by_relevance", side_effect=lambda q, d, n: d[:n]), \
             patch("rag.report_service.rerank_by_recency", side_effect=lambda d: d):
            docs = anyio.run(
                report_service.retrieve_for_report, "Sudan", "Health", "2026-01-01", "2026-06-30", 12
            )
        assert captured["filter"]["country"] == "Sudan"
        assert captured["filter"]["theme"] == "Health"
        assert captured["filter"]["date"] == {"$gte": "2026-01-01", "$lte": "2026-06-30"}
        assert captured["k"] == 12 * 4  # top_k * RERANK_CANDIDATE_MULTIPLIER
        assert len(docs) == 1


# --- analytics distinct countries -------------------------------------------

class TestDistinctCountries:
    def test_distinct_sorted_nonempty(self):
        from ingestion import analytics
        prev = analytics._state.documents
        analytics._state.documents = [
            {"country": "Sudan"}, {"country": "Yemen"}, {"country": "Sudan"}, {"country": ""},
        ]
        try:
            assert analytics.distinct_countries() == ["Sudan", "Yemen"]
        finally:
            analytics._state.documents = prev


# --- endpoints ---------------------------------------------------------------

def _client():
    from api.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestReportEndpoints:
    def test_options(self):
        with patch("ingestion.analytics.distinct_countries", return_value=["Sudan", "Yemen"]):
            r = _client().get("/reports/options")
        assert r.status_code == 200
        body = r.json()
        assert body["countries"] == ["Sudan", "Yemen"]
        assert "Health" in body["themes"]

    def test_options_cold_cache_falls_back_to_static(self):
        # Fresh deploy: scan cache empty → distinct_countries() == [] → the dropdown
        # must still be populated from the static COUNTRIES snapshot (never empty).
        with patch("ingestion.analytics.distinct_countries", return_value=[]):
            r = _client().get("/reports/options")
        assert r.status_code == 200
        countries = r.json()["countries"]
        assert len(countries) > 100
        assert "Sudan" in countries and "Yemen" in countries

    def test_stream_then_persist_and_list(self):
        async def mock_astream(*args, **kwargs):
            yield "## Summary\n"
            yield "Conflict worsened [1]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc(1)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain):
            client = _client()
            resp = client.post("/reports/stream", json={
                "country": "Sudan", "date_from": "2026-01-01", "date_to": "2026-06-30", "language": "en",
            })
            assert resp.status_code == 200
            events = _parse_sse_events(resp.text)
            kinds = [e["event"] for e in events]
            assert "token" in kinds
            assert "sources" in kinds
            assert "saved" in kinds
            assert kinds[-1] == "done"
            saved = next(e for e in events if e["event"] == "saved")
            rid = saved["data"]["report_id"]

            # auto-saved → appears in the list and is fetchable
            lst = client.get("/reports/list").json()["reports"]
            assert any(r["id"] == rid for r in lst)
            full = client.get(f"/reports/{rid}").json()
            assert "Conflict worsened" in full["content"]

    def test_stream_no_docs(self):
        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[])):
            resp = _client().post("/reports/stream", json={"country": "Atlantis"})
            events = _parse_sse_events(resp.text)
            assert events[0]["event"] == "token"
            assert "bulunamadı" in events[0]["data"]["content"] or "No matching" in events[0]["data"]["content"]
            assert events[-1]["event"] == "done"

    def test_get_report_not_owner_404(self):
        from rag import reports as store
        store.create_report(
            "rX", "someone-else", country="Sudan", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        client = _client()
        assert client.get("/reports/rX").status_code == 404
        assert client.delete("/reports/rX").status_code == 404

    def test_delete_own_report(self):
        from rag import reports as store
        store.create_report(
            "rD", "test-user", country="Sudan", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        client = _client()
        assert client.delete("/reports/rD").status_code == 200
        assert client.get("/reports/rD").status_code == 404
