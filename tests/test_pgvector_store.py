"""Integration tests against a real Postgres + pgvector (the production vector index).

Run when TEST_DATABASE_URL points at a disposable Postgres with the pgvector
extension available (CI: the pgvector/pgvector service); skipped otherwise. The
tables are dropped and re-created per test, at a tiny embedding dimension.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from config import get_settings

PG_URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL not set")

# The fixture DROPs chunks/documents. A hosted database (Supabase's pooler may also
# ignore a search_path option) would lose the real corpus — refuse it outright.
if "supabase" in PG_URL:
    raise RuntimeError("TEST_DATABASE_URL must be a disposable local Postgres, not Supabase")

DIM = 3


@pytest.fixture
def pg():
    from rag import db
    real = get_settings()
    settings = MagicMock(DATABASE_URL=PG_URL, EMBED_DIM=DIM, CONVERSATION_DB_PATH="",
                         MMR_LAMBDA=0.5, TOP_K_RETRIEVAL=real.TOP_K_RETRIEVAL,
                         MMR_FETCH_K=real.MMR_FETCH_K, MMR_FETCH_K_CAP=real.MMR_FETCH_K_CAP,
                         RETENTION_DAYS=0, RETENTION_PER_COUNTRY_CAP=0)
    with patch("rag.db.get_settings", return_value=settings), \
         patch("rag.retriever.get_settings", return_value=settings):
        url = db._db_url()
        db._engines.pop(url, None)
        from sqlalchemy import create_engine
        eng = create_engine(url)
        with eng.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS chunks, documents")
        eng.dispose()
        engine = db.get_engine()   # re-creates the schema at DIM
        yield engine
        db._engines.pop(url, None)
        engine.dispose()


def _chunk(doc_id, i, content, **md):
    meta = {"doc_id": doc_id, "title": f"T {doc_id}", "url": f"https://r/{doc_id}",
            "country": "", "theme": "", "doctype": "report", "source": "OCHA",
            "format": "", "date": "2025-01-01", "date_ts": 20250101, **md}
    return {"id": f"{doc_id}_{i}", "content": content, "metadata": meta}


def _search(query_vec, filters=None, k=5, fetch_k=20):
    from rag import retriever
    with patch("rag.retriever.get_embeddings", return_value=MagicMock(embed_query=lambda q: query_vec)):
        return retriever.search("q", filters, k, fetch_k)


def test_upsert_writes_chunks_and_document_rows(pg):
    from ingestion.store import get_store
    store = get_store()
    store.upsert_chunks([_chunk("a", 0, "first", country="Yemen"), _chunk("a", 1, "second", country="Yemen")],
                        [[1, 0, 0], [0.9, 0.1, 0]])
    assert store.counts() == {"chunks": 2, "documents": 1}
    # Re-upserting the same ids overwrites in place (idempotent re-ingest).
    store.upsert_chunks([_chunk("a", 0, "first v2", country="Yemen")], [[1, 0, 0]])
    assert store.counts() == {"chunks": 2, "documents": 1}
    with pg.connect() as conn:
        assert conn.execute(text("SELECT content FROM chunks WHERE id='a_0'")).scalar_one() == "first v2"
        assert conn.execute(text("SELECT country FROM documents WHERE doc_id='a'")).scalar_one() == "Yemen"


def test_delete_prunes_surplus_chunks_or_the_whole_document(pg):
    from ingestion.store import get_store
    store = get_store()
    store.upsert_chunks([_chunk("a", i, f"c{i}") for i in range(3)], [[1, 0, 0]] * 3)
    store.delete_document_chunks("a", keep_ids={"a_0", "a_1"})   # newer, shorter version
    assert store.counts() == {"chunks": 2, "documents": 1}
    store.delete_document_chunks("a")                              # retention: whole document
    assert store.counts() == {"chunks": 0, "documents": 0}


def test_search_returns_nearest_documents_with_metadata(pg):
    from ingestion.store import get_store
    get_store().upsert_chunks(
        [_chunk("near", 0, "near text"), _chunk("far", 0, "far text")],
        [[1, 0, 0], [0, 0, 1]])
    docs = _search([1, 0.05, 0], k=1)
    assert [d.page_content for d in docs] == ["near text"]
    assert docs[0].metadata["doc_id"] == "near" and docs[0].metadata["url"] == "https://r/near"


def test_search_applies_country_alias_theme_and_date_filters(pg):
    from ingestion.store import get_store
    get_store().upsert_chunks([
        _chunk("syr-long", 0, "a", country="Syrian Arab Republic", theme="Health"),
        _chunk("syr-short", 0, "b", country="Syria", theme="Protection", themes=["Protection", "Health"]),
        _chunk("syr-old", 0, "c", country="Syria", theme="Health", date="2023-01-01", date_ts=20230101),
        _chunk("yem", 0, "d", country="Yemen", theme="Health"),
    ], [[1, 0, 0]] * 4)
    docs = _search([1, 0, 0], {"country": "Syria", "theme": "Health", "date": {"$gte": "2024-01-01"}})
    assert {d.metadata["doc_id"] for d in docs} == {"syr-long", "syr-short"}


def test_search_with_no_matches_is_empty(pg):
    assert _search([1, 0, 0], {"country": "Atlantis"}) == []


def test_tables_are_closed_to_supabase_api_roles(pg):
    with pg.connect() as conn:
        rls = dict(conn.execute(text(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('chunks','documents')")).all())
    assert rls == {"chunks": True, "documents": True}
