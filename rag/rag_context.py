"""Shared RAG context + source assembly.

Pure helpers that turn retrieved LangChain ``Document``s into the numbered prompt
context and the matching clickable-source dicts, and that filter sources down to
the ones the answer actually cited. Used by both the chat routes and the M&E
report service, so they live in the rag layer (no FastAPI / route dependency).
"""
import re

from rag.citations import cited_indices

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _is_displayable_source(doc) -> bool:
    """Whether a retrieved doc can become a clickable [n] source on the client.

    Mirrors the frontend's isValidSource (frontend/src/utils/sources.js): the doc
    needs a url + title and must not be a country-index artefact (a 'country'
    doctype whose title is just the country name). Kept in sync so the model is
    never handed a context entry it can cite but that has no clickable source —
    which is what left bracketed [3][4] markers as dead plain text.
    """
    md = doc.metadata
    if not md.get("url") or not md.get("title"):
        return False
    if md.get("doctype") == "country" and md.get("title") == md.get("country"):
        return False
    return True


def _build_context_and_sources(docs):
    """Number displayable docs [1..M] for the prompt and build matching source dicts.

    Only displayable docs (see _is_displayable_source) are numbered, so every
    inline [n] the model can cite maps to a source the client renders as a
    clickable chip. Falls back to the raw docs only if filtering would leave no
    context at all (rare: a query that matched nothing but index artefacts).
    """
    displayable = [d for d in docs if _is_displayable_source(d)]
    docs = displayable or docs
    context = "\n\n---\n\n".join(
        f"[{i}] ({doc.metadata.get('date') or 'tarih yok'}) {doc.page_content}"
        for i, doc in enumerate(docs, 1)
    )
    sources = [
        {
            "index": i,
            "title": doc.metadata.get("title", "Untitled"),
            "url": doc.metadata.get("url", ""),
            "date": doc.metadata.get("date"),
            "country": doc.metadata.get("country"),
            "source": doc.metadata.get("source"),
            "doctype": doc.metadata.get("doctype"),
        }
        for i, doc in enumerate(docs, 1)
        if doc.metadata.get("url") and doc.metadata.get("title")
    ]
    return context, sources


def _filter_cited_sources(answer_text: str, sources: list) -> list:
    """Keep only sources whose [n] marker appears in the answer.

    Falls back to all sources when the model emitted no (or no matching)
    citation markers, so the user never sees an empty source list.
    """
    cited = cited_indices(answer_text)  # handles single [n] and grouped [n, m, ...]
    if not cited:
        return sources
    filtered = [s for s in sources if s.get("index") in cited]
    return filtered or sources
