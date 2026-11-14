"""Write side of the vector index: chunks + embeddings in Postgres (pgvector).

One transaction per call. ``upsert_chunks`` also upserts each document's row in the
``documents`` table, so the admin list and retention never have to scan the index.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy import text

from rag.db import connect

logger = logging.getLogger(__name__)

DOC_FIELDS = ("title", "url", "source", "country", "doctype", "date")


def vector_literal(values: Iterable[float]) -> str:
    """pgvector text form ('[0.1,0.2,...]'), cast to halfvec in SQL."""
    return "[" + ",".join(f"{v:.6g}" for v in values) + "]"


_UPSERT_CHUNK = text("""
    INSERT INTO chunks (id, doc_id, content, metadata, embedding,
                        country, theme, themes, doctype, source, format, date_ts)
    VALUES (:id, :doc_id, :content, CAST(:metadata AS jsonb), CAST(:embedding AS halfvec),
            :country, :theme, :themes, :doctype, :source, :format, :date_ts)
    ON CONFLICT (id) DO UPDATE SET
        doc_id = excluded.doc_id, content = excluded.content, metadata = excluded.metadata,
        embedding = excluded.embedding, country = excluded.country, theme = excluded.theme,
        themes = excluded.themes, doctype = excluded.doctype, source = excluded.source,
        format = excluded.format, date_ts = excluded.date_ts
""")

_UPSERT_DOCUMENT = text("""
    INSERT INTO documents (doc_id, title, url, source, country, doctype, date, updated_at)
    VALUES (:doc_id, :title, :url, :source, :country, :doctype, :date, :updated_at)
    ON CONFLICT (doc_id) DO UPDATE SET
        title = excluded.title, url = excluded.url, source = excluded.source,
        country = excluded.country, doctype = excluded.doctype, date = excluded.date,
        updated_at = excluded.updated_at
""")


def _chunk_row(chunk: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
    md = chunk["metadata"]
    return {
        "id": chunk["id"],
        "doc_id": md["doc_id"],
        "content": chunk["content"],
        "metadata": json.dumps(md, ensure_ascii=False),
        "embedding": vector_literal(embedding),
        "country": md.get("country") or "",
        "theme": md.get("theme") or "",
        "themes": md.get("themes") or None,
        "doctype": md.get("doctype") or "",
        "source": md.get("source") or "",
        "format": md.get("format") or "",
        "date_ts": int(md.get("date_ts") or 0),
    }


class VectorStore:
    """Chunks of the indexed documents, with their embeddings (pgvector)."""

    def clear_collection(self) -> None:
        """Delete every chunk and document row (full re-ingest)."""
        with connect() as conn:
            conn.execute(text("DELETE FROM chunks"))
            conn.execute(text("DELETE FROM documents"))
        logger.info("Cleared the vector index")

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not chunks:
            return
        now = datetime.now(timezone.utc).isoformat()
        documents: Dict[str, Dict[str, Any]] = {}
        for c in chunks:
            md = c["metadata"]
            documents.setdefault(md["doc_id"], {
                "doc_id": md["doc_id"], "updated_at": now,
                **{f: md.get(f) or "" for f in DOC_FIELDS}})
        with connect() as conn:
            conn.execute(_UPSERT_CHUNK, [_chunk_row(c, e) for c, e in zip(chunks, embeddings)])
            conn.execute(_UPSERT_DOCUMENT, list(documents.values()))
        logger.info("Upserted %d chunks (%d documents)", len(chunks), len(documents))

    def delete_document_chunks(self, doc_id: str, keep_ids: Optional[Set[str]] = None) -> None:
        """With *keep_ids*: prune the document's surplus chunks from an older, longer
        version (after an overwrite-upsert). Without: remove the document entirely."""
        with connect() as conn:
            if keep_ids is None:
                conn.execute(text("DELETE FROM chunks WHERE doc_id = :d"), {"d": doc_id})
                conn.execute(text("DELETE FROM documents WHERE doc_id = :d"), {"d": doc_id})
            else:
                conn.execute(text("DELETE FROM chunks WHERE doc_id = :d AND NOT (id = ANY(:keep))"),
                             {"d": doc_id, "keep": list(keep_ids)})

    def counts(self) -> Dict[str, int]:
        with connect() as conn:
            return {
                "chunks": conn.execute(text("SELECT count(*) FROM chunks")).scalar_one(),
                "documents": conn.execute(text("SELECT count(*) FROM documents")).scalar_one(),
            }


def get_store() -> VectorStore:
    return VectorStore()
