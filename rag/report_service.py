"""M&E situation-report retrieval + directive helpers.

The report flow reuses the existing retrieval primitives (rag.retriever) and the
shared context assembly (rag.rag_context). This module owns the report-specific
pieces: fetching a wider, filter-scoped document set and composing the LLM
directive. The route layer (api/routes/reports.py) streams the report chain and
persists the result. Pure rag layer — no FastAPI/route imports.
"""
import logging

import anyio
import re
from collections import defaultdict
from datetime import date
from typing import List, Optional

import numpy as np
from langchain_core.documents import Document
from langdetect import DetectorFactory, detect

from config import get_settings
from rag.embeddings import get_embeddings
from rag.retriever import (
    build_retriever, apply_date_filter, dedupe_by_document,
    rerank_by_relevance,
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

# Same organisation, same day, different language is a translation only when the titles
# also say the same thing. Measured 2026-11-17 on 12 such pairs from chat candidate pools
# (gemini-embedding-001 title cosine): translations 0.85-0.96 (one Arabic/Spanish pair
# 0.72), distinct documents at most 0.68 (a WHO cholera sitrep vs an Ebola update; an IOM
# press release vs a Pashto DTM brief). A missed translation only leaves a duplicate.
_TRANSLATION_MIN_TITLE_COS = 0.8


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


def _translations(docs: List[Document], pairs: list) -> list:
    """The (i, j) *pairs* whose titles are the same title in two languages (title
    embedding cosine >= _TRANSLATION_MIN_TITLE_COS); none when embedding fails."""
    if not pairs:
        return []
    idx = sorted({i for pair in pairs for i in pair})
    try:
        vecs = get_embeddings().embed_documents([docs[i].metadata["title"] for i in idx])
    except Exception:
        logger.warning("Title embedding failed; same-day translations are not collapsed", exc_info=True)
        return []
    unit = {i: np.asarray(v) / np.linalg.norm(v) for i, v in zip(idx, vecs)}
    return [(i, j) for i, j in pairs if float(unit[i] @ unit[j]) >= _TRANSLATION_MIN_TITLE_COS]


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
      (A) translation pair — same publication date, different detected content language, and titles
          that mean the same (see _translations; e.g. a WFP press release posted in English and French); or
      (B) republished/companion — one title is a prefix of the other (see _is_prefix_title_dup).
    Distinct same-source reports survive: a monthly market series has different dates AND non-prefix
    titles, so neither rule fires. The kept representative prefers English, then the most recent date,
    then the fuller text — matching the single-citation rule's 'most authoritative/original, else most
    recent'. Documents that were already reranked (chat) keep instead the copy the reranker scored
    highest, so a translation it ranks low does not push the release out of the top-k. This is the
    retrieval-layer counterpart to the prompt's one-source-per-fact rule."""
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

    same_day_other_language = []
    for idxs in by_source.values():
        for p in range(len(idxs)):
            for q in range(p + 1, len(idxs)):
                i, j = idxs[p], idxs[q]
                di, dj = docs[i], docs[j]
                same_date = bool(di.metadata.get("date")) and di.metadata.get("date") == dj.metadata.get("date")
                diff_lang = langs[i] != "unknown" and langs[j] != "unknown" and langs[i] != langs[j]
                if _is_prefix_title_dup(di.metadata.get("title"), dj.metadata.get("title")):
                    union(i, j)
                elif same_date and diff_lang and di.metadata.get("title") and dj.metadata.get("title"):
                    same_day_other_language.append((i, j))
    for i, j in _translations(docs, same_day_other_language):
        union(i, j)

    clusters: dict = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    def rep_key(i: int):
        d = docs[i]
        return (d.metadata.get("_relevance_score", 0.0), 1 if langs[i] == "en" else 0,
                d.metadata.get("date") or "", len(d.page_content or ""), -i)

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


# Report retrieval (eval 2026-11-16, 6 countries × situation/indicator, May–Nov 2026):
# MMR (λ 0.5) cut the dense pool to ~56 documents before the reranker, and the final
# ranking ignored who published a document, so the latest document of each originator
# organisation reached the context 9% of the time (Yemen's indicator table missed IOM's
# 340,000 update). Now every document of the dense pool is reranked and the ranking
# weighs relevance 0.6, recency in the window 0.2 and an originator source 0.2, with at
# most two documents per organisation: 27%, originator share 54% -> 79%, mean relevance
# 0.833 -> 0.844 (weights 0.5/0.25/0.25 reached 30% at 0.813, 0.4/0.3/0.3 35% at 0.743).
# Re-run 2026-11-17: 25%. IOM's 340,000 update sat at dense rank 101, just past the
# rerank cap, so the newest document of each originator in the pool is now kept through
# the cap: 28%, Yemen 2/8 -> 4/8, relevance 0.869 -> 0.866. Most remaining misses score
# below 0.15 on relevance (weather forecasts, market bulletins, maps, meeting minutes) or
# are translations of an English document, so they are rightly left out.
_REPORT_POOL_CHUNKS = 256      # dense chunks under the filters; all their documents are reranked
_RERANK_MAX_DOCS = 100         # documents per rerank request
_W_RELEVANCE, _W_RECENCY, _W_ORIGINATOR = 0.6, 0.2, 0.2
_PER_SOURCE_CAP = 2
# Organisations that produce the figures humanitarian reports rely on.
ORIGINATORS = frozenset({
    "UN Office for the Coordination of Humanitarian Affairs", "International Organization for Migration",
    "UN High Commissioner for Refugees", "World Food Programme", "World Health Organization",
    "UN Children's Fund", "Food and Agriculture Organization of the United Nations",
    "Famine Early Warning System Network", "Integrated Food Security Phase Classification",
    "Health Cluster", "Nutrition Cluster", "Protection Cluster", "CCCM Cluster", "REACH Initiative",
})


def _doc_date(doc: Document) -> Optional[date]:
    try:
        return date.fromisoformat(str(doc.metadata.get("date"))[:10])
    except ValueError:
        return None


def _cap_keeping_newest_originators(docs: List[Document], limit: int) -> List[Document]:
    """The first *limit* documents in dense order, except that the newest document of
    each originator organisation in the pool is kept even when it ranks below the cut."""
    if len(docs) <= limit:
        return docs
    newest: dict = {}
    for i, d in enumerate(docs):
        source, when = d.metadata.get("source"), _doc_date(d)
        if source in ORIGINATORS and when and (source not in newest or when > newest[source][0]):
            newest[source] = (when, i)
    reserved = {i for _, i in newest.values()}
    rest = [i for i in range(len(docs)) if i not in reserved]
    keep = reserved | set(rest[:max(limit - len(reserved), 0)])
    return [d for i, d in enumerate(docs) if i in keep]


def _rank_for_report(docs: List[Document], date_from: Optional[str], date_to: Optional[str],
                     top_k: int) -> List[Document]:
    """Order reranked documents by relevance, recency within the report window and
    originator source; at most _PER_SOURCE_CAP per organisation while others remain."""
    dates = [_doc_date(d) for d in docs]
    known = [d for d in dates if d]
    start = date.fromisoformat(date_from) if date_from else (min(known) if known else date.today())
    end = date.fromisoformat(date_to) if date_to else date.today()
    span = max((end - start).days, 1)

    def score(i: int) -> float:
        d = docs[i]
        recency = min(1.0, max(0.0, (dates[i] - start).days / span)) if dates[i] else 0.0
        return (_W_RELEVANCE * d.metadata.get("_relevance_score", 0.0) + _W_RECENCY * recency
                + _W_ORIGINATOR * (d.metadata.get("source") in ORIGINATORS))

    order = sorted(range(len(docs)), key=score, reverse=True)
    picked, skipped, per_source = [], [], defaultdict(int)
    for i in order:
        source = docs[i].metadata.get("source")
        if per_source[source] < _PER_SOURCE_CAP:
            per_source[source] += 1
            picked.append(i)
        else:
            skipped.append(i)
    return [docs[i] for i in (picked + skipped)[:top_k]]


async def retrieve_for_report(country: str, theme: Optional[str],
                              date_from: Optional[str], date_to: Optional[str],
                              top_k: Optional[int] = None,
                              report_type: str = "situation") -> List[Document]:
    """Fetch the document set to synthesize into one M&E report.

    Wider than chat retrieval (REPORT_TOP_K): the dense pool under the country (+
    optional theme) and date filters → English preference → date filter → one chunk
    per document, near-duplicates collapsed → relevance rerank of every document →
    ranking by relevance, recency and originator source (_rank_for_report) → top-k.
    indicator_monitoring reports draw a wider set (a table of indicators needs broader
    source coverage than a narrative summary) unless the caller pins an explicit top_k.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.REPORT_TOP_K
        if report_type == "indicator_monitoring":
            top_k = max(top_k, 16)
    query = _retrieval_query(country, theme)
    filters = _build_filters(country, theme, date_from, date_to)

    retriever = build_retriever(filter=filters, k=_REPORT_POOL_CHUNKS)
    docs = await retriever.ainvoke(query)
    docs = _prefer_english(docs)
    docs = apply_date_filter(docs, filters.get("date"))
    docs = _cap_keeping_newest_originators(_collapse_near_duplicates(dedupe_by_document(docs)),
                                           _RERANK_MAX_DOCS)
    docs = await anyio.to_thread.run_sync(rerank_by_relevance, query, docs, len(docs))  # blocking Pinecone call
    return _rank_for_report(docs, date_from, date_to, top_k)


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
