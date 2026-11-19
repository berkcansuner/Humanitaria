"""The round-5 held-out review (rv5) on its ten live contexts: the ten full correct reports
must lose no sentence, and the sentences of the last pass (Turkish month spellings, language-
specific change words, "cannot", the noun "significance", negated not-comparable caveats)
keep or lose their place as stated. "keep": a correct sentence; "remove": a wrong claim."""
import json
from pathlib import Path

import pytest

from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

_DATA = json.loads((Path(__file__).parent / "review_rv5_sets.json").read_text(encoding="utf-8"))
CTX = {k: (Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                              for s in v["sections"]], gaps=[], indicators_covered=[]),
           v["allowed"], v["language"]) for k, v in _DATA.items()}


def _heading(findings, key):
    """A literal heading, or '|'-joined parts that pick the one finding heading with all."""
    parts = key.split("|")
    hits = [s.heading for s in findings.sections if all(p in s.heading for p in parts)]
    return hits[0] if hits else key


def _removed(case, key, sentence):
    findings, allowed, language = CTX[case]
    text = f"## {_heading(findings, key)}\n\n{sentence}\n"
    return verify_narrative(text, findings, allowed, language).removed > 0


@pytest.mark.parametrize("case", sorted(_DATA))
def test_the_full_correct_reports_lose_no_sentence(case):
    findings, allowed, language = CTX[case]
    assert verify_narrative(_DATA[case]["report"], findings, allowed, language).removed == 0


# Item 1: Turkish month names written in ASCII or upper case. Python's re matches i/I with
# ı under IGNORECASE; the lookup must not raise, and the month is still read.
@pytest.mark.parametrize("case,key,sentence,expect", [
    ("afg_pro_en", "IDPs|Latest", "IDPs numbered 3.11 million people in Mayis 2025.", "keep"),
    ("afg_pro_en", "IDPs|Latest", "IDPs numbered 3.11 million people in Kasim 2025.", "remove"),
    ("afg_pro_en", "IDPs|Latest", "IDPs numbered 3.11 million people in Aralik 2025.", "remove"),
    ("afg_pro_tr", "IDP|Son", "Ülke içinde yerinden edilmiş kişi sayısı MAYIS 2025'te 3,11 milyondu.", "keep"),
    ("afg_pro_tr", "IDP|Son", "Ülke içinde yerinden edilmiş kişi sayısı KASIM 2025'te 3,11 milyondu.", "remove"),
])
def test_turkish_month_spellings_never_raise(case, key, sentence, expect):
    assert ("remove" if _removed(case, key, sentence) else "keep") == expect
