"""A country filter the corpus does not know would make the SQL search return nothing
("no documents found"); the chat route drops such a filter and searches unfiltered.
Since the filter-extraction fix the LLM sets a country for most questions, so a
name it spells differently from ReliefWeb ('DR Congo') must not empty the answer."""
from unittest.mock import MagicMock, patch

from api.routes import chat as chat_mod


def _known(*names):
    return patch.object(chat_mod, "corpus_countries", return_value=frozenset(n.lower() for n in names))


def test_unknown_country_is_dropped_other_filters_kept():
    with _known("Sudan", "Democratic Republic of the Congo"):
        out = chat_mod._drop_unknown_country({"country": "DR Congo", "theme": "Health"})
    assert out == {"theme": "Health"}


def test_known_country_is_kept_case_insensitively():
    with _known("Sudan"):
        assert chat_mod._drop_unknown_country({"country": "sudan"}) == {"country": "sudan"}


def test_filters_kept_when_the_corpus_countries_are_unavailable():
    with patch.object(chat_mod, "corpus_countries", return_value=None):
        assert chat_mod._drop_unknown_country({"country": "Atlantis"}) == {"country": "Atlantis"}


def test_plan_retrieval_applies_the_guard():
    with _known("Sudan"), \
         patch.object(chat_mod, "extract_filters", return_value={"country": "Narnia"}), \
         patch.object(chat_mod, "has_session", return_value=False), \
         patch.object(chat_mod.convo_store, "conversation_exists", return_value=False):
        assert chat_mod._plan_retrieval("s", "Narnia'da durum") == ("Narnia'da durum", {})


def test_corpus_countries_adds_short_alias_names_and_does_not_cache_failures():
    from rag import retriever

    retriever._corpus_countries = None
    with patch.object(retriever, "connect", side_effect=RuntimeError("db down")):
        assert retriever.corpus_countries() is None
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value = [("Syrian Arab Republic",), ("Sudan",)]
    with patch.object(retriever, "connect", return_value=conn):
        known = retriever.corpus_countries()
    assert {"syria", "syrian arab republic", "sudan"} <= known
    retriever._corpus_countries = None
