"""The narrow check on a next-period report's "What changed" section.

The main report prompt carries the comparison rules (rag.report_service
.build_comparison_block), but five live checks (2026-11-15) showed it applying them
unevenly from run to run: an August 2025 earthquake was "a significant new event"
in one run and gone in the next. After generation, one single-purpose call reads
only the section's numbered sentences and answers with the numbers to remove.

The code does the removing, so the check can only delete whole sentences: it never
adds or rewords text, and kept sentences keep their [n] markers (renumbered later
by normalize_citations like the rest of the report). Any failure (the call, its
JSON, a missing section) leaves the report as generated: the check must never
block a report.
"""
import logging
import re
from typing import Awaitable, Callable, NamedTuple, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# What the section says when every sentence was removed.
NO_CONFIRMED_CHANGE = {
    "en": "No change dated within this period could be confirmed from the sources.",
    "tr": "Kaynaklardan bu döneme tarihlenen bir değişiklik doğrulanamadı.",
}

class Checked(NamedTuple):
    """The report after the check, and how many sentences it removed (shown to the
    reader, since the saved text replaces what they watched stream)."""
    content: str
    removed: int


_PARAGRAPH = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_NEXT_SECTION = re.compile(r"^## (?!#)", re.MULTILINE)


def split_sentences(body: str) -> list[tuple[int, str]]:
    """(paragraph index, sentence) pairs, in order. A sentence ends at . ! or ?
    followed by whitespace, so decimals such as 5.6 stay whole."""
    out = []
    for p, para in enumerate(_PARAGRAPH.split(body.strip())):
        for sentence in _SENTENCE_END.split(para.strip()):
            if sentence.strip():
                out.append((p, sentence.strip()))
    return out


def remove_sentences(body: str, remove: set[int], language: str) -> str:
    """The body without the 1-based sentence numbers in ``remove``; paragraphs left
    empty disappear. With nothing left, one plain sentence says so."""
    paragraphs: dict[int, list[str]] = {}
    for n, (p, sentence) in enumerate(split_sentences(body), start=1):
        if n not in remove:
            paragraphs.setdefault(p, []).append(sentence)
    kept = [" ".join(s) for _, s in sorted(paragraphs.items())]
    if not kept:
        return NO_CONFIRMED_CHANGE.get(language, NO_CONFIRMED_CHANGE["en"])
    return "\n\n".join(kept)


def build_check_prompt(sentences: list[str], date_from: Optional[str],
                       date_to: Optional[str]) -> str:
    start = date_from or "the start of this period"
    period = f"{date_from or 'unspecified'} to {date_to or 'unspecified'}"
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(sentences, start=1))
    return (
        "You check one section of a humanitarian monitoring report, \"What changed since "
        f"the last report\". The report covers {period}. Its sentences are numbered below.\n\n"
        "Mark a sentence for removal when it presents something as new, as a change, or as "
        "a rise or fall, and:\n"
        f"1. the event, or the figure's reference date or year, is dated before {start} "
        "(e.g. an earthquake in 2025, a total \"in 2025\"), even if the previous report did "
        "not mention it; or\n"
        "2. the figure has no reference date and is presented as new or as a change; or\n"
        "3. it compares figures with different reference periods (e.g. a calendar-year "
        "total with a total over several months); or\n"
        "4. it calls a figure a change only because it is now given as a number (e.g. \"a "
        "specific figure not reported previously\").\n\n"
        "Keep:\n"
        "- sentences reporting a change that happened within the period, even when it "
        "started earlier (e.g. \"shipments stranded since October 2025 have now arrived\");\n"
        "- sentences saying something is unchanged, or is no longer reported;\n"
        "- sentences giving an older figure plainly as background, without calling it new "
        "or a change.\n\n"
        "Mark only sentences that meet a removal rule; when unsure, keep the sentence.\n"
        "Answer with JSON only: {\"remove\": [sentence numbers], \"why\": "
        "{\"<number>\": \"<short reason>\"}}.\n\n"
        f"Sentences:\n{numbered}"
    )


class CheckResult(BaseModel):
    remove: list[int] = Field(default_factory=list)
    why: dict[str, str] = Field(default_factory=dict)

    @field_validator("remove", mode="before")
    @classmethod
    def _numbers(cls, v):
        # Gemini sometimes sends numbers as strings; drop anything not a number.
        if not isinstance(v, list):
            return []
        return [int(x) for x in v if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]

    @field_validator("why", mode="before")
    @classmethod
    def _reasons(cls, v):
        return {str(k): str(r) for k, r in v.items()} if isinstance(v, dict) else {}


_checker_llm = None


def _get_checker_llm():
    global _checker_llm
    if _checker_llm is None:
        from langchain_openai import ChatOpenAI
        from config import get_settings
        s = get_settings()
        kwargs = dict(
            model=s.GEMINI_LLM_MODEL,
            base_url=s.GEMINI_BASE_URL,
            api_key=s.GEMINI_API_KEY,
            temperature=0.0,
            use_responses_api=False,  # Gemini's OpenAI-compatible API is Chat Completions only
            timeout=s.REPORT_LLM_TIMEOUT,
            max_retries=1,
        )
        if s.REPORT_REASONING_EFFORT:
            kwargs["reasoning_effort"] = s.REPORT_REASONING_EFFORT
        _checker_llm = ChatOpenAI(**kwargs).with_structured_output(CheckResult, method="json_mode")
    return _checker_llm


async def _llm_check(prompt: str) -> dict:
    result = await _get_checker_llm().ainvoke(prompt)
    return result.model_dump() if isinstance(result, BaseModel) else result


def _locate(content: str, heading: str) -> Optional[tuple[int, int]]:
    """(start, end) of the section body under '## <heading>', or None."""
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n", content, re.MULTILINE)
    if not m:
        return None
    nxt = _NEXT_SECTION.search(content, m.end())
    return m.end(), (nxt.start() if nxt else len(content))


async def verify_comparison(
    content: str, *, heading: str, date_from: Optional[str], date_to: Optional[str],
    language: str, checker: Optional[Callable[[str], Awaitable[dict]]] = None,
) -> Checked:
    """``content`` with the flagged sentences removed from its comparison section,
    and how many were removed. ``content`` comes back unchanged (0 removed) when
    there is no section, nothing is flagged, or the check fails in any way."""
    span = _locate(content, heading)
    if span is None:
        return Checked(content, 0)
    start, end = span
    region = content[start:end]
    body = region.strip()
    sentences = split_sentences(body)
    if not sentences:
        return Checked(content, 0)

    try:
        raw = await (checker or _llm_check)(
            build_check_prompt([s for _, s in sentences], date_from, date_to))
        result = CheckResult.model_validate(raw) if isinstance(raw, dict) and "remove" in raw \
            else None
    except Exception as exc:
        logger.warning("Comparison check failed; keeping the section as generated: %s", exc)
        return Checked(content, 0)
    if result is None:
        logger.warning("Comparison check gave no usable answer; keeping the section")
        return Checked(content, 0)

    remove = {n for n in result.remove if 1 <= n <= len(sentences)}
    if not remove:
        return Checked(content, 0)
    for n in sorted(remove):
        logger.info("Comparison check removed sentence %d (%s): %s",
                    n, result.why.get(str(n), "no reason given"), sentences[n - 1][1][:160])

    trailing = region[len(region.rstrip()):]
    leading = region[:len(region) - len(region.lstrip())]
    new_region = leading + remove_sentences(body, remove, language) + trailing
    return Checked(content[:start] + new_region + content[end:], len(remove))
