"""M&E situation-report retrieval + directive helpers.

The report flow reuses the existing retrieval primitives (rag.retriever) and the
shared context assembly (rag.rag_context). This module owns the report-specific
pieces: fetching a wider, filter-scoped document set and composing the LLM
directive. The route layer (api/routes/reports.py) streams the report chain and
persists the result. Pure rag layer — no FastAPI/route imports.
"""
import logging
import re
from collections import defaultdict
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

# Minimum shared-prefix length (chars) before two same-source titles count as a
# republished/companion pair — guards against short coincidental shared openings.
_DUP_MIN_PREFIX = 25

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


# Metadata key memoising a document's detected language, so the two report filters
# (_prefer_english + _collapse_near_duplicates) each detect it only once per doc.
_LANG_META_KEY = "_detected_lang"


def _doc_lang(doc: Document) -> str:
    """Detected language for *doc*, computed once and cached on its metadata."""
    lang = doc.metadata.get(_LANG_META_KEY)
    if lang is None:
        lang = _detect_lang(doc.page_content)
        doc.metadata[_LANG_META_KEY] = lang
    return lang


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
    english = [d for d in docs if _doc_lang(d) == "en"]
    if english and len(english) / len(docs) >= _ENGLISH_DOMINANCE:
        return english
    return docs


def _norm_title(t: str) -> str:
    """Lowercase a title and collapse every run of non-alphanumerics to a single space."""
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def _is_prefix_title_dup(a: str, b: str) -> bool:
    """True when two normalised titles are equal, or the shorter is a word-boundary prefix of the
    longer — a base report and its extended '… : Insights and recommendations' companion. The length
    guard avoids collapsing reports that merely share a short opening; a monthly series whose titles
    differ only in the month (… ICSM Mars 2026 / … ICSM Avril 2026) is NOT a prefix of itself, so it
    is correctly left intact."""
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    short, long_ = sorted((na, nb), key=len)
    if short == long_:
        return True
    return len(short) >= _DUP_MIN_PREFIX and long_.startswith(short + " ")


def _collapse_near_duplicates(docs: List[Document]) -> List[Document]:
    """Collapse near-duplicate documents from the SAME organisation to one representative, so the LLM
    never sees — and never double-cites — the same underlying report twice. Within a source, two
    documents are duplicates when EITHER:
      (A) translation pair — same publication date but different detected content language (e.g. a WFP
          press release posted in both English and French); or
      (B) republished/companion — one title is a prefix of the other (see _is_prefix_title_dup).
    Distinct same-source reports survive: a monthly market series has different dates AND non-prefix
    titles, so neither rule fires. The kept representative prefers English, then the most recent date,
    then the fuller text — matching the single-citation rule's 'most authoritative/original, else most
    recent'. This is the retrieval-layer counterpart to the prompt's one-source-per-fact rule."""
    n = len(docs)
    if n < 2:
        return docs

    langs = [_doc_lang(d) for d in docs]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_source: dict = defaultdict(list)
    for i, d in enumerate(docs):
        src = (d.metadata.get("source") or "").strip().lower()
        if src:
            by_source[src].append(i)

    for idxs in by_source.values():
        for p in range(len(idxs)):
            for q in range(p + 1, len(idxs)):
                i, j = idxs[p], idxs[q]
                di, dj = docs[i], docs[j]
                same_date = bool(di.metadata.get("date")) and di.metadata.get("date") == dj.metadata.get("date")
                diff_lang = langs[i] != "unknown" and langs[j] != "unknown" and langs[i] != langs[j]
                if _is_prefix_title_dup(di.metadata.get("title"), dj.metadata.get("title")) or (same_date and diff_lang):
                    union(i, j)

    clusters: dict = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    def rep_key(i: int):
        d = docs[i]
        return (1 if langs[i] == "en" else 0, d.metadata.get("date") or "", len(d.page_content or ""), -i)

    keep = {max(members, key=rep_key) for members in clusters.values()}
    return [d for i, d in enumerate(docs) if i in keep]


REPORT_TYPES = ("situation", "indicator_monitoring", "needs_assessment", "technical_monitoring")

