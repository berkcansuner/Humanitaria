"""Deterministic check of the technical report's narrative against the findings.

The model is told to narrate the code-computed findings only, but a prompt cannot
enforce it. After generation this removes, sentence by sentence:

1. a sentence with a number that is not in the findings or the report directive
   (Turkish and English number formats, 'million'/'milyon' scale words and rounding
   to fewer decimals are accepted; small counts up to 10 are exempt);
2. a significance claim that contradicts the code's verdict in that finding's
   section, and, outside the finding sections, a claim that something is
   significant when no finding is.

Headings are kept. A finding section left empty gets a placeholder sentence, and a
note at the end says how many sentences were removed. The check only deletes: it
never rewords or adds a claim.
"""
import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)


class NarrativeCheck(NamedTuple):
    content: str
    removed: int


_NOTE = {
    "en": "_Note: {n} sentence(s) that could not be verified against the computed statistics "
          "were removed from this report._",
    "tr": "_Not: Hesaplanan istatistiklerle doğrulanamayan {n} cümle rapordan çıkarıldı._",
}
_PLACEHOLDER = {
    "en": "The narrative for this finding could not be verified against the computed "
          "statistics and was removed.",
    "tr": "Bu bulgunun anlatımı hesaplanan istatistiklerle doğrulanamadığı için çıkarıldı.",
}

_NUMBER = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)*)(?:\s*(milyon|million|milyar|billion|bin|thousand)\b)?",
    re.IGNORECASE)
_SCALE = {"milyon": 1e6, "million": 1e6, "milyar": 1e9, "billion": 1e9,
          "bin": 1e3, "thousand": 1e3}
_SMALL_COUNT = 10

_CLAIM = re.compile(r"\bsignificant(?:ly)?\b|\banlaml[ıi](?!l[ıi]k)\w*", re.IGNORECASE)
_NEGATIVE_CLAIM = re.compile(r"\b(?:in|non-?)significant\b|\banlams[ıi]z", re.IGNORECASE)
_EN_NEGATION = re.compile(
    r"\b(?:not|no|non|neither|nor|without|lacks?|lacked|fails?|failed)\b|n't\b", re.IGNORECASE)
_TR_NEGATION = re.compile(
    r"de[ğg]il|olmay|\byok\b|m[ae]m[ae]kte|m[ae]m[ıiuü][şs]|m[ae]d[ıiuü]|m[ae]z\b", re.IGNORECASE)
_WINDOW = 4   # words before (English) / after (Turkish) a claim that can negate it

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _readings(token: str) -> list[tuple[float, int]]:
    """(value, decimals) for each way the token can be read: '.' or ',' as the
    decimal mark (the other one then groups thousands)."""
    out = []
    for decimal, thousands in ((".", ","), (",", ".")):
        t = token.replace(thousands, "")
        if t.count(decimal) > 1:
            continue
        try:
            value = float(t.replace(decimal, "."))
        except ValueError:
            continue
        out.append((value, len(t.split(decimal)[1]) if decimal in t else 0))
    return out


def _allowed_values(text: str) -> list[float]:
    return [value for m in _NUMBER.finditer(text) for value, _ in _readings(m.group(1))]


def _numbers_ok(sentence: str, allowed: list[float]) -> bool:
    for m in _NUMBER.finditer(sentence):
        scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
        readings = _readings(m.group(1))
        if any(d == 0 and scale == 1.0 and v <= _SMALL_COUNT for v, d in readings):
            continue
        if not any(abs(v * scale - a) <= 0.5 * 10 ** -d * scale + 1e-9 * max(1.0, a)
                   for v, d in readings for a in allowed):
            return False
    return True


def _claim(sentence: str) -> str | None:
    """'significant' / 'not significant' / None (no claim, or claims that disagree)."""
    polarities = set()
    if _NEGATIVE_CLAIM.search(sentence):
        polarities.add("not significant")
    for m in _CLAIM.finditer(sentence):
        before = " ".join(sentence[:m.start()].split()[-_WINDOW:])
        after = " ".join(sentence[m.start():].split()[:_WINDOW + 1])
        negated = _EN_NEGATION.search(before) or _TR_NEGATION.search(after)
        polarities.add("not significant" if negated else "significant")
    return polarities.pop() if len(polarities) == 1 else None


def _blocks(text: str) -> list[tuple[str, list[str]]]:
    """('heading', [line]) | ('para', [sentences]) | ('list', [items]) in order."""
    blocks: list[tuple[str, list[str]]] = []
    para: list[str] = []

    def flush():
        if not para:
            return
        if any(_LIST_ITEM.match(line) for line in para):
            blocks.append(("list", list(para)))
        else:
            joined = " ".join(line.strip() for line in para)
            blocks.append(("para", [s for s in _SENTENCE_END.split(joined) if s]))
        para.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            blocks.append(("heading", [line]))
        elif not line.strip():
            flush()
        else:
            para.append(line)
    flush()
    return blocks


def _heading_text(line: str) -> str:
    return line.lstrip("#").strip().strip("*").strip()


def verify_narrative(text: str, findings, allowed_text: str, language: str) -> NarrativeCheck:
    """*allowed_text*: the context and directive the model was given (its numbers are
    the only numbers the narrative may use)."""
    allowed = _allowed_values(allowed_text)
    verdicts = {s.heading: bool(s.stat_result.get("significant")) for s in findings.sections}
    any_significant = any(verdicts.values())

    def bad(sentence: str, section: str | None) -> bool:
        if not _numbers_ok(sentence, allowed):
            return True
        claim = _claim(sentence)
        if claim is None:
            return False
        if section in verdicts:
            return claim != ("significant" if verdicts[section] else "not significant")
        return claim == "significant" and not any_significant

    out: list[str] = []
    removed = 0
    section = None
    kept_here = removed_here = 0

    def close_section():
        # A finding the model did narrate, all of whose sentences failed the check.
        if section in verdicts and kept_here == 0 and removed_here:
            out.append(_PLACEHOLDER.get(language, _PLACEHOLDER["en"]))

    for kind, items in _blocks(text):
        if kind == "heading":
            close_section()
            section = _heading_text(items[0])
            kept_here = removed_here = 0
            out.append(items[0])
            continue
        kept = []
        for item in items:
            if bad(item, section):
                removed_here += 1
                logger.info("Technical report sentence removed (unverified): %s", item)
            else:
                kept.append(item)
        removed += len(items) - len(kept)
        kept_here += len(kept)
        if kept:
            out.append(("\n" if kind == "list" else " ").join(kept))
    close_section()

    if not removed:
        return NarrativeCheck(text, 0)
    out.append(_NOTE.get(language, _NOTE["en"]).format(n=removed))
    return NarrativeCheck("\n\n".join(out), removed)
