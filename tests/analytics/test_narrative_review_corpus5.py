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


# Item 2: Turkish stems only on Turkish reports ("in-" + "-di" is not "indicator").
@pytest.mark.parametrize("case,key,sentence,expect", [
    ("afg_pro_en", "Protection", "This indicator has three observations, too few for a trend test.", "keep"),
    ("afg_pro_en", "Protection", "For this indicator HDX HAPI gives 14,988,378 people for 2026, the plan's only protection figure that year.", "keep"),
    ("afg_pro_en", "Executive Summary", "In 2026, 14,988,378 individuals were in need of protection, the plan's only protection figure for that year.", "keep"),
    ("ssd_pro_en", "Protection", "The latest value, 4,867,750 people in 2026, indicates the scale of protection needs that year.", "keep"),
    ("ssd_pro_en", "Data Coverage & Limitations", "The 2025 figure (2,633,491 people) is one of the plan's separate lines, so it is only indicative of protection needs.", "keep"),
    ("hti_pro_en", "Protection", "Only two observations exist for this indicator, so no trend could be tested.", "keep"),
    ("afg_pro_tr", "Yönetici Özeti", "Koruma ihtiyacı 2026'da 14.988.378 kişiye yükseldi.", "remove"),
    ("afg_pro_en", "Executive Summary", "Protection needs rose to 14,988,378 people in 2026.", "remove"),
])
def test_change_words_are_read_in_the_reports_language(case, key, sentence, expect):
    assert ("remove" if _removed(case, key, sentence) else "keep") == expect


# Item 3: "cannot" and the contractions negate.
@pytest.mark.parametrize("case,key,sentence,expect", [
    ("afg_fn_en", "Food insecurity", "With p=0.059, the result is close to, but not below, the α=0.05 threshold, so the trend cannot be called statistically significant.", "keep"),
    ("sdn_fn_en", "Food insecurity", "With p=0.312, the increase cannot be considered statistically significant.", "keep"),
    ("afg_all1_en", "Food insecurity", "The Holm adjustment raises the p-value from 0.059 to 0.237, well above α=0.05, so the decline cannot be considered statistically significant.", "keep"),
    ("afg_fn_en", "Food insecurity", "The decline can't be called statistically significant.", "keep"),
    ("afg_fn_en", "Food insecurity", "The decline isn’t statistically significant.", "keep"),
    ("afg_fn_en", "Food insecurity", "The decline couldn't be shown to be statistically significant.", "keep"),
    ("hti_pro_en", "IDPs|Trend", "The increase cannot be called statistically significant.", "remove"),
])
def test_cannot_negates_a_significance_claim(case, key, sentence, expect):
    assert ("remove" if _removed(case, key, sentence) else "keep") == expect


