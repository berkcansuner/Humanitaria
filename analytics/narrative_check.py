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
   factor; a fractional change ('fell by a third', 'üçte bir oranında azaldı') likewise.
   A level ('to 32%', '%32'ye', '%32 düzeyinde', 'a third of the population') is checked
   as a number only.

Headings are kept. A finding section left empty gets a placeholder sentence, and a
note at the end says how many sentences were removed. The check only deletes: it
never rewords or adds a claim.
"""
import logging
import math
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
# When the check itself fails, the report keeps the narrative as generated and says so.
UNCHECKED_NOTE = {
    "en": "_Note: the automatic check of this narrative against the computed statistics could "
          "not run; the text is shown as generated._",
    "tr": "_Not: Bu anlatımın hesaplanan istatistiklerle otomatik denetimi çalıştırılamadı; metin "
          "üretildiği gibi gösteriliyor._",
}
_PLACEHOLDER = {
    "en": "The narrative for this finding could not be verified against the computed "
          "statistics and was removed.",
    "tr": "Bu bulgunun anlatımı hesaplanan istatistiklerle doğrulanamadığı için çıkarıldı.",
}

_NUMBER = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)*)"
    r"(?:\s*(milyon|million|milyar|billion|bin|thousand)(?:['’]?[a-zçğıöşüâîû]*)?\b)?",
    re.IGNORECASE)
_SCALE = {"milyon": 1e6, "million": 1e6, "milyar": 1e9, "billion": 1e9,
          "bin": 1e3, "thousand": 1e3}
_SMALL_COUNT = 10

_CLAIM = re.compile(r"\bsignificant(?:ly)?\b|\banlaml[ıi](?!l[ıi]k)\w*", re.IGNORECASE)
_NEGATIVE_CLAIM = re.compile(r"\b(?:in|non-?)significant\b|\banlams[ıi]z", re.IGNORECASE)
_EN_NEGATION = re.compile(
    r"\b(?:not|no|non|never|neither|nor|without|lacks?|lacked|fails?|failed)\b|n't\b", re.IGNORECASE)
_TR_NEGATION = re.compile(
    r"de[ğg]il|olmay|\byok\b|m[ae]m[ae]kte|m[ae]m[ıiuü][şs]|m[ae]d[ıiuü]|m[ae]z\b", re.IGNORECASE)
_WINDOW = 4   # words after a claim (Turkish) that can negate it
_WINDOW_BEFORE = 6   # words before it, within its own clause ("was not found to be statistically significant")
# A negation belongs to the claim's own clause: "Although not large, the decline is
# significant" and "not just visible but significant" claim significance. A comma between
# digits ("14,988,378", "15,0") is part of a number, and "not yet" is one negation.
_STRONG_BREAK = re.compile(
    r"[;:]|\b(?:but|although|though|while|whereas|ancak|fakat|ama|rağmen|karşın)\b|(?<!\bnot )\byet\b",
    re.IGNORECASE)
_CLAUSE_BREAK = re.compile(rf"(?<!\d),|,(?!\d)|{_STRONG_BREAK.pattern}", re.IGNORECASE)
# A short comma aside right after a negation keeps it in scope: "was not, however,
# significant", "was not found, at α=0.05, to be significant".
_NEGATION_ASIDE = re.compile(r"\b(not|never)((?:\s+\w+)?)\s*,(?:\s*[^\s,;:]+){1,6}\s*,", re.IGNORECASE)
# A clause whose subject is negated: "None of the trends was significant", "Neither (of
# the) …", "Not one …", "No trend was …"; Turkish "hiçbiri", "hiçbir …".
_SUBJECT_NEGATION = re.compile(r"^\s*(?:none|neither|not\s+one|no\s+\w+)\b|\bhiçbir", re.IGNORECASE)
# The sentence's subject is negated and the claim is its predicate: "None of the four trends
# (food insecurity, refugees, …) was significant", "Neither the decrease in refugees, nor
# the increase in returnees, was significant", "No trend in this report, whether for …, is
# significant". Parentheses and dash asides are dropped first; the subject reaches the claim
# when no strong break comes between them and no comma-separated part before the claim's
# own has a verb of its own ("No trend was significant, and the regional difference is").
_ASIDE = re.compile(r"\([^()]*\)|\s[—–]\s[^—–]*?\s[—–]\s")
_FINITE = re.compile(r"\b(?:is|are|was|were|remains?|remained|has|have|had|shows?|showed|does|did)\b",
                     re.IGNORECASE)
_PREDICATE_START = re.compile(
    r"\s*(?:is|are|was|were|be|been|remains?|remained|has|have|had|shows?|showed|does|did|could|"
    r"can|would|should|may|might|will|proved|appears?|appeared|seems?|seemed|reached|achieved)\b",
    re.IGNORECASE)
# A negated subject of a verb that itself negates is a double negation: "No partner disputes
# that the increase is significant", "Neither … prevents the increase from being significant".
_DOUBLE_NEGATION = re.compile(
    r"\b(?:disput\w*|doubt\w*|den(?:y|ies|ied)|question\w*)\s+that\b|\b(?:prevent|stop)\w*\b.*\bfrom\b",
    re.IGNORECASE)


def _subject_negates(prefix: str) -> bool:
    """The negated subject at the start of *prefix* (the sentence up to the claim) governs
    the claim."""
    prefix = _ASIDE.sub(" ", prefix)
    if not re.match(r"\s*(?:none|neither|not\s+one|no\s+\w+)\b", prefix, re.IGNORECASE):
        return False
    if _STRONG_BREAK.search(prefix) or _DOUBLE_NEGATION.search(prefix):
        return False
    # A lone dash left after the asides separates clauses like a comma. With commas, the
    # claim's own part must open with the subject's verb ("…, nor the increase in returnees,
    # was significant"), not with a new subject ("No region stands out, and the difference …").
    parts = re.split(r"(?<!\d),|,(?!\d)|\s[—–]\s", prefix)
    return not any(_FINITE.search(part) for part in parts[:-1]) and (
        len(parts) == 1 or bool(_PREDICATE_START.match(parts[-1])))

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


_ROUNDED_FROM = 10_000      # a figure this large may be quoted to 2-4 significant digits


def _rounded(value: float) -> list[float]:
    """*value* rounded to 2, 3 and 4 significant digits (349,999 -> 350,000; 1,611,291 ->
    1,611,000), as a report quotes the full figures of the data notes."""
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


def _numbers_ok(sentence: str, allowed: list[float]) -> bool:
    for m in _NUMBER.finditer(sentence):
        scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
        readings = _readings(m.group(1))
        if any(d == 0 and scale == 1.0 and v <= _SMALL_COUNT for v, d in readings):
            continue
        if not _matches_value(_number_readings(m), allowed):
            return False
    return True


def _claim(sentence: str) -> str | None:
    """'significant' / 'not significant' / None (no claim, or claims that disagree)."""
    polarities = set()
    if _NEGATIVE_CLAIM.search(sentence):
        polarities.add("not significant")
    sentence = _NEGATION_ASIDE.sub(r"\1\2", sentence)
    for m in _CLAIM.finditer(sentence):
        prefix = sentence[:m.start()]
        clause = _CLAUSE_BREAK.split(prefix)[-1]
        before = " ".join(clause.split()[-_WINDOW_BEFORE:])
        after = " ".join(sentence[m.start():].split()[:_WINDOW + 1])
        subject = (_SUBJECT_NEGATION.search(clause) and not _DOUBLE_NEGATION.search(clause)) \
            or _subject_negates(prefix)
        negated = _EN_NEGATION.search(before) or subject or _TR_NEGATION.search(after)
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
# Whole words only: "cutoff", "uptake", "upon", "moreover" are not change words.
_EN_CHANGE_AFTER = re.compile(
    r"^(?:declines?|declined|drops?|dropped|falls?|fell|increases?|increased|rises?|rose|"
    r"reductions?|decreases?|decreased|gains?|growth|jumps?|jumped|cuts?|lower|higher|fewer|more|"
    r"less|down|up|surges?|surged|changes?|changed|improvements?|deteriorations?|worsening|"
    r"loss(?:es)?)$", re.IGNORECASE)
_EN_CHANGE_OF = re.compile(
    r"\b(?:decline|drop|fall|increase|rise|reduction|decrease|growth|change|jump|cut)s?\s+of\s*$",
    re.IGNORECASE)
# Turkish: a level takes a case or 'düzey' word after the number ("%32'ye", "%32'den",
# "%32 düzeyinde"); a change is followed by a change word ("%32 azaldı", "yüzde 32'lik
# bir düşüş", "%32 oranında arttı").
_TR_LEVEL_SUFFIX = re.compile(r"^['’](?:y?[ae]|[dt][ae]n?|s[ıi]|[ıiuü])\b", re.IGNORECASE)
# Whole Turkish change words, by their verb forms: "artık" (any more), "düşük" (low),
# "büyük" (big), "gerilim" (tension), "azami" (maximum), "insani" (humanitarian) are not.
# A verb's forms, after its stem: past (arttı, düştüğü), evidential and perfect (artmış,
# düşmüştür, azalmıştı), progressive (artıyor, büyüyor), aorist (artar, azalır), future
# (artacak, büyüyecek), converbs (artarak, düşüp), verbal nouns that name the change
# (artış, düşüş, azalma, gerileme, düşmektedir) and participles (artan, düşen). The
# adjectives and nouns that share a stem are not among them: artık, artı, düşük, büyük,
# gerilim, azami, insani, inanç.
_TR_SUFFIXES = (r"[dt][ıiuü]\w*|m[ıiuü]ş\w*|[ıiuü]?yor\w*|(?:[ae]|[ıiuü])?r(?:l[ae]r|ken|d[ıi]r)?|"
                r"y?[ae]c[ae][kğ]\w*|y?[ae]r[ae]k|y?[ıiuü]p|m[ae]\w*|y?[ıiuü]ş\w*")
_TR_PARTICIPLE = r"|y?[ae]n(?:l[ae]r\w*)?"


def _tr_verbs(*stems: str, participle: bool = True) -> str:
    suffixes = _TR_SUFFIXES + (_TR_PARTICIPLE if participle else "")
    return "|".join(f"{stem}(?:{suffixes})" for stem in stems)


# "in-" (to come down) takes no participle: "inan…" is to believe.
_TR_RISE_VERBS = _tr_verbs("art", "yüksel", "büyü", "çık", "katlan")
_TR_FALL_VERBS = (_tr_verbs("azal", "düş", "gerile", "eksil", "küçül", "kaybet", "kaybed")
                  + "|" + _tr_verbs("in", participle=False) + r"|geriliyor\w*")
_TR_CHANGE = re.compile(rf"^(?:{_TR_RISE_VERBS}|{_TR_FALL_VERBS})$", re.IGNORECASE)
_TR_FILLER = {"bir", "oranında", "civarında", "kadar", "dolayında", "lik", "lık", "luk", "lük"}

# Multiplicative words, with the factor they claim. Supported for a count when the
# observed latest/first ratio is within ±10% of the factor (halved: 0.45–0.55,
# doubled: 1.8–2.2, tripled: 2.7–3.3, quadrupled: 3.6–4.4); never for a share.
_MULTIPLIERS = [
    # "by half of the partners" is a level; "to (about) half" needs a fall verb before it.
    (0.5, re.compile(r"\bhalv(?:ed|es|ing|e)\b|\bin half\b|\bby half\b(?!\s+(?:of|the)\b)|"
                     r"\bhalf as\b|\b(?:fell|fallen|dropped|declined|decreased|shrank|shrunk|cut|"
                     r"reduced|down)\s+(?:by|to)\s+(?:(?:about|around|nearly|almost|roughly|some|"
                     r"just over|just under|more than|less than)\s+)?(?:a\s+)?half\b|"
                     r"\bhalf\s+(?:of\s+)?what\s+it\s+was\b|\b(?:now|only|just)\s+half\b",
                     re.IGNORECASE)),
    (2.0, re.compile(r"\bdoubl(?:ed|es|ing)\b|\btwo-?fold\b|\btwice as\b|"
                     r"\bikiye\s+katla\w*|\biki\s+kat\w*", re.IGNORECASE)),
    (3.0, re.compile(r"\btripl(?:ed|es|ing)\b|\bthree-?fold\b|\bthree times\b|\büç\s+kat\w*",
                     re.IGNORECASE)),
    (4.0, re.compile(r"\bquadrupl\w*\b|\bfour-?fold\b|\bfour times\b|\bdört\s+kat\w*",
                     re.IGNORECASE)),
]
_FACTOR_TOLERANCE = 0.10

# Fractions. Only a fraction used as a change counts ("fell by a third", "a quarter
# fewer", "üçte bir oranında azaldı"), not a level ("a third of the population",
# "nüfusun üçte biri"). Supported for a count when the observed latest/first ratio
# within ±10% of the fraction matches either reading: changed BY it (ratio 1 ± f) or
# changed TO it (ratio f); never for a share.
_FRACTIONS = [
    (1 / 3, r"(?:a|one)[- ]third", r"üçte\s+bir\w*"),
    (2 / 3, r"two[- ]thirds", r"üçte\s+iki\w*"),
    (1 / 4, r"(?:a|one)[- ](?:quarter|fourth)", r"dörtte\s+bir\w*"),
    (3 / 4, r"three[- ]quarters", r"dörtte\s+üç\w*"),
    (1 / 5, r"(?:a|one)[- ]fifth", r"beşte\s+bir\w*"),
]
_EN_FRACTION_CHANGE = [
    (f, re.compile(rf"\bby\s+(?:(?:about|around|nearly|almost|roughly|some|more than|over|"
                   rf"under|less than|just)\s+)*{en}\b|\b{en}\s+(?:fewer|lower|less|more|higher|"
                   rf"smaller|larger|greater)\b|\b(?:fell|dropped|declined|decreased|shrank|"
                   rf"rose|grew|increased|climbed)\s+(?:to\s+)?(?:about\s+|nearly\s+|almost\s+)?"
                   rf"{en}\b", re.IGNORECASE))
    for f, en, _ in _FRACTIONS]
# Turkish fractions and halves count only when a change word follows: "üçte bir
# oranında azaldı", "yarısına indi"; not "nüfusun üçte biri", "yarısına yakını".
_TR_FRACTION_CHANGE = [
    (f, re.compile(rf"\b{tr}(?:\s+(?:oranında|kadar|civarında|dolayında))?\s+(\w+)",
                   re.IGNORECASE))
    for f, _, tr in _FRACTIONS + [(0.5, "", r"(?:yar[ıi]\s+yar[ıi]ya|yar[ıi]ya|yar[ıi]s[ıi]na)")]]


def _is_en_change(sentence: str, start: int, end: int) -> bool:
    before = [w.strip("(),;:").lower() for w in sentence[:start].split()]
    while before and before[-1] in _QUALIFIER:
        before.pop()
    if before and _EN_CHANGE_BEFORE.match(before[-1]):
        return True
    if _EN_CHANGE_OF.search(" ".join(before)):
        return True
    after = [w.strip("(),;:.") for w in sentence[end:].split()]
    if len(after) > 1 and after[0].lower() in ("up", "down") and (
            after[1].lower() == "from" or _readings(after[1].lstrip("+-"))):
        return False        # "32.0% (down from 47.0%)", "32.0%, down 21.0 points": not this one
    return bool(after) and bool(_EN_CHANGE_AFTER.match(after[0]))


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


def _matches(value: float, computed: list[float], direction: int | None = None) -> bool:
    """*value* as written equals a computed figure rounded to its decimals (or to a
    whole number), and, when the sentence says which way it moved (+1 rise, -1 fall),
    a figure moving that way."""
    def close(c):
        return (abs(value - abs(c)) <= 0.5 + 1e-9 if value == int(value)
                else abs(value - abs(c)) <= 0.05 + 1e-9)
    return any(close(c) and (direction is None or c == 0 or (c > 0) == (direction > 0))
               for c in computed)


_EN_RISE = re.compile(r"\b(?:rose|risen|rises|rising|increased?|increases|increasing|grew|grown|"
                      r"grows|growing|climbed|surged|jumped|gained|up|higher)\b", re.IGNORECASE)
_EN_FALL = re.compile(r"\b(?:fell|fallen|falls|falling|dropped|drops|dropping|declined?|declines|"
                      r"declining|decreased?|decreases|decreasing|shrank|shrunk|reduced|reduction|"
                      r"down|lower|fewer|eased|plunged|slid|lost|cut)\b", re.IGNORECASE)
_TR_RISE = re.compile(rf"^(?:{_TR_RISE_VERBS})$", re.IGNORECASE)
_TR_FALL = re.compile(rf"^(?:{_TR_FALL_VERBS})$", re.IGNORECASE)
_PP_NUMBER = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)*)\s*(?:percentage[- ]points?|yüzde\s+puan|puan)",
                        re.IGNORECASE)


_SAYS_NOT_COMPARABLE = re.compile(
    r"not comparable|cannot be compared|can't be compared|not be compared|different basis|"
    r"karşılaştırılam|kıyaslanam|karşılaştırılabilir değil|karşılaştırılması mümkün değil|"
    r"farklı bir temel", re.IGNORECASE)
# Words that say a figure moved between years: verbs and nouns of change, multipliers,
# "went from … to", "stable". Not "higher"/"lower"/"up to" on their own: comparing a year's
# figure with a sub-line or with the unpublished overall figure is not a change.
_EN_CROSS_YEAR = re.compile(
    r"\b(?:rose(?!-)|risen|rises?|rising|increase[ds]?|increasing|grew|grown|grows?|growing|"
    r"climb(?:ed|s|ing)?|surge[ds]?|jump(?:ed|s)?|gained|fell|fallen|falls?|falling|"
    r"drop(?:ped|s|ping)?|decline[ds]?|declining|decrease[ds]?|decreasing|shr[ai]nk|shrunk|"
    r"eas(?:ed|ing)|plunged|slid|halv\w*|doubl\w*|twice|tripl\w*|quadrupl\w*|two-?fold|"
    r"three-?fold|stable|steady|unchanged|reach(?:ed|es|ing)?|went\s+from|gone\s+from)\b",
    re.IGNORECASE)
# "greater/more/fewer/less/higher/lower … than <year or value>" compares two years.
_EN_COMPARATIVE = re.compile(
    r"\b(?:greater|more|fewer|less|higher|lower|larger|smaller|bigger)\b.*?\bthan\s+"
    r"(?:in\s+|those\s+of\s+|that\s+of\s+|the\s+figure\s+(?:for|of)\s+|the\s+)?"
    r"(?P<what>[\d.,]+(?:\s*(?:million|thousand|billion))?)", re.IGNORECASE)
_TR_COMPARATIVE = re.compile(
    r"(?:19|20)\d{2}['’]\w*\s+(?:göre|kıyasla|oranla)\b.*?\bdaha\s+(?:fazla|az|yüksek|düşük|çok)",
    re.IGNORECASE)
_TR_MULTIPLE = re.compile(r"\b(?:iki|üç|dört)\s+kat\w*|\byarı\s+yarıya\b|\byarısına\b",
                          re.IGNORECASE)
_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


def _tr_change_word(sentence: str) -> bool:
    words = [w.strip("(),;:.'’").lower() for w in re.split(r"[\s'’]+", sentence)]
    return any(_TR_CHANGE.match(w) and not (i and words[i - 1] == "ortaya")   # "ortaya çıkan"
               for i, w in enumerate(words))


# Phrases that set a figure against another year even without a change verb next to it.
_CHANGE_PHRASE = re.compile(
    r"\b(?:up|down)\s+from\b|\b(?:highest|lowest)\b.*\bsince\b|\bbu\s+yana\b|"
    # "exceeded the 2025 figure", "below the 2024 level"; not "above the 2025 Gender Based
    # Violence line", a sub-line of the plan.
    r"\b(?:exceed\w*|surpass\w*|above|below|(?:higher|lower|more|less)\s+than)\s+(?:the\s+|its\s+)?"
    r"(?:19|20)\d{2}\s+(?:figure|level|value|total|number)\b|"
    r"\ben\s+(?:yüksek|düşük)\b.*\b(?:beri|bu\s+yana)\b", re.IGNORECASE)
# "from 14.8 to 15.0 million": the scale word after the last number applies to the first.
_RANGE = re.compile(
    r"(\d+(?:[.,]\d+)?)(\s+(?:to|and|-|–|ile|ila)\s+\d+(?:[.,]\d+)?\s*"
    r"(million|milyon|billion|milyar|thousand|bin))", re.IGNORECASE)


# --- A series value with the wrong period ("fell to 14.8 million in 2026" when 14.8
# million is 2025's figure). Conservative: one year (and at most one month) named, no
# range or "since". ---
_MONTH_NUMBER = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"])}
_MONTH_NUMBER.update({name: i + 1 for i, name in enumerate(
    ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül",
     "ekim", "kasım", "aralık"])})
# A month only as a date, followed by its year ("may be" is not May): "March 2022", "Ocak 2026".
_MONTH = re.compile(r"\b(" + "|".join(_MONTH_NUMBER) + r")\s+(?:19|20)\d{2}", re.IGNORECASE)


def _fold_i(name: str) -> str:
    """Python's re matches i, I, ı and İ alike under IGNORECASE, so "Mayis", "MAYIS" and
    "KASIM" match "mayıs"/"kasım": all four fold to "i" for the lookup."""
    return name.replace("İ", "i").replace("I", "i").lower().replace("ı", "i")


_MONTH_BY_FOLD = {_fold_i(name): number for name, number in _MONTH_NUMBER.items()}
_AMBIGUOUS_TIME = re.compile(
    r"\bsince\b|\bbetween\b|\bfrom\b.*\bto\b|\bbu\s+yana\b|\bberi\b|arasında|\bile\b.*\barası",
    re.IGNORECASE)


def _series_points(findings) -> list[tuple[float, str, str, str]]:
    """(value, 'YYYY-MM-DD', resolution, heading) for every value the code wrote about a
    series."""
    points = []
    for s in findings.sections:
        r = s.stat_result
        res = r.get("resolution", "month")
        if r.get("periods") and r.get("values"):
            points += [(float(v), str(p)[:10], res, s.heading) for p, v in zip(r["periods"], r["values"])]
        for v, p in ((r.get("first_value"), r.get("first_period")),
                     (r.get("latest_value"), r.get("latest_period"))):
            if v is not None and p:
                points.append((float(v), str(p)[:10], res, s.heading))
    return points


def _wrong_period(sentence: str, points: list) -> bool:
    """The sentence names one year (and at most one month) and quotes a value of a series
    for it, but none of the values it quotes of that series belongs to that period. A
    second value of the series beside the period's own is a comparison ("17.4 million in
    2026, up from 14.8 million"), not a wrong period."""
    years = set(_YEAR.findall(sentence))
    found = [_MONTH_BY_FOLD.get(_fold_i(m)) for m in _MONTH.findall(sentence)]
    if None in found:
        return False                # a spelling the table does not know: the rule is skipped
    months = set(found)
    if len(years) != 1 or len(months) > 1 or _AMBIGUOUS_TIME.search(sentence):
        return False
    year, month = years.pop(), (months.pop() if months else None)

    def fits(p, res):
        if p[:4] != year:
            return False
        return month is None or res == "year" or int(p[5:7]) == month
    fitting: set[str] = set()          # series with a quoted value of the stated period
    misplaced: list[set[str]] = []     # per quoted value of another period: its series
    for m in _NUMBER.finditer(sentence):
        token = m.group(1)
        if not m.group(2) and _YEAR.fullmatch(token):
            continue                                    # a year, not a value
        readings = _number_readings(m)
        matched = [(p, res, h) for v, p, res, h in points if _matches_value(readings, [v])]
        if any(fits(p, res) for p, res, _ in matched):
            fitting |= {h for p, res, h in matched if fits(p, res)}
        elif matched:
            misplaced.append({h for _, _, h in matched})
    return any(not (series & fitting) for series in misplaced)


# A comma-detached phrase that completes the clause before it: "increased in 2026, to
# 14,988,378", "stood at 15.0 million, up from 2025", "…, the highest since 2024".
_ATTACHED = re.compile(r"^\s*(?:up|down|to|from|by|the\s+(?:highest|lowest))\b", re.IGNORECASE)
_AND = re.compile(r"\b(?:and|ve)\b", re.IGNORECASE)
# Turkish "while" is a converb on the verb: "korurken", "artarken", "azalmazken".
_TR_WHILE = re.compile(r"(?<=[rz]ken)\s", re.IGNORECASE)


def _has_figure(text: str) -> bool:
    """A number other than a year."""
    return any(m.group(2) or not _YEAR.fullmatch(m.group(1)) for m in _NUMBER.finditer(text))


def _change_clauses(sentence: str) -> list[str]:
    """The sentence's clauses for the one-value change rule. Breaks: ';', ':', a comma
    (not one between digits), 'but', 'while', 'although' and the like, and a Turkish verb in
    '-rken'/'-zken' ("korurken", while keeping); a comma piece that
    starts with 'up', 'down', 'to', 'from', 'by' or 'the highest/lowest' stays with the
    clause before it. 'and' ('ve') separates two clauses only when the text on each side
    of it quotes a figure other than a year ("IDPs fell to 3.06 million and protection
    needs stood at 15.0 million"), not in "rose in 2026 and stood at 15.0 million"."""
    clauses: list[str] = []
    for piece in (p for chunk in _CLAUSE_BREAK.split(sentence) for p in _TR_WHILE.split(chunk)):
        if clauses and _ATTACHED.match(piece):
            clauses[-1] += "," + piece
        else:
            clauses.append(piece)
    out = []
    for clause in clauses:
        parts = _AND.split(clause)
        start = 0
        for i in range(1, len(parts)):
            left, right = " and ".join(parts[start:i]), " and ".join(parts[i:])
            if _has_figure(left) and _has_figure(right):
                out.append(left)
                start = i
        out.append(" and ".join(parts[start:]))
    return [c for c in out if c.strip()]


def _says_change(sentence: str) -> bool:
    """A word of change between years, in English or Turkish."""
    return bool(_EN_CROSS_YEAR.search(sentence) or _TR_MULTIPLE.search(sentence)
                or _tr_change_word(sentence))


def _series_values_in(sentence: str, values: list[float]) -> int:
    """How many different numbers of the sentence are values of the series (rounded quotes
    count). Counted per number: one "15.0 million" matching both 14,988,378 and, rounded to
    two digits, 14,809,904 is still one value."""
    hit = set()
    sentence = _RANGE.sub(r"\1 \3\2", sentence)
    for m in _NUMBER.finditer(sentence):
        if _matches_value(_number_readings(m), values):
            hit.add(m.group(0).strip())
    return len(hit)


def _compares_years(sentence: str, years: set, values: list[float]) -> bool:
    """A comparison between two years of the series: '… than (in) 2025', '… than 14.2
    million', "2025'e göre … daha fazla"."""
    if _TR_COMPARATIVE.search(sentence):
        return True
    for m in _EN_COMPARATIVE.finditer(sentence):
        what = m.group("what").rstrip(".,")
        if what in years:
            return True
        token = _NUMBER.match(what)
        if token and _series_values_in(what, values):
            return True
    return False


def _direction(sentence: str) -> int | None:
    """+1 when the sentence only says something rose, -1 when it only says something
    fell, None when it says neither or both."""
    words = [w.strip("(),;:.'’") for w in re.split(r"[\s'’]+", sentence)]
    rise = bool(_EN_RISE.search(sentence)) or any(_TR_RISE.match(w) for w in words)
    fall = bool(_EN_FALL.search(sentence)) or any(_TR_FALL.match(w) for w in words)
    return (1 if rise else -1) if rise != fall else None


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
        "pp": [r["line_change"] for r in shares if r.get("line_change") is not None]
              + [r["slope"] for r in shares if r.get("slope") is not None],
        "ratios": [x for x in (_ratio(r) for r in counts) if x],
    }


