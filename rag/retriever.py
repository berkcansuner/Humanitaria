import logging
import math
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_chroma import Chroma
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from config import get_settings
from rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_vectorstore() -> VectorStore:
    settings = get_settings()
    embeddings = get_embeddings()
    if settings.VECTOR_STORE_PROVIDER == "pinecone":
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX)
        return PineconeVectorStore(
            index=index,
            embedding=embeddings,
            text_key="text",
            namespace=settings.PINECONE_NAMESPACE or None,
        )
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        persist_directory=settings.CHROMA_DB_PATH,
        embedding_function=embeddings,
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


def _build_chroma_filter(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a flat filter dict to explicit ChromaDB operator format.

    Chroma 1.0+ requires an explicit $and wrapper for multi-field queries.
    Single-field filters are passed as-is to avoid unnecessary wrapping.

    Country uses $in with both the canonical short name and the full ReliefWeb
    official name so queries work on both current data (full names) and
    future re-ingested data (normalized short names via parser).
    """
    if not filters:
        return None
    conditions = []
    for key, val in filters.items():
        if key == "date":
            # ChromaDB 1.5.9 only supports $gte/$lte for numeric values, not strings.
            # Date filtering is handled in Python after retrieval (see routes/chat.py).
            pass
        elif key == "country":
            full_name = _COUNTRY_RELIEFWEB_ALIASES.get(val)
            if full_name:
                conditions.append({key: {"$in": [val, full_name]}})
            else:
                conditions.append({key: {"$eq": val}})
        elif isinstance(val, dict):
            # Other operator dicts (e.g. {"$in": [...]}) passed through as-is
            conditions.append({key: val})
        else:
            conditions.append({key: {"$eq": val}})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


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

    Date is pushed into the DB as a numeric `date_ts` $gte range — the feature
    ChromaDB's string $gte could not provide.
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
        elif isinstance(val, dict):
            conditions[key] = val
        else:
            conditions[key] = {"$eq": val}
    return conditions or None


def build_retriever(filter: Optional[Dict[str, Any]] = None):
    vectorstore = _get_vectorstore()
    settings = get_settings()
    if settings.VECTOR_STORE_PROVIDER == "pinecone":
        store_filter = _build_pinecone_filter(filter)
    else:
        store_filter = _build_chroma_filter(filter)
    # When a date filter is present, fetch more candidates so post-filtering
    # in Python has enough docs to work with after the date cut.
    has_date_filter = isinstance(filter, dict) and "date" in filter
    fetch_k = settings.MMR_FETCH_K * 4 if has_date_filter else settings.MMR_FETCH_K
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.TOP_K_RETRIEVAL,
            "fetch_k": max(fetch_k, settings.TOP_K_RETRIEVAL),
            "lambda_mult": settings.MMR_LAMBDA,
            "filter": store_filter,
        },
    )


def apply_date_filter(docs: List[Document], date_filter: Optional[Dict[str, Any]]) -> List[Document]:
    """Post-retrieval date filter using Python string comparison (YYYY-MM-DD is lexicographic).

    ChromaDB 1.5.9 does not support $gte/$lte on string metadata fields,
    so date filtering is done here after retrieval.
    """
    if not date_filter or not isinstance(date_filter, dict):
        return docs
    date_from = date_filter.get("$gte", "")
    if not date_from:
        return docs
    return [d for d in docs if d.metadata.get("date", "0000-00-00") >= date_from]


def rerank_by_recency(docs: List[Document], decay_factor: Optional[float] = None) -> List[Document]:
    """Re-rank retrieved documents to prioritize recent ones.

    Blends MMR relevance position with exponential document recency:
    score = (1 - decay_factor) * mmr_rank_score + decay_factor * recency_score

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
        mmr_score = 1.0 / (1 + i)  # Position 0=1.0, 1=0.5, 2=0.33, ...
        if doc_date is not None:
            days_ago = max(0, (today - doc_date).days)
            recency_score = math.exp(-days_ago / 365.0)
        else:
            recency_score = 0.0
        blended = (1 - factor) * mmr_score + factor * recency_score
        scored.append((blended, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored]
