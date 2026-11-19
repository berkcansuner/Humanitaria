"""Deterministic check of the model's interpretation paragraphs in a technical report.

The report's facts are written in code (analytics.report_text). The model adds one short
paragraph under the Executive Summary and under each finding, and this module drops,
sentence by sentence, what such a paragraph must not say. Every rule is a presence test:
no scope, polarity or subject is parsed, because a dropped interpretation sentence costs
nothing (the fact it would have restated is printed right above it), while a kept false
one misleads. A sentence is dropped when it contains:

1. a figure: anything but a year the findings name or a whole count up to ten;
2. the vocabulary of statistics or of certainty ('significant', a test's name, 'proven',
   'beyond chance', 'may be noise', 'kesin', 'tesadüf');
3. a multiplier, fraction, majority, record or a figure in words ('doubled', 'a third',
   'most of', 'millions'; 'iki katı', 'yarıya', 'çoğu', 'rekor');
4. a cause or a link between findings ('driven by', 'explains'; 'nedeni', 'kaynaklanıyor');
5. a capitalised name the model was not given (a region outside the ranking, another
   country);
6. the present ('currently', 'this year'; 'şu anda', 'güncel'): values carry their dates;
7. a word of change (rise, fall, stable, worse …): always in the Executive Summary and
   under a finding with no direction over time (a regional ranking, a correlation, years
   that are not comparable, a single value); under a finding with a direction, a
   sentence is kept only when it names that one direction and nothing else;
8. 'overall', 'total', 'full' and the like, in a report whose figures are plan lines.

The "What changed" section of a next-period report states figures by design: there rule
1 becomes "every number is one the model was given", rules 6 and 7 do not apply, the
others do.

What no word list can catch stays possible and is the prompt's job alone: a wrong order
among the regions the ranking names, an indicator the report does not have, a false
detail on a correct direction.

The check only deletes. Headings the report does not have are ignored with their text.
"""
import logging
import math
import re
from typing import NamedTuple

from analytics.report_text import COMMENTARY_LABEL, HEADINGS

logger = logging.getLogger(__name__)


class Commentary(NamedTuple):
    by_heading: dict        # heading -> the checked paragraph (headings with none are absent)
    comparison: str | None  # the checked "What changed" section, when the report has one
    removed: int


_NUMBER = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)*)"
    r"(?:\s*(milyon|million|milyar|billion|bin|thousand)(?:['’]?[a-zçğıöşüâîû]*)?\b)?",
    re.IGNORECASE)
_SCALE = {"milyon": 1e6, "million": 1e6, "milyar": 1e9, "billion": 1e9,
          "bin": 1e3, "thousand": 1e3}
_SMALL_COUNT = 10
_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_LABEL = re.compile(
    r"^\s*[*_]{0,2}(?:" + "|".join(re.escape(v.strip("*:")) for v in COMMENTARY_LABEL.values())
    + r")\s*:?[*_]{0,2}\s*:?\s*", re.IGNORECASE)


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


def _has_figure(sentence: str, years: set[str]) -> bool:
    """A number other than a small count or a year the findings name."""
    return any(not _small_count(m) and not (not m.group(2) and m.group(1) in years)
               for m in _NUMBER.finditer(sentence))


# --- vocabulary --------------------------------------------------------------------------
# Word lists, deliberately wide: losing a fine interpretation sentence costs nothing.

# Statistics, and how sure a finding is: the code states every verdict, so a paragraph
# may neither claim certainty ("proven", "beyond chance") nor deny it ("may be noise").
_STATISTICS = re.compile(
    r"significan|anlaml[ıi]|anlams[ıi]z|\bp[- ]?values?\b|\bp[- ]?değer|\bp\s*[=<>≤≥]|"
    r"mann[- ]kendall|\bkendall|\bsen(?:'s|['’]in)?\s+(?:slope|eğim)|kruskal|pearson|\bholm\b|"
    r"bonferroni|confidence\s+interval|güven\s+aral[ıi]ğ|"
    r"\bstatistic\w*|\bchance\b|\bnoise\b|\brandom\w*|\bartefacts?\b|\bartifacts?\b|\bprov(?:e[nsd]?|ing)\b|"
    r"\bproof\b|\bconclusive\w*|\brobust\w*|\bsettled\b|\bbeyond\s+doubt\b|\bthreshold\w*|"
    r"\bevidential\b|\bevidence\b|\b(?:un)?reliabl\w*|\bfirm(?:ly)?\b|\bsolid\w*|\bcertain\w*|"
    r"\bdefinit\w*|\bundeniabl\w*|\bunquestionabl\w*|\bweak\w*|\bstrong\w*|\btests?\s+confirm\w*|"
    r"\bistatisti\w*|\btesadüf\w*|\brastlant\w*|\bgürültü\w*|\bkanıt\w*|\bkesin\w*|\bsağlam\w*|"
    r"\bgüvenil\w*|\bsınama\w*|\bşüphesiz\w*|\bkuşkusuz\w*|\bzayıf\w*|\bgüçlü\w*|\beşi[kğ]\w*|"
    r"\bsonucu\s+(?:bunu\s+)?doğrul\w*", re.IGNORECASE)