def _relative_claim_ok(sentence: str, profile: dict) -> bool:
    direction = _direction(sentence)
    for value in _percent_changes(sentence):
        if profile["share"] or not _matches(value, profile["relative"], direction):
            # A share's change is in percentage points, and only as computed.
            if not (_PP.search(sentence) and _matches(value, profile["pp"], direction)):
                return False
    if direction is not None:
        # A change in percentage points said the wrong way round ("rose by 21.0
        # percentage points" for a computed -21.0): removed, when it matches only that.
        for m in _PP_NUMBER.finditer(sentence):
            values = [v for v, _ in _readings(m.group(1))]
            if (any(_matches(v, profile["pp"]) for v in values)
                    and not any(_matches(v, profile["pp"], direction) for v in values)):
                return False
    for factor, pattern in _MULTIPLIERS:
        if pattern.search(sentence):
            if profile["share"] or not any(
                    abs(x - factor) <= _FACTOR_TOLERANCE * factor for x in profile["ratios"]):
                return False
    claims = [f for f, pattern in _EN_FRACTION_CHANGE if pattern.search(sentence)]
    claims += [f for f, pattern in _TR_FRACTION_CHANGE
               if any(_TR_CHANGE.match(m.group(1)) for m in pattern.finditer(sentence))]
    for fraction in claims:
        near = _FACTOR_TOLERANCE * fraction
        if profile["share"] or not any(
                abs(abs(1 - x) - fraction) <= near or abs(x - fraction) <= near
                for x in profile["ratios"]):
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


