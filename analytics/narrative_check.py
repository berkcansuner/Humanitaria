"""Deterministic check of the technical report's narrative against the findings.

The model is told to narrate the code-computed findings only, but a prompt cannot
enforce it. After generation this removes, sentence by sentence:

1. a sentence with a number that is not in the findings or the report directive
   (Turkish and English number formats, 'million'/'milyon' scale words and rounding
   to fewer decimals are accepted; small counts up to 10 are exempt);
2. a significance claim that contradicts the code's verdict in that finding's
   section (any claim, either way, in a finding that was not tested), and, outside
   the finding sections, a claim that something is significant when no finding is;
3. a relative-change claim the code did not compute: a change stated in percent
   ('fell by 32%', '%32 azaldı') is kept only when it is a count's computed relative
   change, or a share's computed percentage-point change said in percentage points;
   'halved' / 'doubled' / 'yarıya' / 'iki katına' and the like never about a share,
   and about a count only when the observed latest/first ratio is within ±10% of the
   factor. A level ('to 32%', '%32'ye', '%32 düzeyinde') is checked as a number only.

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
    """Every value the text states, plain and, after a scale word, scaled too
    ('2.3 million' allows 2.3 and 2,300,000)."""
    out = []
    for m in _NUMBER.finditer(text):
        scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
        for value, _ in _readings(m.group(1)):
            out += [value, value * scale] if scale != 1.0 else [value]
    return out


def _numbers_ok(sentence: str, allowed: list[float]) -> bool:
    for m in _NUMBER.finditer(sentence):
        scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
        readings = _readings(m.group(1))
        if any(d == 0 and scale == 1.0 and v <= _SMALL_COUNT for v, d in readings):
            continue
        # With a scale word the number is tried scaled and as written: a range such as
        # "9.5 to 35.0 million" carries the word only after its last number.
        tries = [(v * s, 0.5 * 10 ** -d * s) for v, d in readings for s in {scale, 1.0}]
        if not any(abs(v - a) <= tol + 1e-9 * max(1.0, a) for v, tol in tries for a in allowed):
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


# --- Relative-change claims (owner feedback 2026-11-18). A share (IPC 3+, % of the
# analysed population) changes in percentage points; "fell by 32%" or "halved" about it
# is a relative claim the code never computed. A count's relative change is legitimate
# only as computed (the trend's change along its line). ---

_PCT_EN = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)*)\s*(?:%|percent\b|per cent\b)", re.IGNORECASE)
_PCT_TR = re.compile(r"(?:%\s*|\byüzde\s+)(\d+(?:[.,]\d+)*)(?![\d.,]*\s*(?:yüzde\s+)?puan)",
                     re.IGNORECASE)
_PP = re.compile(r"percentage[- ]points?|yüzde\s+puan|\bpuan", re.IGNORECASE)
_QUALIFIER = {"about", "around", "nearly", "almost", "roughly", "approximately", "some",
              "over", "under", "just", "more", "than", "less", "only", "a", "an", "the"}
_EN_CHANGE_BEFORE = re.compile(
    r"^(?:by|up|down|rose|risen|rise|rises|rising|increased?|increases|increasing|grew|grown|"
    r"grows?|growing|fell|fallen|falls?|falling|dropped|drops?|dropping|declined?|declines|"
    r"declining|decreased?|decreases|decreasing|shrank|shrunk|climbed|surged|jumped|plunged|"
    r"slid|eased|gained|lost|cut|reduced|changed)$", re.IGNORECASE)
_EN_CHANGE_AFTER = re.compile(
    r"^(?:decline|drop|fall|increase|rise|reduction|decrease|gain|growth|jump|cut|lower|higher|"
    r"fewer|more|less|down|up|surge|change)\w*", re.IGNORECASE)
_EN_CHANGE_OF = re.compile(
    r"\b(?:decline|drop|fall|increase|rise|reduction|decrease|growth|change|jump|cut)s?\s+of\s*$",
    re.IGNORECASE)
# Turkish: a level takes a case or 'düzey' word after the number ("%32'ye", "%32'den",
# "%32 düzeyinde"); a change is followed by a change word ("%32 azaldı", "yüzde 32'lik
# bir düşüş", "%32 oranında arttı").
_TR_LEVEL_SUFFIX = re.compile(r"^['’](?:y?[ae]|[dt][ae]n?|s[ıi]|[ıiuü])\b", re.IGNORECASE)
_TR_CHANGE = re.compile(r"^(?:azal|art|düş|yüksel|geril|eksil|büyü|küçül|kayb|gerile)",
                        re.IGNORECASE)
_TR_FILLER = {"bir", "oranında", "civarında", "kadar", "dolayında", "lik", "lık", "luk", "lük"}

# Multiplicative words, with the factor they claim. Supported for a count when the
# observed latest/first ratio is within ±10% of the factor (halved: 0.45–0.55,
# doubled: 1.8–2.2, tripled: 2.7–3.3, quadrupled: 3.6–4.4); never for a share.
_MULTIPLIERS = [
    (0.5, re.compile(r"\bhalv(?:ed|es|ing|e)\b|\b(?:by|in) half\b|\bhalf as\b|"
                     r"yar[ıi]\s+yar[ıi]ya|\byar[ıi]ya\b|\byar[ıi]s[ıi]na\b", re.IGNORECASE)),
    (2.0, re.compile(r"\bdoubl(?:ed|es|ing)\b|\btwo-?fold\b|\btwice as\b|"
                     r"\bikiye\s+katla\w*|\biki\s+kat\w*", re.IGNORECASE)),
    (3.0, re.compile(r"\btripl(?:ed|es|ing)\b|\bthree-?fold\b|\bthree times\b|\büç\s+kat\w*",
                     re.IGNORECASE)),
    (4.0, re.compile(r"\bquadrupl\w*\b|\bfour-?fold\b|\bfour times\b|\bdört\s+kat\w*",
                     re.IGNORECASE)),
]
_FACTOR_TOLERANCE = 0.10


def _is_en_change(sentence: str, start: int, end: int) -> bool:
    before = [w.strip("(),;:").lower() for w in sentence[:start].split()]
    while before and before[-1] in _QUALIFIER:
        before.pop()
    if before and _EN_CHANGE_BEFORE.match(before[-1]):
        return True
    if _EN_CHANGE_OF.search(" ".join(before)):
        return True
    after = sentence[end:].split()
    return bool(after) and bool(_EN_CHANGE_AFTER.match(after[0].strip("(),;:.")))


def _is_tr_change(sentence: str, end: int) -> bool:
    rest = sentence[end:]
    if _TR_LEVEL_SUFFIX.match(rest):
        return False
    words = [w.strip("(),;:.'’").lower() for w in re.split(r"[\s'’]+", rest) if w.strip("'’")]
    while words and words[0] in _TR_FILLER:
        words.pop(0)
    return bool(words) and bool(_TR_CHANGE.match(words[0]))


def _percent_changes(sentence: str) -> list[float]:
    """The values of the percentages the sentence states as a change ('fell by 32%',
    'a 32% decline', '%32 azaldı', "yüzde 32'lik bir düşüş"), not as a level."""
    out = []
    for m in _PCT_EN.finditer(sentence):
        if _is_en_change(sentence, m.start(), m.end()):
            out += [v for v, _ in _readings(m.group(1))[:1]]
    for m in _PCT_TR.finditer(sentence):
        if _is_tr_change(sentence, m.end()):
            out += [v for v, _ in _readings(m.group(1))[-1:]]
    return out


def _matches(value: float, computed: list[float]) -> bool:
    """*value* as written equals a computed figure rounded to its decimals (or to a
    whole number)."""
    return any(abs(value - abs(c)) <= 0.5 + 1e-9 if value == int(value)
               else abs(value - abs(c)) <= 0.05 + 1e-9 for c in computed)


def _ratio(r: dict) -> float | None:
    """Observed latest / first value of a finding, or None."""
    if r.get("kind") == "snapshot" and r.get("values"):
        first, last = r["values"][0], r["values"][-1]
    else:
        first, last = r.get("first_value"), r.get("latest_value")
    return last / first if first and last is not None else None


def _profile(stat_results: list[dict]) -> dict:
    """What relative claims a stretch of text may make: the computed relative changes
    of counts, the percentage-point changes of shares, the observed count ratios, and
    whether it is about a share."""
    shares = [r for r in stat_results
              if r.get("unit") == "percentage points" or r.get("value_unit") == "%"]
    counts = [r for r in stat_results if r not in shares]
    return {
        "share": bool(shares) and not counts,
        "relative": [r["pct_change"] for r in counts if r.get("pct_change") is not None],
        "pp": [r["line_change"] for r in shares if r.get("line_change") is not None],
        "ratios": [x for x in (_ratio(r) for r in counts) if x],
    }


def _relative_claim_ok(sentence: str, profile: dict) -> bool:
    for value in _percent_changes(sentence):
        if profile["share"] or not _matches(value, profile["relative"]):
            # A share's change is in percentage points, and only as computed.
            if not (_PP.search(sentence) and _matches(value, profile["pp"])):
                return False
    for factor, pattern in _MULTIPLIERS:
        if pattern.search(sentence):
            if profile["share"] or not any(
                    abs(x - factor) <= _FACTOR_TOLERANCE * factor for x in profile["ratios"]):
                return False
    return True


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
    # None: the finding was not tested (no p-value), so it has no verdict at all.
    verdicts = {s.heading: (None if s.stat_result.get("tested") is False
                            else bool(s.stat_result.get("significant")))
                for s in findings.sections}
    any_significant = any(verdicts.values())
    # A finding section may claim its own computed changes; any other section (the
    # Executive Summary, the coverage and methods notes) those of the whole report.
    profiles = {s.heading: _profile([s.stat_result]) for s in findings.sections}
    whole = _profile([s.stat_result for s in findings.sections])
    whole["share"] = False

    def bad(sentence: str, section: str | None) -> bool:
        if not _numbers_ok(sentence, allowed):
            return True
        if not _relative_claim_ok(sentence, profiles.get(section or "", whole)):
            return True
        claim = _claim(sentence)
        if claim is None:
            return False
        if section in verdicts:
            if verdicts[section] is None:
                return True     # neither 'significant' nor 'not significant' was tested
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