# Multipliers, fractions, majorities, records, and figures written as words.
_PROPORTION = {
    "en": re.compile(
        r"\bhalv\w*|\bhalf\b|\bdoubl\w*|\btripl\w*|\bquadrupl\w*|\b\w+-?fold\b|\btwice\b|"
        r"\b(?:two|three|four|five|six|ten|several|many)\s+times\b|"
        r"\b(?:a|one|two|three)[- ](?:thirds?|quarters?|fourths?|fifths?|tenths?)\b|"
        r"\bone\s+in\s+\w+\b|\bfraction\b|\bmillions?\b|\bbillions?\b|\bthousands?\b|\bhundreds?\b|"
        r"\bpercent\w*|\bper\s+cent\b|"
        r"\bmajority\b|\bmost\s+of\b|\bthe\s+bulk\b|\blion['’]s\s+share\b|\brecord(?:s|ed)?\b|"
        r"\bunprecedented\b|\ball-time\b|\bever\b|\bon\s+record\b|"
        r"\b(?:highest|lowest|largest|smallest)\s+(?:level|point|caseload|figure|value)\b",
        re.IGNORECASE),
    "tr": re.compile(
        r"\bkat(?:[ıi]|[ıi]na|[ıi]ndan|l[ıi]k)?\b|\bkatla\w*|\byar[ıi](?:s[ıi]\w*|ya|dan)?\b|"
        r"\b(?:üçte|dörtte|beşte|onda)\b|\bçoğu\w*|\bçoğunlu[ğk]\w*|\brekor\w*|"
        r"\bmilyon\w*|\bmilyar\w*|\bbin(?:lerce)?\b|\byüzlerce\b|\byüzde\b|\bkişiden\b|"
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

# The present: a latest value is dated in its fact sentence, and may be years old.
_NOW = {
    "en": re.compile(r"\bcurrent(?:ly)?\b|\bthis\s+year\b|\btoday\b|\bnow\b|\bat\s+present\b|"
                     r"\bpresent(?:ly)?\b|\bso\s+far\b|\bto\s+date\b|\bongoing\b", re.IGNORECASE),
    "tr": re.compile(r"\bbu\s+yıl\w*|\biçinde\s+bulunduğumuz\b|\bşu\s+an\w*|\bh[aâ]lihaz[ıi]r\w*|"
                     r"\bbugün\w*|\bgüncel\w*|\bmevcut\s+durum\w*|\bhalen\b|\bhâlen\b", re.IGNORECASE),
}

_EN_RISE = re.compile(
    r"\b(?:ris(?:e|es|en|ing)|rose|increas\w*|grow(?:s|n|ing|th)?|grew|climb\w*|surg\w*|"
    r"jump\w*|gain(?:s|ed|ing)?|soar\w*|spik\w*|expand\w*|escalat\w*|mount(?:s|ed|ing)?|"
    r"swell\w*|balloon\w*|accelerat\w*|crept|creep\w*|higher|above|upward\w*|upturn|upswing|"
    r"uptick|up)\b", re.IGNORECASE)
_EN_FALL = re.compile(
    r"\b(?:fall(?:s|en|ing)?|fell|drop(?:s|ped|ping)?|declin\w*|decreas\w*|shr[aiu]nk\w*|"
    r"eas(?:ed|ing)|plung\w*|slid(?:e|es|ing)?|reduc\w*|lower(?:ed|ing|s)?|fewer|less|"
    r"dwindl\w*|contract(?:s|ed|ing|ion)|reced\w*|slow(?:s|ed|ing)?|trickle|taper\w*|"
    r"evaporat\w*|collaps\w*|dip(?:s|ped|ping)?|below|downward\w*|downturn|down)\b", re.IGNORECASE)
# Change whose direction the check cannot read (is "worse" up or down?), or no change at
# all: never kept, whatever the finding.
_EN_OTHER_CHANGE = re.compile(
    r"\b(?:stabl\w*|stabili[sz]\w*|steady|steadily|unchanged|constant|flat|plateau\w*|"
    r"worse\w*|deteriorat\w*|improv\w*|better|recover\w*|rebound\w*|peak\w*|revers\w*|"
    r"chang(?:e|es|ed|ing)|shift(?:s|ed|ing)?|fluctuat\w*|uninterrupted|"
    r"year\s+after\s+year|without\s+interruption)\b", re.IGNORECASE)

# Turkish verb forms after a stem: past (arttı), evidential (artmış), progressive
# (artıyor), aorist (artar), future (artacak), converbs (artarak, düşüp), verbal nouns
# (artış, azalma) and participles (artan). "artık" (any more), "düşük" (low), "büyük"
# (big) and "insani" (humanitarian) are not among them. A stem ending in a vowel narrows
# before -yor: gerile- -> geriliyor.
_TR_SUFFIXES = (r"[dt][ıiuü]\w*|m[ıiuü]ş\w*|[ıiuü]?yor\w*|(?:[ae]|[ıiuü])?r(?:l[ae]r|ken|d[ıi]r)?|"
                r"y?[ae]c[ae][kğ]\w*|y?[ae]r[ae]k|y?[ıiuü]p|m[ae]\w*|y?[ıiuü]ş\w*|y?[ae]n(?:l[ae]r\w*)?")


def _tr_verbs(*stems: str) -> str:
    forms = [f"{stem}(?:{_TR_SUFFIXES})" for stem in stems]
    forms += [f"{stem[:-1]}[ıiuü]yor\\w*" for stem in stems if stem[-1] in "ae"]
    return "|".join(forms)


_TR_RISE = re.compile(
    rf"^(?:{_tr_verbs('art', 'yüksel', 'büyü', 'çık', 'katlan', 'tırman', 'sıçra', 'genişle', 'fırla', 'kabar', 'hızlan')}"
    r"|yukarı(?!da)\w*|üzerinde|üstünde)$", re.IGNORECASE)
_TR_FALL = re.compile(
    rf"^(?:{_tr_verbs('azal', 'düş', 'gerile', 'eksil', 'küçül', 'daral', 'hafifle', 'eri', 'yavaşla', 'durul')}"
    r"|in(?:d[ıi]\w*|iyor\w*|miş\w*|erek|ip|ecek\w*)|iniş\w*|aşağı\w*|altında|altına)$", re.IGNORECASE)
_TR_OTHER_CHANGE = re.compile(
    rf"^(?:{_tr_verbs('değiş', 'kötüleş', 'iyileş', 'toparlan', 'dalgalan')}"
    r"|sabit\w*|istikrar\w*|durağan\w*|aynı|kesintisiz\w*)$", re.IGNORECASE)
# "daha yüksek / daha az": a comparison. ("En yüksek bölgeler" is the ranking's own wording.)
_TR_COMPARATIVE = re.compile(r"\bdaha\s+(?:(yüksek|fazla|çok|büyük)|(düşük|az|küçük))\w*", re.IGNORECASE)


# The prompt's own way of pointing at the computed paragraph is not a comparison.
_POINTER = re.compile(
    r"\b(?:results?|facts?|paragraphs?|verdicts?|values?|figures?|findings?|rankings?|text|stated|given|"
    r"shown|noted|described)\s+above\b|\babove[- ]mentioned\b|\byukarıda\w*", re.IGNORECASE)


def _tr_words(sentence: str) -> list[str]:
    return [w.strip("(),;:.!?“”\"'’") for w in re.split(r"[\s'’]+", sentence)]


def _change(sentence: str, language: str) -> tuple[bool, bool, bool]:
    """(rise, fall, other change), in the report's language."""
    sentence = _POINTER.sub(" ", sentence)
    if language == "tr":
        words = _tr_words(sentence)
        comparative = [m for m in _TR_COMPARATIVE.finditer(sentence)]
        return (any(_TR_RISE.match(w) for w in words) or any(m.group(1) for m in comparative),
                any(_TR_FALL.match(w) for w in words) or any(m.group(2) for m in comparative),
                any(_TR_OTHER_CHANGE.match(w) for w in words))
    return (bool(_EN_RISE.search(sentence)), bool(_EN_FALL.search(sentence)),
            bool(_EN_OTHER_CHANGE.search(sentence)))


def _direction(r: dict) -> int | None:
    """The one direction over time a sentence about this finding may state (+1 up, -1
    down): the tested direction of a trend, the move from the previous value to the latest
    of a short series. None when the finding has none (a ranking, a correlation, years that
    are not comparable, one value, no trend, values that do not move)."""
    if r["kind"] == "trend":
        return {"increasing": 1, "decreasing": -1}.get(r.get("direction"))
    if r["kind"] == "snapshot" and not r.get("not_comparable") and len(r.get("values") or []) > 1:
        previous, latest = r["values"][-2], r["values"][-1]
        return None if latest == previous else (1 if latest > previous else -1)
    return None


# A name the model was not given: a region outside the ranking, another country, an agency.
_NAME = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-ZÇĞİÖŞÜ][a-zçğıöşüâîû]{2,})")


