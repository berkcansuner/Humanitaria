"""Deterministic check of the one section of a technical report a model writes.

A technical monitoring report is written in code (analytics.report_text): every value,
date, test result and caveat comes from HDX HAPI data and is listed with its dataset. The
single exception is the "What changed since the last report" section of a next-period
report, which a model writes from the current findings and the previous report's text.
This drops, sentence by sentence, what that section must not say. Every rule is a presence
test (no scope, polarity or subject is parsed): a dropped sentence costs little, a kept
false one misleads. A sentence is dropped when it contains:

1. a number the model was not given (the findings and the previous report are the only
   sources; small counts up to ten are exempt; rounded quotes of large figures are accepted);
2. the vocabulary of statistics or of certainty ('significant', a test's name, 'proven',
   'beyond chance'; 'anlamlı', 'kesin', 'tesadüf'): the code states every verdict;
3. a multiplier, fraction, majority or record ('doubled', 'a third', 'most of'; 'iki
   katı', 'yarıya', 'çoğu', 'rekor'): none of them is computed;
4. a cause or a link between findings ('driven by', 'explains'; 'nedeni', 'kaynaklanıyor');
5. a capitalised name the model was not given (another country, a region not in the data);
6. 'overall', 'total', 'full' and the like, in a report whose figures are plan lines.

The check only deletes. What no word list can catch (a wrong direction stated without a
number, a detail the data does not hold) is left to the second, model-based check of this
section (rag.report_compare) and to the prompt.
"""
import logging
import math
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)


class Checked(NamedTuple):
    content: str | None     # the section's text without the dropped sentences (None: nothing left)
    removed: int


_NUMBER = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)*)"
    r"(?:\s*(milyon|million|milyar|billion|bin|thousand)(?:['’]?[a-zçğıöşüâîû]*)?\b)?",
    re.IGNORECASE)
_SCALE = {"milyon": 1e6, "million": 1e6, "milyar": 1e9, "billion": 1e9,
          "bin": 1e3, "thousand": 1e3}
_SMALL_COUNT = 10
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


# --- numbers -----------------------------------------------------------------------------

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


_ROUNDED_FROM = 10_000      # a figure this large may be quoted to 2-4 significant digits


def _rounded(value: float) -> list[float]:
    if abs(value) < _ROUNDED_FROM:
        return []
    digits = int(math.floor(math.log10(abs(value))))
    return [round(value, k - 1 - digits) for k in (2, 3, 4)]


def _matches_value(sentence_values: list[tuple[float, float]], allowed: list[float]) -> bool:
    """A number as written ((value, tolerance) readings) is an allowed value, or a
    rounding of a large one."""
    return any(abs(v - a) <= tol + 1e-9 * max(1.0, a) for v, tol in sentence_values for a in allowed) \
        or any(abs(v - r) <= 1e-6 * max(1.0, r) for v, _ in sentence_values
               for a in allowed for r in _rounded(a))


def _number_readings(m) -> list[tuple[float, float]]:
    scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
    # With a scale word the number is tried scaled and as written: a range such as
    # "9.5 to 35.0 million" carries the word only after its last number.
    return [(v * s, 0.5 * 10 ** -d * s) for v, d in _readings(m.group(1)) for s in {scale, 1.0}]


def _small_count(m) -> bool:
    return not m.group(2) and any(d == 0 and v <= _SMALL_COUNT for v, d in _readings(m.group(1)))


def _numbers_given(sentence: str, allowed: list[float]) -> bool:
    """Every number of the sentence is one the model was given (small counts exempt)."""
    return all(_small_count(m) or _matches_value(_number_readings(m), allowed)
               for m in _NUMBER.finditer(sentence))



# --- vocabulary --------------------------------------------------------------------------
# Word lists, deliberately wide.

