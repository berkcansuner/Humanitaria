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


_EN_TEXT = ("The humanitarian situation continues to deteriorate as conflict and "
            "displacement increase across the affected regions, leaving millions in need.")
_FR_TEXT = ("La situation humanitaire continue de se détériorer alors que le conflit et les "
            "déplacements augmentent dans les régions touchées, laissant des millions dans le besoin.")


def _doc_text(text: str) -> Document:
    return Document(page_content=text, metadata={"title": "t", "url": "u"})


def _src_doc(title: str, source: str, date: str, text: str) -> Document:
    return Document(page_content=text, metadata={"title": title, "source": source, "date": date, "url": "u"})


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

    def test_create_report_stores_report_type(self):
        from rag import reports as store
        store.create_report(
            "r-type", "test-user", country="Mali", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
            report_type="indicator_monitoring",
        )
        rep = store.get_report("r-type")
        assert rep["report_type"] == "indicator_monitoring"
        rows = store.list_reports("test-user")
        assert next(r for r in rows if r["id"] == "r-type")["report_type"] == "indicator_monitoring"

    def test_create_report_defaults_report_type_to_situation(self):
        from rag import reports as store
        store.create_report(
            "r-default", "test-user", country="Mali", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        assert store.get_report("r-default")["report_type"] == "situation"

    def test_create_report_stores_images(self):
        from rag import reports as store
        store.create_report(
            "r-img", "test-user", country="Mali", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
            cover_image="data:image/png;base64,AAAA",
            section_images=[{"heading": "Overview", "image": "data:image/png;base64,BBBB"}],
        )
        rep = store.get_report("r-img")
        assert rep["cover_image"] == "data:image/png;base64,AAAA"
        assert rep["section_images"] == [{"heading": "Overview", "image": "data:image/png;base64,BBBB"}]
        # lean list must NOT carry the heavy image columns
        rows = store.list_reports("test-user")
        row = next(r for r in rows if r["id"] == "r-img")
        assert "cover_image" not in row and "section_images" not in row

    def test_create_report_images_default_none(self):
        from rag import reports as store
        store.create_report(
            "r-noimg", "test-user", country="Mali", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        rep = store.get_report("r-noimg")
        assert rep["cover_image"] is None
        assert rep["section_images"] is None


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
        assert captured["filter"]["doctype"] == "report"
        assert captured["k"] == 12 * 4  # top_k * RERANK_CANDIDATE_MULTIPLIER
        assert len(docs) == 1

    def test_prefer_english_filters_when_english_dominant(self):
        # Anglophone crisis: candidates ≥ 60% English → cite English sources only.
        from rag.report_service import _prefer_english
        docs = [_doc_text(_EN_TEXT)] * 4 + [_doc_text(_FR_TEXT)]   # 4/5 = 0.8 EN
        out = _prefer_english(docs)
        assert len(out) == 4
        assert all(d.page_content == _EN_TEXT for d in out)

    def test_prefer_english_keeps_all_when_french_dominant(self):
        # Francophone crisis: English a minority → keep the French-majority set intact.
        from rag.report_service import _prefer_english
        docs = [_doc_text(_EN_TEXT)] * 2 + [_doc_text(_FR_TEXT)] * 3   # 2/5 = 0.4 EN
        out = _prefer_english(docs)
        assert out == docs

    def test_prefer_english_empty_is_noop(self):
        from rag.report_service import _prefer_english
        assert _prefer_english([]) == []

    def test_collapse_translation_pair_keeps_english(self):
        # Same WFP press release in English + French (same org, same date) → one English representative.
        from rag.report_service import _collapse_near_duplicates
        en = _src_doc("WFP scales up emergency Ebola response in eastern DRC",
                      "World Food Programme", "2026-05-22", _EN_TEXT)
        fr = _src_doc("Le PAM intensifie sa réponse d'urgence contre Ebola dans l'est de la RDC",
                      "World Food Programme", "2026-05-22", _FR_TEXT)
        out = _collapse_near_duplicates([en, fr])
        assert len(out) == 1
        assert out[0].metadata["title"].startswith("WFP scales up")

    def test_collapse_prefix_companion_keeps_most_recent(self):
        # Base report + its "… : Insights and recommendations" companion (same org) → keep most recent.
        from rag.report_service import _collapse_near_duplicates
        base = _src_doc("How the conduct of conflict affects food security and health care in Sudan",
                        "Insecurity Insight", "2026-04-20", _EN_TEXT)
        companion = _src_doc("How the conduct of conflict affects food security and health care in Sudan: "
                             "Insights and recommendations to enhance civilian protection",
                             "Insecurity Insight", "2026-04-14", _EN_TEXT + " More detail.")
        out = _collapse_near_duplicates([base, companion])
        assert len(out) == 1
        assert out[0].metadata["date"] == "2026-04-20"

    def test_collapse_keeps_distinct_monthly_series(self):
        # A monthly market series (Mars vs Avril, different dates) must NOT be collapsed.
        from rag.report_service import _collapse_near_duplicates
        mar = _src_doc("République démocratique du Congo - Initiative conjointe de suivi des marchés (ICSM) - Mars 2026",
                       "REACH Initiative", "2026-04-27", _FR_TEXT)
        avr = _src_doc("République démocratique du Congo - Initiative conjointe de suivi des marchés (ICSM) - Avril 2026",
                       "REACH Initiative", "2026-06-02", _FR_TEXT)
        out = _collapse_near_duplicates([mar, avr])
        assert len(out) == 2

    def test_collapse_keeps_different_source_same_date(self):
        # Two distinct SMART surveys, same date but different orgs → not grouped, not collapsed.
        from rag.report_service import _collapse_near_duplicates
        a = _src_doc("Enquête nutritionnelle SMART Rapide - Fataki, Ituri",
                     "Action contre la Faim France", "2026-05-08", _FR_TEXT)
        b = _src_doc("Enquête nutritionnelle et de mortalité SMART - Alimbongo, Nord-Kivu",
                     "Nutrition Cluster", "2026-05-08", _FR_TEXT)
        out = _collapse_near_duplicates([a, b])
        assert len(out) == 2

    def test_collapse_noop_on_singleton_and_empty(self):
        from rag.report_service import _collapse_near_duplicates
        assert _collapse_near_duplicates([]) == []
        one = [_src_doc("t", "WFP", "2026-01-01", _EN_TEXT)]
        assert _collapse_near_duplicates(one) == one

    def _report_settings(self, report_top_k=12, candidate_multiplier=4):
        s = MagicMock()
        s.REPORT_TOP_K = report_top_k
        s.RERANK_CANDIDATE_MULTIPLIER = candidate_multiplier
        return s

    def test_retrieve_widens_top_k_for_indicator_monitoring(self):
        from rag import report_service
        captured = {}

        def fake_build_retriever(filter=None, k=None):
            captured["k"] = k
            r = MagicMock()
            r.ainvoke = AsyncMock(return_value=[])
            return r

        with patch("rag.report_service.get_settings", return_value=self._report_settings()), \
             patch("rag.report_service.build_retriever", side_effect=fake_build_retriever), \
             patch("rag.report_service.rerank_by_relevance", side_effect=lambda q, d, n: d[:n]), \
             patch("rag.report_service.rerank_by_recency", side_effect=lambda d: d):
            anyio.run(
                report_service.retrieve_for_report, "Mali", None, None, None, None,
                "indicator_monitoring",
            )
        assert captured["k"] == 16 * 4  # top_k widened to 16 (> REPORT_TOP_K=12) for indicator_monitoring

    def test_retrieve_situation_keeps_configured_top_k(self):
        from rag import report_service
        captured = {}

        def fake_build_retriever(filter=None, k=None):
            captured["k"] = k
            r = MagicMock()
            r.ainvoke = AsyncMock(return_value=[])
            return r

        with patch("rag.report_service.get_settings", return_value=self._report_settings()), \
             patch("rag.report_service.build_retriever", side_effect=fake_build_retriever), \
             patch("rag.report_service.rerank_by_relevance", side_effect=lambda q, d, n: d[:n]), \
             patch("rag.report_service.rerank_by_recency", side_effect=lambda d: d):
            anyio.run(report_service.retrieve_for_report, "Sudan", None, None, None)
        assert captured["k"] == 12 * 4  # unchanged for the default (situation) type

    def test_report_title_type_prefix(self):
        from rag.report_service import report_title
        assert report_title("Mali", "Food and Nutrition", "2026-04-01", "2026-07-01",
                            report_type="indicator_monitoring") == \
            "Indicator Monitoring Report — Mali · Food and Nutrition · 2026-04-01 – 2026-07-01"
        assert report_title("Mali", None, "2026-04-01", "2026-07-01",
                            report_type="needs_assessment") == \
            "Needs Assessment Brief — Mali · All sectors · 2026-04-01 – 2026-07-01"
        # default (situation) unchanged
        assert report_title("Sudan", None, "2026-01-01", "2026-06-30") == \
            "Sudan · All sectors · 2026-01-01 – 2026-06-30"

    def test_build_directive_type_verb(self):
        from rag.report_service import build_report_directive
        situation = build_report_directive("Sudan", None, "2026-01-01", "2026-06-30", 5, "en")
        indicator = build_report_directive("Mali", None, "2026-01-01", "2026-06-30", 5, "en",
                                           report_type="indicator_monitoring")
        needs = build_report_directive("Mali", None, "2026-01-01", "2026-06-30", 5, "en",
                                       report_type="needs_assessment")
        assert situation.startswith("Generate the situation report.")
        assert indicator.startswith("Generate the indicator monitoring report.")
        assert needs.startswith("Generate the needs assessment brief.")

    def test_report_types_constant(self):
        from rag.report_service import REPORT_TYPES
        assert REPORT_TYPES == ("situation", "indicator_monitoring", "needs_assessment")


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

    def test_stream_emits_images_and_persists(self):
        async def mock_astream(*a, **k):
            yield "## Overview\n"
            yield "Situation [1]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc(1)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain), \
             patch("api.routes.reports.report_images.generate_image",
                   return_value="data:image/png;base64,ZZZ"), \
             patch("api.routes.reports.report_images.extract_section_headings",
                   return_value=["Overview"]), \
             patch("api.routes.reports.settings_images_enabled", return_value=True):
            client = _client()
            resp = client.post("/reports/stream", json={"country": "Sudan", "language": "en"})
            events = _parse_sse_events(resp.text)
            kinds = [e["event"] for e in events]
            assert "images" in kinds
            img_ev = next(e for e in events if e["event"] == "images")
            assert img_ev["data"]["cover"] == "data:image/png;base64,ZZZ"
            assert img_ev["data"]["sections"] == [{"heading": "Overview", "image": "data:image/png;base64,ZZZ"}]
            rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
            rep = client.get(f"/reports/{rid}").json()
            assert rep["cover_image"] == "data:image/png;base64,ZZZ"
            assert rep["section_images"] == [{"heading": "Overview", "image": "data:image/png;base64,ZZZ"}]

    def test_stream_image_failure_saves_text_only(self):
        async def mock_astream(*a, **k):
            yield "## Overview\nText [1]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc(1)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain), \
             patch("api.routes.reports.report_images.generate_image", return_value=None), \
             patch("api.routes.reports.settings_images_enabled", return_value=True):
            client = _client()
            resp = client.post("/reports/stream", json={"country": "Sudan", "language": "en"})
            events = _parse_sse_events(resp.text)
            rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
            rep = client.get(f"/reports/{rid}").json()
            assert rep["cover_image"] is None
            assert rep["section_images"] is None   # no images, but the report saved fine

    def test_stream_images_disabled_no_image_event(self):
        async def mock_astream(*a, **k):
            yield "## Overview\nText [1]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc(1)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain), \
             patch("api.routes.reports.settings_images_enabled", return_value=False):
            client = _client()
            resp = client.post("/reports/stream", json={"country": "Sudan", "language": "en"})
            events = _parse_sse_events(resp.text)
            assert "images" not in [e["event"] for e in events]

    def test_get_report_not_owner_404(self):
        from rag import reports as store
        store.create_report(
            "rX", "someone-else", country="Sudan", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        client = _client()
        assert client.get("/reports/rX").status_code == 404
        assert client.delete("/reports/rX").status_code == 404

    def test_get_report_deleted_between_owner_check_and_fetch_404(self):
        # TOCTOU: is_owner passes, then the row is deleted before get_report fetches
        # it (returns None). Must be a graceful 404, never a 500.
        with patch("api.routes.reports.report_store.is_owner", return_value=True), \
             patch("api.routes.reports.report_store.get_report", return_value=None):
            r = _client().get("/reports/whatever")
        assert r.status_code == 404

    def test_delete_own_report(self):
        from rag import reports as store
        store.create_report(
            "rD", "test-user", country="Sudan", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        client = _client()
        assert client.delete("/reports/rD").status_code == 200
        assert client.get("/reports/rD").status_code == 404

    def test_stream_invalid_report_type_rejected(self):
        r = _client().post("/reports/stream", json={"country": "Sudan", "report_type": "bogus_type"})
        assert r.status_code == 422

    def test_stream_indicator_monitoring_persists_type(self):
        async def mock_astream(*args, **kwargs):
            yield "## Overview\n"
            yield "Situation dire [1]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream

        with patch("api.routes.reports.retrieve_for_report", new=AsyncMock(return_value=[_doc(1)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain) as mock_build_chain:
            client = _client()
            resp = client.post("/reports/stream", json={
                "country": "Mali", "report_type": "indicator_monitoring", "language": "en",
            })
            assert resp.status_code == 200
            events = _parse_sse_events(resp.text)
            rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
            mock_build_chain.assert_called_once_with("indicator_monitoring")

            full = client.get(f"/reports/{rid}").json()
            assert full["report_type"] == "indicator_monitoring"
            lst = client.get("/reports/list").json()["reports"]
            assert next(r for r in lst if r["id"] == rid)["report_type"] == "indicator_monitoring"

    def test_legacy_null_report_type_normalizes_to_situation(self):
        """A report row inserted before the report_type column existed (NULL) reads
        back as 'situation' through the API, never a bare null."""
        from rag.db import get_engine
        from sqlalchemy import text as sqltext
        from rag import reports as store

        store.create_report(
            "r-legacy", "test-user", country="Sudan", theme=None, date_from=None, date_to=None,
            language="en", title="t", content="c", sources=None, doc_count=1,
        )
        with get_engine().begin() as conn:
            conn.execute(sqltext("UPDATE reports SET report_type = NULL WHERE id = :id"),
                        {"id": "r-legacy"})

        client = _client()
        lst = client.get("/reports/list").json()["reports"]
        row = next(r for r in lst if r["id"] == "r-legacy")
        assert row["report_type"] == "situation"
        full = client.get("/reports/r-legacy").json()
        assert full["report_type"] == "situation"

    def test_report_types_constant_matches_api_literal(self):
        from rag.report_service import REPORT_TYPES
        from api.routes.reports import ReportRequest
        literal_values = ReportRequest.model_fields["report_type"].annotation.__args__
        assert set(REPORT_TYPES) == set(literal_values)


class TestReportPdf:
    _CONTENT = ("## Executive Summary\nConflict worsened [1].\n\n"
                "## Key Findings\n### Health\n- Outbreak reported [2].")
    _SOURCES = [
        {"index": 1, "title": "WFP Report", "url": "https://reliefweb.int/r/1", "source": "WFP", "date": "2026-01-01"},
        {"index": 2, "title": "WHO Report", "url": "https://reliefweb.int/r/2", "source": "WHO", "date": "2026-02-01"},
    ]

    def test_render_pdf_bytes(self):
        from rag.report_pdf import render_report_pdf
        pdf = render_report_pdf({
            "country": "Sudan", "theme": None, "date_from": "2026-01-01", "date_to": "2026-06-30",
            "doc_count": 2, "content": self._CONTENT, "sources": self._SOURCES,
        })
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000

    def test_render_pdf_turkish(self):
        from rag.report_pdf import render_report_pdf
        pdf = render_report_pdf({
            "country": "Sudan", "theme": "Sağlık", "date_from": None, "date_to": None,
            "doc_count": 1, "content": "## Yönetici Özeti\nÇatışma ve güvensizlik şiddetli [1].",
            "sources": None,
        })
        assert pdf[:4] == b"%PDF"

    def test_pdf_endpoint_owner(self):
        from rag import reports as store
        store.create_report(
            "rpdf", "test-user", country="Sudan", theme=None, date_from="2026-01-01",
            date_to="2026-06-30", language="en", title="t", content=self._CONTENT,
            sources=self._SOURCES, doc_count=2,
        )
        r = _client().get("/reports/rpdf/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF"

    def test_pdf_endpoint_not_owner_404(self):
        from rag import reports as store
        store.create_report(
            "rpdf2", "someone-else", country="Sudan", theme=None, date_from=None,
            date_to=None, language="en", title="t", content="c", sources=None, doc_count=1,
        )
        assert _client().get("/reports/rpdf2/pdf").status_code == 404

    def test_pdf_deleted_between_owner_check_and_fetch_404(self):
        # TOCTOU: is_owner passes, then the row is deleted before get_report fetches
        # it (returns None). Must be a graceful 404, never a 500 from render_report_pdf(None).
        from unittest.mock import patch
        with patch("api.routes.reports.report_store.is_owner", return_value=True), \
             patch("api.routes.reports.report_store.get_report", return_value=None):
            r = _client().get("/reports/whatever/pdf")
        assert r.status_code == 404

    def test_long_url_source_renders(self):
        # A long ReliefWeb slug URL must render — it wraps via the fixed table layout (CJK word-wrap)
        # instead of overflowing the right margin — without raising.
        from rag.report_pdf import render_report_pdf
        long_url = "https://reliefweb.int/report/democratic-republic-congo/" + "x-" * 60 + "end"
        pdf = render_report_pdf({
            "country": "DRC", "theme": None, "date_from": None, "date_to": None,
            "doc_count": 1, "content": "## Executive Summary\nText [1].",
            "sources": [{"index": 1, "title": "Long URL source", "url": long_url,
                         "source": "WFP", "date": "2026-05-22"}],
        })
        assert pdf[:4] == b"%PDF"

    def test_valid_sources_drives_cover_count(self):
        # The cover "Source reports" count is len(_valid_sources): entries missing a title/url are
        # excluded, so the cover number always equals the number of listed references.
        from rag.report_pdf import _valid_sources
        sources = [
            {"index": 1, "title": "A", "url": "u1"},
            {"index": 2, "title": "B", "url": "u2"},
            {"index": 3, "title": "no-url"},          # dropped
            {"index": 4, "url": "no-title"},           # dropped
        ]
        assert len(_valid_sources(sources)) == 2

    def test_type_label_defaults_and_maps(self):
        from rag.report_pdf import _type_label
        assert _type_label(None) == "M&E Situation Report"
        assert _type_label("situation") == "M&E Situation Report"
        assert _type_label("indicator_monitoring") == "M&E Indicator Monitoring Report"
        assert _type_label("needs_assessment") == "M&E Needs Assessment Brief"
        assert _type_label("unknown_type") == "M&E Situation Report"

    def test_render_pdf_with_indicator_table(self):
        from rag.report_pdf import render_report_pdf
        content = (
            "## Overview\nSituation remains dire [1].\n\n"
            "## Indicator Table\n"
            "| Indicator | Latest value | As of | Source |\n"
            "|---|---|---|---|\n"
            "| IPC Phase | Phase 4 | 2026-05-01 | [1] |\n\n"
            "## Data Gaps\nNo WASH data available.\n\n"
            "## Recent Developments\nAccess improved slightly [1]."
        )
        pdf = render_report_pdf({
            "country": "Mali", "theme": "Food and Nutrition", "date_from": None, "date_to": None,
            "doc_count": 1, "content": content,
            "sources": [{"index": 1, "title": "WFP Report", "url": "https://reliefweb.int/r/1",
                         "source": "WFP", "date": "2026-05-01"}],
            "report_type": "indicator_monitoring",
        })
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000

    # A 1x1 transparent PNG data URI (valid, tiny) for embedding tests.
    _PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
            "2mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

    def test_render_pdf_with_cover_and_section_images(self):
        from rag.report_pdf import render_report_pdf
        sources = [{"index": 1, "title": "WFP", "url": "https://reliefweb.int/r/1",
                    "source": "WFP", "date": "2026-05-01"}]
        pdf = render_report_pdf({
            "country": "Sudan", "theme": None, "date_from": None, "date_to": None,
            "doc_count": 1, "report_type": "situation",
            "content": "## Executive Summary\nText [1].\n\n## Outlook\nMore [1].",
            "sources": sources,
            "cover_image": self._PNG,
            "section_images": [{"heading": "Executive Summary", "image": self._PNG}],
        })
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000
        # the embedded PNG must materially grow the PDF vs the same report without images.
        # `sources` is kept identical to `pdf`'s so the delta isolates the image contribution
        # (a mismatched `sources` list alone shifts PDF size by 100+ bytes, which would make
        # this assert pass trivially even with no image embedded).
        from rag.report_pdf import render_report_pdf as _r
        bare = _r({"country": "Sudan", "theme": None, "date_from": None, "date_to": None,
                   "doc_count": 1, "report_type": "situation",
                   "content": "## Executive Summary\nText [1].\n\n## Outlook\nMore [1].",
                   "sources": sources})
        assert len(pdf) > len(bare) + 100

    def test_render_pdf_section_image_matches_apostrophe_heading(self):
        # Regression: Python-Markdown does not escape ' or " in heading text (only
        # & < >), so the section-image matcher must use the same quote=False escaping
        # or headings like "Women's Health" never match and silently drop their image.
        from rag.report_pdf import render_report_pdf
        sources = [{"index": 1, "title": "WFP", "url": "https://reliefweb.int/r/1",
                    "source": "WFP", "date": "2026-05-01"}]
        content = "## Women's Health\nText [1].\n\n## Outlook\nMore [1]."
        pdf = render_report_pdf({
            "country": "Sudan", "theme": None, "date_from": None, "date_to": None,
            "doc_count": 1, "report_type": "situation",
            "content": content, "sources": sources,
            "section_images": [{"heading": "Women's Health", "image": self._PNG}],
        })
        assert pdf[:4] == b"%PDF"
        bare = render_report_pdf({
            "country": "Sudan", "theme": None, "date_from": None, "date_to": None,
            "doc_count": 1, "report_type": "situation",
            "content": content, "sources": sources,
        })
        assert len(pdf) > len(bare) + 100

    def test_render_pdf_without_images_unchanged(self):
        # A report dict lacking image keys must still render (regression).
        from rag.report_pdf import render_report_pdf
        pdf = render_report_pdf({
            "country": "Sudan", "theme": None, "date_from": "2026-01-01", "date_to": "2026-06-30",
            "doc_count": 1, "content": "## Executive Summary\nText [1].", "sources": None,
        })
        assert pdf[:4] == b"%PDF"


class TestCitationNormalization:
    def test_cited_indices_handles_groups(self):
        from rag.citations import cited_indices
        assert cited_indices("a [1] b [2, 3] c [5].") == {1, 2, 3, 5}

    def test_grouped_citations_keep_all_sources(self):
        # The reported bug: grouped [1, 2, 3] dropped most sources from the list.
        from rag.citations import normalize_citations
        content = "Conflict and famine worsened [1, 2, 3]. Confirmed [3]."
        sources = [
            {"index": 1, "title": "A", "url": "u1"},
            {"index": 2, "title": "B", "url": "u2"},
            {"index": 3, "title": "C", "url": "u3"},
        ]
        c, s = normalize_citations(content, sources)
        assert {x["index"] for x in s} == {1, 2, 3}   # 3 survives via the separate "Confirmed [3]"
        assert "[1][2]" in c                          # expanded group, then capped to 2

    def test_renumbers_by_first_appearance_and_drops_uncited(self):
        from rag.citations import normalize_citations
        content = "Eighth [8] then third [3]."
        sources = [
            {"index": 3, "title": "C", "url": "u3"},
            {"index": 8, "title": "H", "url": "u8"},
            {"index": 5, "title": "uncited", "url": "u5"},
        ]
        c, s = normalize_citations(content, sources)
        assert [x["index"] for x in s] == [1, 2]
        assert [x["title"] for x in s] == ["H", "C"]
        assert "[1]" in c and "[2]" in c and "[8]" not in c and "[3]" not in c

    def test_drops_dead_marker(self):
        from rag.citations import normalize_citations
        content = "Real [1]. Hallucinated [9]."
        sources = [{"index": 1, "title": "A", "url": "u1"}]
        c, s = normalize_citations(content, sources)
        assert len(s) == 1 and s[0]["index"] == 1
        assert "[9]" not in c and "Hallucinated." in c

    def test_caps_long_citation_runs(self):
        import re as _re
        from rag.citations import normalize_citations
        content = "Broad claim [1][2][3][4][5][6][7]."
        sources = [{"index": i, "title": f"S{i}", "url": f"u{i}"} for i in range(1, 8)]
        c, s = normalize_citations(content, sources)
        run = _re.findall(r"(?:\[\d+\])+", c)[0]
        assert run.count("[") == 2   # consecutive pile capped to 2 (prompt drives one-per-fact)
        assert len(s) == 2           # overflow sources drop out

    def test_stream_stores_normalized_report(self):
        async def mock_astream(*a, **k):
            yield "## Summary\nConflict and famine worsened [1, 2, 3]. Confirmed [3]."

        mock_chain = MagicMock()
        mock_chain.astream = mock_astream
        with patch("api.routes.reports.retrieve_for_report",
                   new=AsyncMock(return_value=[_doc(1), _doc(2), _doc(3)])), \
             patch("api.routes.reports.build_report_chain", return_value=mock_chain):
            client = _client()
            resp = client.post("/reports/stream", json={"country": "Sudan", "language": "en"})
            events = _parse_sse_events(resp.text)
            rid = next(e for e in events if e["event"] == "saved")["data"]["report_id"]
            rep = client.get(f"/reports/{rid}").json()
            assert len(rep["sources"]) == 3            # grouped citation no longer drops sources
            assert "[1][2]" in rep["content"]          # group expanded, capped to 2, normalised