def _unknown_names(sentence: str, known: set[str]) -> bool:
    return any(m.group(1).casefold() not in known and m.group(1).lower() not in known
               for m in _NAME.finditer(sentence))


# --- the check ---------------------------------------------------------------------------

def _sections(text: str) -> list[tuple[str, list[str]]]:
    """(heading, sentences) for each '## ' section of the model's text, in order; list
    items count as sentences. Text before the first heading is ignored."""
    out: list[tuple[str, list[str]]] = []
    para: list[str] = []

    def flush():
        if para and out:
            if any(_LIST_ITEM.match(line) for line in para):
                out[-1][1].extend(_LIST_ITEM.sub("", line).strip() for line in para)
            else:
                joined = " ".join(line.strip() for line in para)
                out[-1][1].extend(s for s in _SENTENCE_END.split(joined) if s)
        para.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            out.append((line.lstrip("#").strip().strip("*").strip(), []))
        elif not line.strip():
            flush()
        else:
            para.append(line)
    flush()
    return out


def _key(heading: str) -> str:
    return " ".join(heading.casefold().split())


def check_commentary(text: str, findings, allowed_text: str, language: str,
                     comparison_heading: str | None = None, label: str = "") -> Commentary:
    """The model's paragraphs, by the report's headings, without the sentences the rules
    above drop. *allowed_text*: the context and directive the model was given (the only
    source of the years a paragraph may name, and of the "What changed" section's
    numbers). *label* names the report in the log of dropped sentences; the sentences are
    model-written report text, not user data."""
    lang = "tr" if language == "tr" else "en"
    years = set(_YEAR.findall(allowed_text))
    names = {w.casefold() for w in re.findall(r"[^\W\d_]{3,}", allowed_text)}
    names |= {w.lower() for w in re.findall(r"[^\W\d_]{3,}", allowed_text)}
    allowed = _allowed_values(allowed_text)
    summary = HEADINGS[lang]["summary"]
    plan_lines = any(n.get("kind") == "plan_line" for n in findings.note_items) or any(
        s.stat_result.get("not_comparable") for s in findings.sections)
    known = {_key(summary): (summary, "summary", None)}
    known.update({_key(s.heading): (s.heading, "finding", s.stat_result) for s in findings.sections})
    if comparison_heading:
        known[_key(comparison_heading)] = (comparison_heading, "comparison", None)

    def broken(sentence: str, mode: str, stat: dict | None) -> str | None:
        """The rule the sentence breaks, or None."""
        # Under a regional ranking no region is named again: a wrong order cannot be read
        # by a word list, and the ranking with its values is printed right above.
        ranked = [re.escape(str(n)) for n, _ in (stat or {}).get("ranking") or []] \
            if stat and stat.get("kind") == "region" else []
        regions = re.compile(r"\b(?:" + "|".join(ranked) + r")\b", re.IGNORECASE) if ranked else None
        if mode == "comparison":
            if not _numbers_given(sentence, allowed):
                return "a number the model was not given"
        elif _has_figure(sentence, years):
            return "a figure"
        if _STATISTICS.search(sentence):
            return "statistical vocabulary"
        # In "What changed" a scale word after a checked number is part of that number.
        if _PROPORTION[lang].search(_NUMBER.sub(" ", sentence) if mode == "comparison" else sentence):
            return "a multiplier, fraction, majority or record"
        if plan_lines and _TOTALS[lang].search(sentence):
            return "a total, in a report of plan lines"
        if _CAUSE[lang].search(sentence):
            return "a cause or a link between findings"
        if _unknown_names(sentence, names):
            return "a name the findings do not give"
        if mode == "comparison":
            return None
        if regions and regions.search(sentence):
            return "a region, under a ranking the code already gives"
        if _NOW[lang].search(sentence):
            return "the present, for a dated value"
        rise, fall, other = _change(sentence, lang)
        if other:
            return "a change the check cannot read"
        if not (rise or fall):
            return None
        supported = _direction(stat) if stat else None
        if supported is None:
            return "a change where the finding gives none"
        if rise and fall or (1 if rise else -1) != supported:
            return "a direction against the finding"
        return None

    kept: dict[str, list[str]] = {}
    removed = 0
    for heading, sentences in _sections(text):
        if _key(heading) not in known:
            continue                # a section the report does not have: not used at all
        name, mode, stat = known[_key(heading)]
        for i, sentence in enumerate(sentences):
            if i == 0:
                sentence = _LABEL.sub("", sentence)     # the label is added in code
            rule = broken(sentence, mode, stat) if sentence.strip() else "empty"
            if rule is None:
                kept.setdefault(name, []).append(sentence.strip())
            elif rule != "empty":
                removed += 1
                logger.info("Commentary check dropped a sentence [%s] (%s) under '%s': %s",
                            label or "report", rule, name, sentence)
    comparison = None
    if comparison_heading and comparison_heading in kept:
        comparison = " ".join(kept.pop(comparison_heading))
    return Commentary({h: " ".join(s) for h, s in kept.items()}, comparison, removed)
