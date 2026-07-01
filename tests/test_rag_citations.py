"""Unit tests for rag.citations — citation normalisation for generated reports."""
from rag.citations import (
    expand_citation_groups,
    cited_indices,
    _is_valid_source,
    _cap_citation_runs,
    normalize_citations,
)


class TestExpandCitationGroups:
    def test_expands_grouped_to_singles(self):
        assert expand_citation_groups("deteriorated [1, 3, 4].") == "deteriorated [1][3][4]."

    def test_leaves_single_and_plain_text_untouched(self):
        assert expand_citation_groups("clashes [2] intensified.") == "clashes [2] intensified."

    def test_empty_is_safe(self):
        assert expand_citation_groups("") == ""


class TestCitedIndices:
    def test_collects_single_and_grouped(self):
        assert cited_indices("a [1] b [3, 4] c [1]") == {1, 3, 4}

    def test_empty_when_none(self):
        assert cited_indices("no citations here") == set()


class TestIsValidSource:
    def test_valid_with_url_and_title(self):
        assert _is_valid_source({"url": "http://x", "title": "T"}) is True

    def test_invalid_missing_url_or_title(self):
        assert _is_valid_source({"title": "T"}) is False
        assert _is_valid_source({"url": "http://x"}) is False

    def test_invalid_country_index_artefact(self):
        assert _is_valid_source(
            {"url": "http://x", "title": "Sudan", "doctype": "country", "country": "Sudan"}
        ) is False


class TestCapCitationRuns:
    def test_trims_run_to_two(self):
        assert _cap_citation_runs("access constrained [1][4][9][10].") == "access constrained [1][4]."

    def test_leaves_short_runs(self):
        assert _cap_citation_runs("a [1][2] b [3].") == "a [1][2] b [3]."


class TestNormalizeCitations:
    def _sources(self):
        return [
            {"index": 1, "url": "http://a", "title": "A"},
            {"index": 2, "url": "http://b", "title": "B"},
            {"index": 3, "url": "http://c", "title": "C"},
        ]

    def test_renumbers_contiguously_by_first_appearance(self):
        # Only sources 3 and 1 are cited (in that order) → remapped to 1, 2.
        content, sources = normalize_citations("First [3]. Then [1].", self._sources())
        assert content == "First [1]. Then [2]."
        assert [s["index"] for s in sources] == [1, 2]
        assert [s["title"] for s in sources] == ["C", "A"]

    def test_expands_group_then_renumbers(self):
        content, sources = normalize_citations("Both [1, 3] matter.", self._sources())
        assert content == "Both [1][2] matter."
        assert [s["title"] for s in sources] == ["A", "C"]

    def test_drops_marker_without_valid_source(self):
        # Source 2 is a country artefact → its [2] marker is dropped (with its space).
        sources = [
            {"index": 1, "url": "http://a", "title": "A"},
            {"index": 2, "url": "http://b", "title": "Sudan", "doctype": "country", "country": "Sudan"},
        ]
        content, out = normalize_citations("Valid [1] then dead [2].", sources)
        assert content == "Valid [1] then dead."
        assert [s["index"] for s in out] == [1]

    def test_empty_content_or_sources_is_safe(self):
        assert normalize_citations("", self._sources()) == ("", self._sources())
        assert normalize_citations("text [1]", []) == ("text [1]", [])