_STATISTICS = re.compile(
    r"significan|anlaml[ıi]|anlams[ıi]z|\bp[- ]?values?\b|\bp[- ]?değer|\bp\s*[=<>≤≥]|"
    r"mann[- ]kendall|\bkendall|\bsen(?:'s|['’]in)?\s+(?:slope|eğim)|kruskal|pearson|\bholm\b|"
    r"bonferroni|confidence\s+interval|güven\s+aral[ıi]ğ|"
    r"\bstatistic\w*|\bchance\b|\bnoise\b|\brandom\w*|\bartefacts?\b|\bartifacts?\b|\bprov(?:e[nsd]?|ing)\b|"
    r"\bproof\b|\bconclusive\w*|\brobust\w*|\bsettled\b|\bbeyond\s+doubt\b|\bthreshold\w*|"
    r"\bevidential\b|\bevidence\b|\b(?:un)?reliabl\w*|\bfirm(?:ly)?\b|\bsolid\w*|\bcertain\w*|"
    r"\bdefinite(?:ly)?\b|\bdefinitive\w*|\bundeniabl\w*|\bunquestionabl\w*|\bweak\w*|\bstrong\w*|\btests?\s+confirm\w*|"
    r"\bistatisti\w*|\btesadüf\w*|\brastlant\w*|\bgürültü\w*|\bkanıt\w*|\bkesin\w*|\bsağlam\w*|"
    r"\bgüvenil\w*|\bsınama\w*|\bşüphesiz\w*|\bkuşkusuz\w*|\bzayıf\w*|\bgüçlü\w*|\beşi[kğ]\w*|"
    r"\bsonucu\s+(?:bunu\s+)?doğrul\w*", re.IGNORECASE)

# Multipliers, fractions, majorities, records, and figures written as words.
_PROPORTION = {
    "en": re.compile(
        r"\bhalv\w*|\bhalf\b|\bdoubl\w*|\btripl\w*|\bquadrupl\w*|\b\w+-?fold\b|\btwice\b|"
        r"\b(?:two|three|four|five|six|ten|several|many)\s+times\b|"
        r"\b(?:a|one|two|three)[- ](?:thirds?|quarters?|fourths?|fifths?|tenths?)\b|"
        r"\bone\s+in\s+\w+\b|\bfraction\b|"
        r"\bmajority\b|\bmost\s+of\b|\bthe\s+bulk\b|\blion['’]s\s+share\b|\brecord(?:s|ed)?\b|"
        r"\bunprecedented\b|\ball-time\b|\bever\b|\bon\s+record\b|"
        r"\b(?:highest|lowest|largest|smallest)\s+(?:level|point|caseload|figure|value)\b",
        re.IGNORECASE),
    "tr": re.compile(
        r"\bkat(?:[ıi]|[ıi]na|[ıi]ndan|l[ıi]k)?\b|\bkatla\w*|\byar[ıi](?:s[ıi]\w*|ya|dan)?\b|"
        r"\b(?:üçte|dörtte|beşte|onda)\b|\bçoğu\w*|\bçoğunlu[ğk]\w*|\brekor\w*|"
        r"\beşi\s+görülme\w*|\bbugüne\s+kadar\w*|\bşimdiye\s+kadar\w*|\btüm\s+zamanlar\w*|"
        r"\bzirve\w*|\btavan\w*|\bdibe\b|\bdip\b|\ben\s+(?:yüksek|düşük)\s+(?:seviye|düzey|nokta|rakam|değer)\w*",
        re.IGNORECASE),
}

# The whole of something, where the figures are lines of a plan.
_TOTALS = {
    "en": re.compile(
        r"\b(?:overall|totals?|entire\w*|whole|altogether|combined|sums?|summ\w*|aggregat\w*|"
        r"full|complete\w*|sector-wide|everyone|everybody|all\s+(?:people|those|persons))\b",
        re.IGNORECASE),
    "tr": re.compile(
        r"\btoplam\w*|\btoplan\w*|\bgenel\s+(?!olarak\b)\w+|\bgenel(?:i|inde|ini)\b|\btamam[ıi]\w*|"
        r"\btüm\w*|\bbütün\w*|\bherkes\w*|\bhepsi\w*", re.IGNORECASE),
}

