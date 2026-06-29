"""M&E situation-report retrieval + directive helpers.

The report flow reuses the existing retrieval primitives (rag.retriever) and the
shared context assembly (rag.rag_context). This module owns the report-specific
pieces: fetching a wider, filter-scoped document set and composing the LLM
directive. The route layer (api/routes/reports.py) streams the report chain and
persists the result. Pure rag layer — no FastAPI/route imports.
"""
import logging
from typing import List, Optional

from langchain_core.documents import Document
from langdetect import DetectorFactory, detect

from config import get_settings
from rag.retriever import (
    build_retriever, apply_date_filter, dedupe_by_document,
    rerank_by_relevance, rerank_by_recency,
)

logger = logging.getLogger(__name__)

# Deterministic language detection (langdetect is randomised by default).
DetectorFactory.seed = 0

_LANG_NAMES = {"tr": "Turkish", "en": "English"}

# Share-of-candidates threshold above which English is treated as dominant and the
# source set is filtered to English only. Tuned from ReliefWeb's language mix:
# anglophone crises (Sudan/Yemen/Afghanistan/Ukraine) sit at ~0.97-0.99 English, so
# they filter to English sources; francophone crises (DRC/Mali/Niger/CAR…) sit at
# ~0.43-0.56 English, so they fall below the bar and keep their French-majority set.
_ENGLISH_DOMINANCE = 0.6


def _detect_lang(text: str) -> str:
    """Best-effort ISO-639-1 code for *text* ('unknown' on failure/empty). Detect on a
    prefix — enough signal, and far cheaper than scanning a full report body."""
    try:
        return detect((text or "")[:1000])
    except Exception:
        return "unknown"


def _prefer_english(docs: List[Document]) -> List[Document]:
    """Adaptive source-language filter, decided from the candidate set's own mix.

    The index carries no usable language metadata, so language is detected from each
    document's content. When English clearly dominates (≥ _ENGLISH_DOMINANCE), keep
    only the English documents so an anglophone-crisis report cites English sources;
    otherwise return the candidates untouched so a francophone-crisis report keeps its
    French-majority sources instead of being gutted. No country list — purely the data.
    """
    if not docs:
        return docs
    english = [d for d in docs if _detect_lang(d.page_content) == "en"]
    if english and len(english) / len(docs) >= _ENGLISH_DOMINANCE:
        return english
    return docs


def _retrieval_query(country: str, theme: Optional[str]) -> str:
    """Embedding/rerank query synthesized from the form (no natural-language query)."""
    if theme:
        return f"{country} {theme} humanitarian situation"
    return f"{country} humanitarian situation overview"


def _build_filters(country: str, theme: Optional[str],
                   date_from: Optional[str], date_to: Optional[str]) -> dict:
    """Filter dict in the shape rag.retriever expects (country / theme / date range)."""
    filters: dict = {"country": country}
    if theme:
        filters["theme"] = theme
    date: dict = {}
    if date_from:
        date["$gte"] = date_from
    if date_to:
        date["$lte"] = date_to
    if date:
        filters["date"] = date
    return filters


async def retrieve_for_report(country: str, theme: Optional[str],
                              date_from: Optional[str], date_to: Optional[str],
                              top_k: Optional[int] = None) -> List[Document]:
    """Fetch the document set to synthesize into one situation report.

    Wider than chat retrieval (REPORT_TOP_K): candidates → date filter → dedupe by
    document → relevance rerank → mild recency blend → top-k. Filtered by
    country (+ optional theme) and the from–to date window.
    """
    settings = get_settings()
    top_k = top_k or settings.REPORT_TOP_K
    query = _retrieval_query(country, theme)
    filters = _build_filters(country, theme, date_from, date_to)

    candidate_k = top_k * settings.RERANK_CANDIDATE_MULTIPLIER
    retriever = build_retriever(filter=filters, k=candidate_k)
    docs = await retriever.ainvoke(query)
    docs = _prefer_english(docs)
    docs = apply_date_filter(docs, filters.get("date"))
    docs = dedupe_by_document(docs)
    docs = rerank_by_relevance(query, docs, top_k)
    docs = rerank_by_recency(docs)
    return docs[:top_k]


def report_title(country: str, theme: Optional[str],
                 date_from: Optional[str], date_to: Optional[str]) -> str:
    """Human-readable saved-report title: 'Country · Sector · from–to'."""
    sector = theme or "All sectors"
    period = f"{date_from or '…'} – {date_to or '…'}"
    return f"{country} · {sector} · {period}"


def build_report_directive(country: str, theme: Optional[str], date_from: Optional[str],
                           date_to: Optional[str], doc_count: int, language: str) -> str:
    """The 'human' directive passed to the report chain alongside the context."""
    lang_name = _LANG_NAMES.get((language or "en").lower(), "English")
    sector = theme or "all sectors"
    return (
        "Generate the situation report. "
        f"Country: {country}. Sector(s): {sector}. "
        f"Period: {date_from or 'unspecified'} to {date_to or 'unspecified'}. "
        f"Source documents available: {doc_count}. "
        f"Write the entire report (including all headings) in {lang_name}."
    )
