"""Unit tests for rag.rag_context — context + source assembly and cited-source filter."""
from langchain_core.documents import Document

from rag.rag_context import (
    _is_displayable_source,
    _build_context_and_sources,
    _filter_cited_sources,
)


def _doc(**md):
    return Document(page_content=md.pop("body", "text"), metadata=md)


class TestIsDisplayableSource:
    def test_valid(self):
        assert _is_displayable_source(_doc(url="http://x", title="T")) is True

    def test_missing_url_or_title(self):
        assert _is_displayable_source(_doc(title="T")) is False
        assert _is_displayable_source(_doc(url="http://x")) is False

    def test_country_index_artefact(self):
        assert _is_displayable_source(
            _doc(url="http://x", title="Sudan", doctype="country", country="Sudan")
        ) is False


class TestBuildContextAndSources:
    def test_numbers_displayable_and_builds_sources(self):
        docs = [
            _doc(body="alpha", url="http://a", title="A", date="2024-01-01"),
            _doc(body="beta", url="http://b", title="B", date="2024-02-02"),
        ]
        context, sources = _build_context_and_sources(docs)
        assert "[1] (2024-01-01) alpha" in context
        assert "[2] (2024-02-02) beta" in context
        assert [s["index"] for s in sources] == [1, 2]
        assert sources[0]["url"] == "http://a"

    def test_only_displayable_docs_are_numbered(self):
        docs = [
            _doc(body="artefact", url="http://c", title="Sudan", doctype="country", country="Sudan"),
            _doc(body="real", url="http://a", title="A"),
        ]
        context, sources = _build_context_and_sources(docs)
        # The country artefact is filtered out; the real doc becomes [1].
        assert "[1] (tarih yok) real" in context
        assert len(sources) == 1
        assert sources[0]["title"] == "A"

    def test_falls_back_to_raw_docs_when_all_artefacts(self):
        # Rare: a query that matched only country-index artefacts. The doc is kept as
        # context (so the prompt isn't empty); the source-list guard is only url+title,
        # so in this fallback the artefact does become a (single) source.
        docs = [_doc(body="only", url="http://c", title="Sudan", doctype="country", country="Sudan")]
        context, sources = _build_context_and_sources(docs)
        assert "[1] (tarih yok) only" in context
        assert len(sources) == 1
        assert sources[0]["index"] == 1


class TestFilterCitedSources:
    def _sources(self):
        return [{"index": 1, "title": "A"}, {"index": 2, "title": "B"}, {"index": 3, "title": "C"}]

    def test_keeps_only_cited(self):
        out = _filter_cited_sources("uses [1] and [3]", self._sources())
        assert [s["index"] for s in out] == [1, 3]

    def test_handles_grouped_citations(self):
        out = _filter_cited_sources("both [1, 2] here", self._sources())
        assert [s["index"] for s in out] == [1, 2]

    def test_falls_back_to_all_when_none_cited(self):
        out = _filter_cited_sources("no markers", self._sources())
        assert len(out) == 3
