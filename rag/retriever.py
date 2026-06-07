import logging
import math
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from config import get_settings
from rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_vectorstore() -> VectorStore:
    settings = get_settings()
    embeddings = get_embeddings()
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX)
    return PineconeVectorStore(
        index=index,
        embedding=embeddings,
        text_key="text",
        namespace=settings.PINECONE_NAMESPACE or None,
    )


# ReliefWeb stores some countries under their full official UN names.
# ingestion/parser._normalize_country_name strips these for new ingests,
# but existing data uses the full forms. $in covers both.
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


def _date_to_int(date_str: str) -> Optional[int]:
    """'2024-01-01' -> 20240101; invalid/empty -> None."""
    try:
        if isinstance(date_str, str) and date_str[:10].count("-") == 2:
            return int(date_str[:10].replace("-", ""))
    except (ValueError, AttributeError):
        pass
    return None


def _build_pinecone_filter(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pinecone metadata filter (keys are implicitly AND-ed).

    Date is pushed into the DB as a numeric `date_ts` $gte range for
    server-side date filtering.
    """
    if not filters:
        return None
    conditions: Dict[str, Any] = {}
    for key, val in filters.items():
        if key == "date":
            date_from = val.get("$gte") if isinstance(val, dict) else None
            ts = _date_to_int(date_from) if date_from else None
            if ts is not None:
                conditions["date_ts"] = {"$gte": ts}
        elif key == "country":
            full_name = _COUNTRY_RELIEFWEB_ALIASES.get(val)
            if full_name:
                conditions[key] = {"$in": [val, full_name]}
            else:
                conditions[key] = {"$eq": val}
        elif key == "theme":
            # Legacy records store a single `theme` string; enriched records store
            # all sector themes in a `themes` list. Match either so re-indexed data
            # gains multi-theme recall without regressing the existing namespace.
            conditions["$or"] = [{"theme": {"$eq": val}}, {"themes": {"$in": [val]}}]
        elif isinstance(val, dict):
            conditions[key] = val
        else:
            conditions[key] = {"$eq": val}
    return conditions or None


def build_retriever(filter: Optional[Dict[str, Any]] = None, k: Optional[int] = None):
    vectorstore = _get_vectorstore()
    settings = get_settings()
    # k may be raised by the caller to fetch a larger candidate pool for
    # dedup + reranking; defaults to the final top-k.
    k = k or settings.TOP_K_RETRIEVAL
    store_filter = _build_pinecone_filter(filter)
    # When a date filter is present, fetch more candidates so post-filtering
    # in Python has enough docs to work with after the date cut.
    has_date_filter = isinstance(filter, dict) and "date" in filter
    fetch_k = settings.MMR_FETCH_K * 4 if has_date_filter else settings.MMR_FETCH_K
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": max(fetch_k, k),
            "lambda_mult": settings.MMR_LAMBDA,
            "filter": store_filter,
        },
    )


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

    Defensive layer on top of Pinecone's server-side date_ts $gte filter.
    """
    if not date_filter or not isinstance(date_filter, dict):
        return docs
    date_from = date_filter.get("$gte", "")
    if not date_from:
        return docs
    return [d for d in docs if d.metadata.get("date", "0000-00-00") >= date_from]


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