_REPORT_TYPE_TITLE_PREFIX = {
    "indicator_monitoring": "Indicator Monitoring Report — ",
    "needs_assessment": "Needs Assessment Brief — ",
    "technical_monitoring": "Technical Monitoring Report — ",
}

_REPORT_TYPE_DIRECTIVE_VERB = {
    "situation": "Generate the situation report.",
    "indicator_monitoring": "Generate the indicator monitoring report.",
    "needs_assessment": "Generate the needs assessment brief.",
    "technical_monitoring": "Generate the technical monitoring report narrative.",
}


def _retrieval_query(country: str, theme: Optional[str]) -> str:
    """Embedding/rerank query synthesized from the form (no natural-language query)."""
    if theme:
        return f"{country} {theme} humanitarian situation"
    return f"{country} humanitarian situation overview"


def _build_filters(country: str, theme: Optional[str],
                   date_from: Optional[str], date_to: Optional[str]) -> dict:
    """Filter dict in the shape rag.retriever expects (country / theme / date range).

    Always scoped to doctype="report": a disaster or country-index record has no
    source organisation (parse_disaster/parse_country both set source=""), and
    the report system prompt's citation rule (rag/chain.py _REPORT_SYSTEM_PROMPT,
    rule 7) attributes each cited fact to its source organisation — letting a
    non-report record slip into a situation report would produce a citation with
    a blank/garbled attribution. Chat retrieval is unaffected: a user can still
    ask about disasters there via the query processor's doctype filter.
    """
    filters: dict = {"country": country, "doctype": "report"}
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
                              top_k: Optional[int] = None,
                              report_type: str = "situation") -> List[Document]:
    """Fetch the document set to synthesize into one M&E report.

    Wider than chat retrieval (REPORT_TOP_K): candidates → date filter → dedupe by
    document → relevance rerank → mild recency blend → top-k. Filtered by
    country (+ optional theme) and the from–to date window. indicator_monitoring
    reports draw from a wider pool (a table of indicators needs broader source
    coverage than a narrative summary) unless the caller pins an explicit top_k.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.REPORT_TOP_K
        if report_type == "indicator_monitoring":
            top_k = max(top_k, 16)
    query = _retrieval_query(country, theme)
    filters = _build_filters(country, theme, date_from, date_to)

    candidate_k = top_k * settings.RERANK_CANDIDATE_MULTIPLIER
    retriever = build_retriever(filter=filters, k=candidate_k)
    docs = await retriever.ainvoke(query)
    docs = _prefer_english(docs)
    docs = apply_date_filter(docs, filters.get("date"))
    docs = dedupe_by_document(docs)
    docs = _collapse_near_duplicates(docs)
    docs = rerank_by_relevance(query, docs, top_k)
    docs = rerank_by_recency(docs)
    return docs[:top_k]


def report_title(country: str, theme: Optional[str], date_from: Optional[str],
                 date_to: Optional[str], report_type: str = "situation") -> str:
    """Human-readable saved-report title: 'Country · Sector · from–to', prefixed
    with the type label for non-situation reports (situation stays unprefixed,
    unchanged from the original single-type format)."""
    sector = theme or "All sectors"
    period = f"{date_from or '…'} – {date_to or '…'}"
    prefix = _REPORT_TYPE_TITLE_PREFIX.get(report_type, "")
    return f"{prefix}{country} · {sector} · {period}"


def build_report_directive(country: str, theme: Optional[str], date_from: Optional[str],
                           date_to: Optional[str], doc_count: int, language: str,
                           report_type: str = "situation") -> str:
    """The 'human' directive passed to the report chain alongside the context."""
    lang_name = _LANG_NAMES.get((language or "en").lower(), "English")
    sector = theme or "all sectors"
    verb = _REPORT_TYPE_DIRECTIVE_VERB.get(report_type, _REPORT_TYPE_DIRECTIVE_VERB["situation"])
    return (
        f"{verb} "
        f"Country: {country}. Sector(s): {sector}. "
        f"Period: {date_from or 'unspecified'} to {date_to or 'unspecified'}. "
        f"Source documents available: {doc_count}. "
        f"Write the entire report (including all headings) in {lang_name}."
    )
