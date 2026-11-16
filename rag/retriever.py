import json
import logging
import math
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores.utils import maximal_marginal_relevance
from pinecone import Pinecone
from sqlalchemy import text

from config import get_settings
from rag.db import connect
from rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)


# ReliefWeb stores some countries under their full official UN names.
# ingestion/parser._normalize_country_name strips these for new ingests,
# but existing data uses the full forms. Matching both covers either.
_COUNTRY_RELIEFWEB_ALIASES: Dict[str, str] = {
    "Iran":               "Iran (Islamic Republic of)",
    "Syria":              "Syrian Arab Republic",
    "Turkey":             "Türkiye",
    "State of Palestine": "occupied Palestinian territory",
    "Bolivia":            "Bolivia (Plurinational State of)",
    "Venezuela":          "Venezuela (Bolivarian Republic of)",
    "Moldova":            "Republic of Moldova",
    "Tanzania":           "United Republic of Tanzania",
    "South Korea":        "Republic of Korea",
    "North Korea":        "Democratic People's Republic of Korea",
}

# Filter keys that map 1:1 onto a chunks column (equality match).
_EQ_COLUMNS = ("doctype", "source", "format")


def _date_to_int(date_str: str) -> Optional[int]:
    """'2024-01-01' -> 20240101; invalid/empty -> None."""
    try:
        if isinstance(date_str, str) and date_str[:10].count("-") == 2:
            return int(date_str[:10].replace("-", ""))
    except (ValueError, AttributeError):
        pass
    return None


def build_sql_filter(filters: Optional[Dict[str, Any]]) -> Tuple[List[str], Dict[str, Any]]:
    """WHERE clauses (AND-ed) + bind params for the query-processor filters.

    Only known keys become SQL (column names are never taken from input); values are
    always bound. ``date`` is a numeric ``date_ts`` range ($gte, optional $lte);
    ``country`` also matches ReliefWeb's long official name; ``theme`` matches the
    primary theme or any entry of the multi-theme list."""
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    for key, val in (filters or {}).items():
        if key == "date":
            if isinstance(val, dict):
                ts_from = _date_to_int(val["$gte"]) if val.get("$gte") else None
                ts_to = _date_to_int(val["$lte"]) if val.get("$lte") else None
                if ts_from is not None:
                    clauses.append("date_ts >= :date_from")
                    params["date_from"] = ts_from
                if ts_to is not None:
                    clauses.append("date_ts <= :date_to")
                    params["date_to"] = ts_to
        elif not isinstance(val, str) or not val:
            logger.debug("Ignoring non-string filter %s=%r", key, val)
        elif key == "country":
            clauses.append("country = ANY(:countries)")
            params["countries"] = [val, *([_COUNTRY_RELIEFWEB_ALIASES[val]]
                                          if val in _COUNTRY_RELIEFWEB_ALIASES else [])]
        elif key == "theme":
            clauses.append("(theme = :theme OR :theme = ANY(themes))")
            params["theme"] = val
        elif key in _EQ_COLUMNS:
            clauses.append(f"{key} = :{key}")
            params[key] = val
        else:
            logger.debug("Ignoring unknown filter key %r", key)
    return clauses, params


def search(query: str, filters: Optional[Dict[str, Any]], k: int, fetch_k: int,
           lambda_mult: Optional[float] = None) -> List[Document]:
    """Nearest *fetch_k* chunks (cosine) under *filters*, then MMR down to *k*
    (lambda_mult, default MMR_LAMBDA).

    HNSW with iterative scan keeps filtered searches from coming back short (a
    plain HNSW scan stops after ef_search candidates, before the WHERE clause)."""
    settings = get_settings()
    query_vec = get_embeddings().embed_query(query)
    clauses, params = build_sql_filter(filters)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = text(f"""
        SELECT content, metadata, embedding::text AS emb,
               embedding <=> CAST(:q AS halfvec) AS dist
        FROM chunks {where}
        ORDER BY embedding <=> CAST(:q AS halfvec)
        LIMIT :fetch_k""")
    from ingestion.store import vector_literal
    with connect() as conn:
        conn.execute(text("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true)"))
        conn.execute(text("SELECT set_config('hnsw.ef_search', :ef, true)"),
                     {"ef": str(min(1000, max(40, fetch_k)))})
        rows = conn.execute(sql, {**params, "q": vector_literal(query_vec), "fetch_k": fetch_k}).fetchall()
    if not rows:
        return []
    rows = sorted(rows, key=lambda r: r.dist)   # relaxed_order may be slightly out of order
    picked = maximal_marginal_relevance(
        np.array(query_vec, dtype=np.float32),
        [json.loads(r.emb) for r in rows],
        lambda_mult=settings.MMR_LAMBDA if lambda_mult is None else lambda_mult,
        k=min(k, len(rows)),
    )
    return [Document(page_content=rows[i].content, metadata=dict(rows[i].metadata)) for i in picked]


class PgVectorRetriever(BaseRetriever):
    """LangChain retriever over the pgvector chunk table (MMR). ``ainvoke`` runs the
    blocking search in a worker thread (BaseRetriever's default async path)."""

    filters: Optional[Dict[str, Any]] = None
    k: int
    fetch_k: int
    lambda_mult: Optional[float] = None   # None → MMR_LAMBDA

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        return search(query, self.filters, self.k, self.fetch_k, self.lambda_mult)


