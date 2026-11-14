"""Row mapping of the pgvector store (ingestion/store.py). The SQL itself runs in
tests/test_pgvector_store.py against a real Postgres."""
import json

from ingestion.store import VectorStore, _chunk_row, get_store, vector_literal


def test_vector_literal_is_pgvector_text_form():
    assert vector_literal([0.5, -1, 1e-7]) == "[0.5,-1,1e-07]"


def test_chunk_row_maps_filter_columns_and_keeps_full_metadata():
    md = {"doc_id": "abc", "country": "Yemen", "theme": "Health", "themes": ["Health", "WASH"],
          "doctype": "report", "source": "OCHA", "format": "Situation Report",
          "date": "2025-02-03", "date_ts": 20250203, "url": "u", "title": "t"}
    row = _chunk_row({"id": "abc_0", "content": "body", "metadata": md}, [0.1, 0.2])
    assert row["id"] == "abc_0" and row["doc_id"] == "abc" and row["content"] == "body"
    assert row["embedding"] == "[0.1,0.2]"
    assert (row["country"], row["theme"], row["themes"]) == ("Yemen", "Health", ["Health", "WASH"])
    assert (row["doctype"], row["source"], row["format"], row["date_ts"]) == (
        "report", "OCHA", "Situation Report", 20250203)
    assert json.loads(row["metadata"]) == md


def test_chunk_row_defaults_for_missing_fields():
    row = _chunk_row({"id": "x_0", "content": "c", "metadata": {"doc_id": "x"}}, [1.0])
    assert row["themes"] is None and row["country"] == "" and row["date_ts"] == 0


def test_factory_returns_vector_store():
    assert isinstance(get_store(), VectorStore)