# The tests a Methods section may name, by family; English and Turkish spellings.
_METHODS = {
    "trend": re.compile(r"mann[- ]kendall|\bkendall|\bsen(?:'s|['’]in)?\s+(?:slope|eğim)", re.IGNORECASE),
    "region": re.compile(r"kruskal", re.IGNORECASE),
    "correlation": re.compile(r"pearson", re.IGNORECASE),
    "holm": re.compile(r"\bholm\b|bonferroni", re.IGNORECASE),
}
_METHODS_HEADING = re.compile(r"method|yöntem|metodoloji", re.IGNORECASE)
# A method named only to say it was not applied or not needed ("no Holm correction was
# applied", "Kruskal-Wallis was not applicable", "Holm düzeltmesi uygulanmadı") is not a
# claim that it was used. The negation must govern the method's application in the clause
# that names it: "did not find a significant difference" or "…, and no Holm correction was
# needed" after another method do not exempt that method.
_APPLIED = (r"appl(?:y|ies|ied|icable)|needed|necessary|required|used|run|computed|performed|"
            r"conducted|tested|carried\s+out|done|made|warranted")
_NOT_APPLIED = re.compile(
    rf"\b(?:not|never)\s+(?:\w+\s+)?(?:{_APPLIED})\b|n't\s+(?:\w+\s+)?(?:{_APPLIED})\b|"
    rf"\b(?:no|none|neither)\b.*\b(?:{_APPLIED})\b|\bwithout\b|\bunnecessary\b|"
    r"\b(?:was|were)\s+not\s*\.?\s*$|"      # elliptical: "…; Kruskal-Wallis and Pearson were not."
    r"uygulanma\w*|uygulanam\w*|gerekme\w*|gereksiz\w*|gerek\s+(?:yok|duyulma\w*|kalma\w*)|"
    r"kullanılma\w*|yapılma\w*", re.IGNORECASE)


