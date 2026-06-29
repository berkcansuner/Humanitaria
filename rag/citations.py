"""Citation normalisation for generated reports.

Server-side port of the frontend renumberCitations (frontend/src/utils/
renumberCitations.js): expand grouped citations, keep only the cited + displayable
sources, and renumber the inline [n] markers and the source list to a contiguous
1..N sequence by first appearance. Produces clean, self-consistent data for both
the stored report (PDF render) and the on-screen view, so the Sources section can
never go out of sync with the cited markers.
"""
import re

# A grouped citation like "[1, 3, 4]" (two or more numbers).
_GROUP_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)+)\]")
# A single citation "[n]" with an optional leading space (so a dropped marker takes
# its space with it instead of leaving a double space).
_SINGLE_RE = re.compile(r"( ?)\[(\d+)\]")

# Run of consecutive citations "[a][b][c]...". Used to cap a pile of citations down
# to the most relevant few, since RAG models tend to over-cite (one statement can
# arrive carrying 5-7 markers, which reads as clutter in a prose report).
_RUN_RE = re.compile(r"(?:\[\d+\]){2,}")
_MAX_CITES_PER_SPOT = 3


def expand_citation_groups(text: str) -> str:
    """'deteriorated [1, 3, 4]' -> 'deteriorated [1][3][4]' so the single-[n] logic
    below reaches every cited number."""
    if not text:
        return text
    return _GROUP_RE.sub(
        lambda m: "".join(f"[{n.strip()}]" for n in m.group(1).split(",")), text
    )


def cited_indices(text: str) -> set:
    """All citation numbers in *text*, handling both single [n] and grouped [n, m]."""
    out = set()
    for grp in _GROUP_RE.findall(text):
        out.update(int(n.strip()) for n in grp.split(","))
    for n in re.findall(r"\[(\d+)\]", text):
        out.add(int(n))
    return out


def _is_valid_source(s: dict) -> bool:
    """A source that can render as a listed reference: has url + title and is not a
    country-index artefact (mirrors rag.rag_context._is_displayable_source for dicts)."""
    if not s.get("url") or not s.get("title"):
        return False
    if s.get("doctype") == "country" and s.get("title") == s.get("country"):
        return False
    return True


def _cap_citation_runs(text: str) -> str:
    """Trim any run of consecutive citations to the first _MAX_CITES_PER_SPOT, so a
    statement carrying a pile of markers ('[1][2][3][4][5]') reads cleanly. Markers
    dropped here that appear nowhere else fall out of the source list downstream."""
    def _trim(m):
        markers = re.findall(r"\[\d+\]", m.group(0))
        return "".join(markers[:_MAX_CITES_PER_SPOT])
    return _RUN_RE.sub(_trim, text)


def normalize_citations(content: str, sources):
    """Expand grouped citations, keep only cited + valid sources, and renumber the [n]
    markers and the source list to a contiguous 1..N by first appearance.

    Returns ``(content, sources)``. A marker with no valid/cited source is dropped
    (with its leading space) so the reader never sees a dead [n]. Safe on already-clean
    or empty input.
    """
    if not content or not sources:
        return content, sources

    content = _cap_citation_runs(expand_citation_groups(content))
    valid = {
        s["index"]: s
        for s in sources
        if s.get("index") is not None and _is_valid_source(s)
    }

    # Cited indices in order of first appearance in the (expanded) text.
    order = []
    for m in _SINGLE_RE.finditer(content):
        idx = int(m.group(2))
        if idx in valid and idx not in order:
            order.append(idx)

    remap = {old: i + 1 for i, old in enumerate(order)}

    new_content = _SINGLE_RE.sub(
        lambda m: (f"{m.group(1)}[{remap[int(m.group(2))]}]"
                   if int(m.group(2)) in remap else ""),
        content,
    )
    new_sources = [{**valid[old], "index": remap[old]} for old in order]
    return new_content, new_sources