def build_retriever(filter: Optional[Dict[str, Any]] = None, k: Optional[int] = None,
                    lambda_mult: Optional[float] = None):
    settings = get_settings()
    # k may be raised by the caller to fetch a larger candidate pool for
    # dedup + reranking; defaults to the final top-k.
    k = k or settings.TOP_K_RETRIEVAL
    # MMR only adds value when the candidate pool (fetch_k) is meaningfully larger
    # than k — otherwise it selects every candidate and the diversity step is a
    # no-op. The caller often raises k to a rerank pool (TOP_K * multiplier), so
    # scale fetch_k off k (not just the MMR_FETCH_K floor). Fetch even wider when a
    # date filter will thin the pool in Python afterwards.
    has_date_filter = isinstance(filter, dict) and "date" in filter
    fetch_multiplier = 12 if has_date_filter else 3
    # Cap the candidate pool: MMR is O(fetch_k * k) vector math on a constrained CPU,
    # and the date filter already runs in SQL, so a wider pool adds little recall.
    fetch_k = min(max(settings.MMR_FETCH_K, k * fetch_multiplier), settings.MMR_FETCH_K_CAP)
    return PgVectorRetriever(filters=filter or None, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult)


@lru_cache(maxsize=1)
def _get_pinecone_client() -> Pinecone:
    return Pinecone(api_key=get_settings().PINECONE_API_KEY)


def dedupe_by_document(docs: List[Document]) -> List[Document]:
    """Keep only the highest-ranked chunk per source document.

    Several chunks of the same report can rank together; collapsing them to one
    spreads the final top-k across distinct documents (better source diversity).
    """
    seen = set()
    out: List[Document] = []
    for doc in docs:
        key = doc.metadata.get("doc_id") or doc.metadata.get("url")
        if key in seen:
            continue
        seen.add(key)
        out.append(doc)
    return out


def rerank_by_relevance(query: str, docs: List[Document], top_n: int) -> List[Document]:
    """Re-score candidates against the query with Pinecone's hosted reranker.

    Adds a true query-relevance signal on top of MMR retrieval. Active only when
    RERANK_ENABLED and there is more than one doc; otherwise (or on any error)
    the original order is preserved (truncated to top_n) so a request never fails.
    """
    settings = get_settings()
    if not settings.RERANK_ENABLED or len(docs) <= 1:
        return docs[:top_n]
    try:
        result = _get_pinecone_client().inference.rerank(
            model=settings.RERANK_MODEL,
            query=query,
            documents=[doc.page_content for doc in docs],
            top_n=min(top_n, len(docs)),
            return_documents=False,
            # Chunks can exceed bge-reranker-v2-m3's 1024-token query+document limit
            # (legacy word-count chunks in the default namespace can be ~1700 tokens).
            # Without this the call 400s and the relevance signal is silently lost
            # to the MMR fallback below.
            parameters={"truncate": "END"},
        )
        reranked = []
        for item in result.data:
            doc = docs[item.index]
            # Attach the (0-1) relevance score so rerank_by_recency can blend it
            # with recency instead of the steep 1/(1+i) position fallback.
            doc.metadata["_relevance_score"] = float(item.score)
            reranked.append(doc)
        return reranked
    except Exception as e:
        logger.warning("Relevance rerank failed, keeping original order: %s", e)
        return docs[:top_n]


def apply_date_filter(docs: List[Document], date_filter: Optional[Dict[str, Any]]) -> List[Document]:
    """Post-retrieval date filter (YYYY-MM-DD lexicographic compare).

    Defensive layer on top of the SQL date_ts range filter.
    """
    if not date_filter or not isinstance(date_filter, dict):
        return docs
    date_from = date_filter.get("$gte", "")
    date_to = date_filter.get("$lte", "")
    if not date_from and not date_to:
        return docs

    def _in_range(d) -> bool:
        dt = d.metadata.get("date", "0000-00-00")
        if date_from and dt < date_from:
            return False
        if date_to and dt > date_to:
            return False
        return True

    return [d for d in docs if _in_range(d)]


def rerank_by_recency(docs: List[Document], decay_factor: Optional[float] = None) -> List[Document]:
    """Re-rank retrieved documents to prioritize recent ones.

    Blends a relevance component with exponential document recency:
    score = (1 - decay_factor) * relevance + decay_factor * recency_score

    relevance is the raw Pinecone reranker score (0-1) when present on every doc
    (set by rerank_by_relevance); otherwise it falls back to the position-based
    1/(1+i). Using the raw score lets recency matter among comparably-relevant
    docs, instead of the steep position decay pinning the top-ranked doc.

    recency_score = exp(-days_ago / 365)  — always positive, 1.0 at 0 days, ~0.37 at 1 yr
    Documents without a date get recency_score = 0.
    """
    if not docs:
        return docs

    settings = get_settings()
    if not settings.RERANK_BY_DATE:
        return docs

    factor = decay_factor if decay_factor is not None else settings.DATE_DECAY_FACTOR
    today = datetime.now()

    rel_scores = [doc.metadata.get("_relevance_score") for doc in docs]
    use_scores = len(docs) > 1 and all(s is not None for s in rel_scores)

    parsed_dates: List[Optional[datetime]] = []
    for doc in docs:
        date_str = doc.metadata.get("date", "")
        if date_str and len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
            try:
                parsed_dates.append(datetime.strptime(date_str[:10], "%Y-%m-%d"))
            except ValueError:
                parsed_dates.append(None)
        else:
            parsed_dates.append(None)

    scored = []
    for i, (doc, doc_date) in enumerate(zip(docs, parsed_dates)):
        # Raw Pinecone relevance score when available, else position fallback.
        relevance = rel_scores[i] if use_scores else 1.0 / (1 + i)
        if doc_date is not None:
            days_ago = max(0, (today - doc_date).days)
            recency_score = math.exp(-days_ago / 365.0)
        else:
            recency_score = 0.0
        blended = (1 - factor) * relevance + factor * recency_score
        scored.append((blended, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored]