# A cause, or a link between two findings: the findings state neither. (Plain 'because' /
# 'nedeniyle' stay: "because the series is short" is the caution we want.)
_CAUSE = {
    "en": re.compile(
        r"\bdriven\s+by\b|\bexplain\w*|\bresult(?:s|ed|ing)?\s+(?:of|from|in)\b|\breasons?\b|"
        r"\bthanks\s+to\b|\bstems?\s+from\b|\bstemm\w*|\battribut\w*|\bshows?\s+that\b|"
        r"\breflect(?:s|ed|ing)?\b|\bdue\s+to\b|\bcaus\w*|\bowing\s+to\b|\bas\s+a\s+result\b|"
        r"\bleads?\s+to\b|\bled\s+to\b|\bbecause\s+of\b|\bconsequence\w*|\bfuell?ed\b|\bfuell?ing\b",
        re.IGNORECASE),
    "tr": re.compile(
        r"\bneden(?:i|idir|leri|ler)\b|\bkaynaklan\w*|\baçıkl[ıa]\w*|\bsayesinde\b|\barkasında\b|"
        r"\byüzünden\b|\byol\s+aç\w*|\byansıt(?:ıyor|makta|tı|ır)\w*|"
        r"\w+[dt][ıiuü]ğ[ıiuü]n[ıiuü]\s+göster\w*|\bsonucudur\b|\bsonucunda\b|\btetikle\w*|\bbağlı\s+olarak\b",
        re.IGNORECASE),
}

# A name the model was not given: a region outside the ranking, another country, an agency.
_NAME = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-ZÇĞİÖŞÜ][a-zçğıöşüâîû]{2,})")


def _unknown_names(sentence: str, known: set[str]) -> bool:
    return any(m.group(1).casefold() not in known and m.group(1).lower() not in known
               for m in _NAME.finditer(sentence))


# --- the check ---------------------------------------------------------------------------

def _paragraphs(text: str, heading: str) -> list[list[str]]:
    """The sentences of each paragraph under *heading* in the model's text (list items
    count as sentences). Text under any other heading is not used; text before the first
    heading is, when the model wrote no heading at all."""
    wanted = " ".join(heading.casefold().split())
    has_heading = any(line.lstrip().startswith("#") for line in text.splitlines())
    inside = not has_heading
    out: list[list[str]] = []
    para: list[str] = []

    def flush():
        if para:
            if any(_LIST_ITEM.match(line) for line in para):
                out.append([_LIST_ITEM.sub("", line).strip() for line in para])
            else:
                joined = " ".join(line.strip() for line in para)
                out.append([s for s in _SENTENCE_END.split(joined) if s])
        para.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            inside = " ".join(line.lstrip("#").strip().strip("*").casefold().split()) == wanted
        elif not line.strip():
            flush()
        elif inside:
            para.append(line)
    flush()
    return out


def check_comparison(text: str, findings, allowed_text: str, language: str, heading: str,
                     label: str = "") -> Checked:
    """The model's "What changed" section (found under *heading*) without the sentences
    the rules above drop. *allowed_text*: the context and directive the model was given,
    the previous report included: the only source of its numbers and names. *label* names
    the report in the log of dropped sentences; the sentences are model-written report
    text, not user data."""
    lang = "tr" if language == "tr" else "en"
    allowed = _allowed_values(allowed_text)
    names = {w.casefold() for w in re.findall(r"[^\W\d_]{3,}", allowed_text)}
    names |= {w.lower() for w in re.findall(r"[^\W\d_]{3,}", allowed_text)}
    plan_lines = any(n.get("kind") == "plan_line" for n in findings.note_items) or any(
        s.stat_result.get("not_comparable") for s in findings.sections)

    def broken(sentence: str) -> str | None:
        """The rule the sentence breaks, or None."""
        if not _numbers_given(sentence, allowed):
            return "a number the model was not given"
        if _STATISTICS.search(sentence):
            return "statistical vocabulary"
        # A scale word after a checked number is part of that number.
        if _PROPORTION[lang].search(_NUMBER.sub(" ", sentence)):
            return "a multiplier, fraction, majority or record"
        if plan_lines and _TOTALS[lang].search(sentence):
            return "a total, in a report of plan lines"
        if _CAUSE[lang].search(sentence):
            return "a cause or a link between findings"
        if _unknown_names(sentence, names):
            return "a name the findings do not give"
        return None

    kept: list[str] = []
    removed = 0
    for sentences in _paragraphs(text, heading):
        good = []
        for sentence in sentences:
            rule = broken(sentence)
            if rule is None:
                good.append(sentence.strip())
            else:
                removed += 1
                logger.info("Comparison check dropped a sentence [%s] (%s): %s",
                            label or "report", rule, sentence)
        if good:
            kept.append(" ".join(good))
    return Checked("\n\n".join(kept) or None, removed)