# Item 4: the noun "significance" with its verbs is a claim, either way; a significance level
# or threshold is not.
@pytest.mark.parametrize("case,key,sentence,expect", [
    ("hti_pro_en", "IDPs|Trend", "Although IDPs rose steeply, the trend did not reach statistical significance.", "remove"),
    ("hti_pro_en", "IDPs|Trend", "The rise in IDPs falls short of statistical significance after the Holm adjustment.", "remove"),
    ("hti_pro_en", "Refugees", "The increase in refugees did not reach significance after the Holm correction.", "remove"),
    ("afg_fn_en", "Food insecurity", "The decline in food insecurity reached statistical significance.", "remove"),
    ("afg_all1_en", "Humanitarian funding", "The fall in funding achieved statistical significance at α=0.05.", "remove"),
    ("afg_fn_en", "Food insecurity", "The decline showed no statistical significance (p=0.059).", "keep"),
    ("hti_pro_en", "IDPs|Trend", "The increase reached statistical significance (Holm-adjusted p=0.017).", "keep"),
    ("hti_pro_en", "Refugees", "The increase in refugees attained statistical significance after the Holm correction.", "keep"),
    ("afg_fn_en", "Executive Summary", "The decline in food insecurity, 21.0 percentage points along the trend line, falls just short of statistical significance (p=0.059).", "keep"),
    ("afg_pro_en", "Returnees", "A Kendall tau of 1.00 shows a perfectly consistent increase, yet the trend falls short of significance after the Holm adjustment (Holm-adjusted p=0.179).", "keep"),
    ("afg_all1_en", "Humanitarian funding", "The Kendall tau of -1.00 reflects a strictly monotonic decline, though with four observations the trend does not reach statistical significance (Holm-adjusted p=0.268).", "keep"),
    ("afg_fn_en", "Food insecurity", "The test uses the 0.05 significance level.", "keep"),
    ("hti_pro_en", "IDPs|Trend", "The Holm-adjusted p-value of 0.017 is below the significance threshold of 0.05.", "keep"),
    ("afg_fn_tr", "Gıda güvensizliği", "Düşüş istatistiksel anlamlılığa ulaşmadı.", "keep"),
    ("afg_fn_tr", "Gıda güvensizliği", "Düşüş anlamlılık düzeyine ulaştı.", "remove"),
    ("afg_fn_tr", "Gıda güvensizliği", "Anlamlılık düzeyi α=0,05 olarak alınmıştır.", "keep"),
])
def test_the_noun_significance_is_a_claim(case, key, sentence, expect):
    assert ("remove" if _removed(case, key, sentence) else "keep") == expect


# Item 5: a change word governed by a negation in its own clause is the not-comparable caveat.
@pytest.mark.parametrize("case,key,sentence,expect", [
    ("afg_pro_en", "Protection", "For this reason no trend is tested, and the figures should not be read as a rise or fall.", "keep"),
    ("afg_pro_en", "Protection", "The three figures should not be read as an increase or a decrease, since each year may count a different line.", "keep"),
    ("ssd_pro_en", "Protection", "Because the three values rest on different plan lines, they do not show an increase or a decrease in protection needs.", "keep"),
    ("afg_pro_en", "Executive Summary", "Protection: people in need was 14,988,378 people in 2026; the 2024 and 2025 figures (14,809,904 and 14,213,777) may be single plan lines, so the three years should not be read as an increase or decrease.", "keep"),
    ("ssd_pro_en", "Executive Summary", "Protection needs were 4,867,750 people in 2026; the 2025 figure of 2,633,491 is a single plan line, so the difference does not reflect a fall and rise in needs.", "keep"),
    ("ssd_pro_tr", "Koruma", "Bu nedenle rakamlar arasındaki fark bir artış ya da düşüş olarak yorumlanmamalıdır.", "keep"),
    ("afg_pro_tr", "Koruma", "Rakamlar yıldan yıla farklı kalemlere dayandığından bir artış ya da azalış olarak okunmamalıdır.", "keep"),
    ("afg_pro_tr", "Koruma", "2026 rakamı 14.988.378 kişi, 2025 rakamı 14.213.777 kişi, 2024 rakamı ise 14.809.904 kişidir; ancak bunlar farklı temellere dayandığından yıllar arasında bir artış ya da azalış olarak yorumlanmamalıdır.", "keep"),
    ("afg_pro_en", "Protection", "The 2026 figure cannot be interpreted as a rise from 2025.", "keep"),
    ("afg_pro_en", "Protection", "No rise or fall can be stated between these years.", "keep"),
    ("afg_pro_en", "Executive Summary", "Protection needs rose to 14,988,378 people in 2026, but the figures should not be read as an increase.", "remove"),
    ("afg_pro_en", "Executive Summary", "Protection needs rose to 14,988,378 people in 2026; earlier figures do not show a decrease.", "remove"),
    ("afg_pro_tr", "Yönetici Özeti", "Koruma ihtiyacı 2026'da 14.988.378 kişiye yükseldi; bu bir azalış olarak okunmamalıdır.", "remove"),
])
def test_a_negated_change_is_the_caveat_not_a_claim(case, key, sentence, expect):
    assert ("remove" if _removed(case, key, sentence) else "keep") == expect
