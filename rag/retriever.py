import logging
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from config import get_settings
from rag.embeddings import OllamaLangChainEmbeddings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    settings = get_settings()
    embeddings = OllamaLangChainEmbeddings()
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        persist_directory=settings.CHROMA_DB_PATH,
        embedding_function=embeddings,
    )


def build_retriever(filter: Optional[Dict[str, Any]] = None):
    vectorstore = _get_vectorstore()
    settings = get_settings()
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.TOP_K_RETRIEVAL, "filter": filter if filter else None}
    )


def rerank_by_recency(docs: List[Document], decay_factor: Optional[float] = None) -> List[Document]:
    """Re-rank retrieved documents to prioritize recent ones.

    Blends MMR relevance position with document recency:
    score = (1 - decay_factor) * mmr_rank_score + decay_factor * recency_score

    Documents without a date get recency_score = 0.
    Recency is computed as days-ago relative to today, normalized by 365 days.
    """
    if not docs:
        return docs

    settings = get_settings()
    if not settings.RERANK_BY_DATE:
        return docs

    factor = decay_factor if decay_factor is not None else settings.DATE_DECAY_FACTOR
    n = len(docs)
    today = datetime.now()

    # Parse dates and compute recency scores
    parsed_dates = []
    for doc in docs:
        date_str = doc.metadata.get("date", "")
        if date_str and len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
            try:
                parsed_dates.append(datetime.strptime(date_str[:10], "%Y-%m-%d"))
            except ValueError:
                parsed_dates.append(None)
        else:
            parsed_dates.append(None)

    # Compute blended scores
    scored = []
    for i, (doc, doc_date) in enumerate(zip(docs, parsed_dates)):
        mmr_score = 1.0 / (1 + i)  # Position 0=1.0, 1=0.5, 2=0.33, ...
        if doc_date is not None:
            days_ago = max(0, (today - doc_date).days)
            recency_score = max(0.0, 1.0 - (days_ago / 365.0))
        else:
            recency_score = 0.0
        blended = (1 - factor) * mmr_score + factor * recency_score
        scored.append((blended, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored]