def _listed_methods(allowed_text: str) -> set | None:
    """The test families the context's METHOD NOTES list (None: the context has none)."""
    if "METHOD NOTES:" not in allowed_text:
        return None
    # Only the note lines themselves: the directive and, for a next-period report, the
    # previous report's whole text follow them, and name every method there is.
    lines = []
    for line in allowed_text.split("METHOD NOTES:", 1)[1].splitlines()[1:]:
        if not line.startswith("- "):
            break
        lines.append(line)
    notes = "\n".join(lines)
    return {family for family, pattern in _METHODS.items() if pattern.search(notes)}


_RELATIVE_ASIDE = re.compile(r",\s*(?:which|that|who)\b[^,;:]*,", re.IGNORECASE)


def _names_unlisted_method(sentence: str, listed: set) -> bool:
    # "A Holm correction, which adjusts for several tests, was not needed": the relative
    # aside is dropped so the method and its "not needed" stay in one clause.
    sentence = _RELATIVE_ASIDE.sub("", sentence)
    return any(pattern.search(clause) and not _NOT_APPLIED.search(clause)
               for clause in _CLAUSE_BREAK.split(sentence)
               for family, pattern in _METHODS.items() if family not in listed)


def verify_narrative(text: str, findings, allowed_text: str, language: str,
                     label: str = "") -> NarrativeCheck:
    """*allowed_text*: the context and directive the model was given (its numbers are
    the only numbers the narrative may use). *label* names the report in the log of
    removed sentences ("Afghanistan / Health / technical_monitoring"); the sentences
    are model-written report text, not user data."""
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
    # Sections whose years are not comparable (different plan lines): a sentence there may
    # give each year's value, but not a rise, fall or change between them.
    points = _series_points(findings)
    not_comparable = {s.heading: ({str(p)[:4] for p in s.stat_result.get("periods") or []},
                                  [float(v) for v in s.stat_result.get("values") or []])
                      for s in findings.sections if s.stat_result.get("not_comparable")}

    def across_years(sentence: str, section: str | None) -> bool:
        """The sentence states a change, or a comparison, between two years of a series
        whose years are not comparable, without saying they are not comparable."""
        if _SAYS_NOT_COMPARABLE.search(sentence):
            return False
        for heading, (years, values) in not_comparable.items():
            # One value of the series, narrated as a change ("rose to 15.0 million in 2026",
            # "artarak 15,0 milyona ulaştı", "…, up from 2025"): the change word, or a phrase
            # that sets the value against a year, must sit in the clause that quotes it.
            if any(_series_values_in(c, values) and (_CHANGE_PHRASE.search(c) or _says_change(c))
                   for c in _change_clauses(sentence)):
                return True
            own = section == heading
            two_years = len(years & set(_YEAR.findall(sentence))) >= 2
            two_values = _series_values_in(sentence, values) >= 2
            if own and _says_change(sentence):
                return True     # in its own section, any change of the figure is across years
            if (two_values or (own and two_years)) and (
                    _says_change(sentence) or _compares_years(sentence, years, values)):
                return True
        return False

    listed_methods = _listed_methods(allowed_text)

    def bad(sentence: str, section: str | None) -> str | None:
        """The rule the sentence breaks, or None."""
        if not _numbers_ok(sentence, allowed):
            return "a number not in the findings"
        if _wrong_period(sentence, points):
            return "a series value given for another period"
        if listed_methods is not None and section and _METHODS_HEADING.search(section.casefold()) and \
                _names_unlisted_method(sentence, listed_methods):
            return "a test the method notes do not list"
        if not _relative_claim_ok(sentence, profiles.get(section or "", whole)):
            return "a relative change the findings do not support"
        if across_years(sentence, section):
            return "a change or comparison between years that are not comparable"
        claim = _claim(sentence)
        if claim is None:
            return None
        if section in verdicts:
            if verdicts[section] is None:
                return "a significance claim about an untested finding"
            if claim != ("significant" if verdicts[section] else "not significant"):
                return "a significance claim against the computed verdict"
            return None
        if claim == "significant" and not any_significant:
            return "a significance claim when no finding is significant"
        return None

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
            rule = bad(item, section)
            if rule:
                removed_here += 1
                logger.info("Narrative check removed a sentence [%s] (%s) under '%s': %s",
                            label or "report", rule, section or "(no heading)", item)
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
