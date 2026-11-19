"""The model's interpretation paragraphs are checked by presence rules only: a dropped
sentence costs nothing (the facts are written in code), a kept false one misleads."""
import json
import logging
from pathlib import Path

import pytest

from analytics.narrative_check import check_commentary
from analytics.technical_report import Findings, ReportSection
from tests.analytics import samples

REF = "Refugees (people) — Trend Analysis"                      # decreasing, not significant
FS = "Food security: people in need — Latest Values"            # up from the previous year
IDP = "Internally displaced people (IDPs) — Regional Analysis"  # a ranking: no direction
ALLOWED = "PERIOD ANALYSED: 19 November 2025 to 19 November 2026. Values for 2022, 2024, 2025."


def _findings(**fields):
    return samples.findings(samples.trend(), samples.snapshot(), samples.region(), **fields)


def _kept(heading, sentence, language="en", findings=None, **kwargs):
    res = check_commentary(f"## {heading}\n\n{sentence}", findings or _findings(), ALLOWED,
                           language, **kwargs)
    return bool(res.by_heading)


@pytest.mark.parametrize("heading,sentence", [
    ("Executive Summary", "Read together, the findings describe needs but cannot show where they are heading."),
    ("Executive Summary", "The 2025 refugee figure predates the chosen period, so it should be verified against newer data."),
    (REF, "The decline is visible in the yearly values, yet the test result above does not allow it to be treated as established."),
    (REF, "With four observations the series is short, so the next UNHCR update matters."),
    (FS, "The latest figure is above the previous one, which is worth watching in the next plan."),
    (FS, "Three yearly values describe the scale of need rather than a trend."),
    (IDP, "The ranking shows where displaced people are concentrated at one point in time."),
])
def test_an_interpretation_without_figures_or_claims_is_kept(heading, sentence):
    assert _kept(heading, sentence)


@pytest.mark.parametrize("heading,sentence", [
    # 1. Figures: the code states them.
    (REF, "Refugee numbers stand at 2.67 million people."),
    (REF, "The slope is about 817,000 people per year."),
    (FS, "Needs are at 17.4 million."),
    ("Executive Summary", "Around 95% of the change is recent."),
    ("Executive Summary", "The figure for 2019 was different."),          # a year the findings do not name
    # 2. Statistics: the code states every verdict.
    (REF, "The decline is statistically significant."),
    (REF, "The decline is not statistically significant."),
    (REF, "The trend failed to reach significance."),
    (REF, "The Mann-Kendall result is weak."),
    (IDP, "A Kruskal-Wallis comparison would confirm the gap."),
    (REF, "The confidence interval is wide."),
    (REF, "The p-value is high."),
    # 3. Multipliers, fractions, majorities, records.
    (REF, "Refugee numbers have halved."),
    (FS, "Needs nearly doubled."),
    (REF, "Numbers fell by a third."),
    (IDP, "Most of the displaced live in Herat."),
    (FS, "Needs are at a record high."),
    # 4. Change words: never in the summary, never where the finding has no direction.
    ("Executive Summary", "Protection needs continue to grow."),
    ("Executive Summary", "Refugee numbers are falling."),
    ("Executive Summary", "The situation remains stable."),
    (IDP, "Displacement in Herat is rising."),
    # … and under a finding with a direction, not the opposite one or "no change".
    (REF, "Refugee numbers are climbing."),
    (REF, "Refugee numbers remained stable."),
    (FS, "Food security needs dropped."),
])
def test_what_an_interpretation_must_not_say_is_dropped(heading, sentence):
    assert not _kept(heading, sentence)


def test_only_the_findings_one_direction_is_kept():
    assert _kept(REF, "The fall in refugee numbers should be checked against returns.")
    assert _kept(FS, "Needs rose between the two latest plans.")
    # Both directions in one sentence, or a change the check cannot read: not kept.
    assert not _kept(REF, "Whether numbers rise or fall next depends on the coming year's data.")
    assert not _kept(REF, "The refugee situation has been worsening.")
    # A short series moves from its previous value to its latest, whatever came before.
    f = samples.findings(samples.snapshot(values=[2970000.0, 3110000.0, 3060000.0]))
    assert _kept(f.sections[0].heading, "The latest count is slightly lower.", findings=f)
    assert not _kept(f.sections[0].heading, "The count has crept up.", findings=f)
    # "The test result above" points at the computed paragraph; it is not a comparison.
    assert _kept(IDP, "The ranking above shows where to look first.")
    assert _kept(IDP, "Yukarıdaki sıralama ilk nereye bakılacağını gösterir.", "tr")


@pytest.mark.parametrize("heading,sentence,language", [
    # Certainty claimed or denied: the code states every verdict.
    (REF, "The decline is a robust, well-established pattern.", "en"),
    (REF, "The fall is beyond what chance alone would produce.", "en"),
    (REF, "The movement could easily be noise.", "en"),
    (REF, "Düşüş kanıtlanmış bir örüntüdür.", "tr"),
    (REF, "Azalış tesadüfle açıklanamaz.", "tr"),
    (REF, "Bu eğilim kesindir.", "tr"),
    # A cause, or a link between findings.
    (REF, "The decrease is driven by large-scale returns.", "en"),
    (REF, "The rise in returnees explains this series.", "en"),
    (REF, "Azalışın nedeni kitlesel geri dönüşlerdir.", "tr"),
    (REF, "Bu durum çatışmaların durulduğunu gösteriyor.", "tr"),
    # A name the model was not given, and a region under a ranking.
    (REF, "Many of them moved to Pakistan and Iran.", "en"),
    (IDP, "The burden is heaviest in Kandahar province.", "en"),
    (IDP, "Balkh carries the heaviest load of any province.", "en"),
    (IDP, "En ağır yük Kabul vilayetindedir.", "tr"),
    # The present, for a dated value.
    (REF, "The figure describes the current situation on the ground.", "en"),
    (REF, "Rakam içinde bulunduğumuz yılın durumunu gösterir.", "tr"),
    # Figures in words.
    ("Executive Summary", "Seventeen million people need food assistance.", "en"),
    ("Executive Summary", "About one in three people faces acute food insecurity.", "en"),
    ("Yönetici Özeti", "On yedi milyon kişi gıda yardımına ihtiyaç duyuyor.", "tr"),
    # Change verbs outside the usual ones; Turkish stems narrow before -yor.
    (FS, "Needs have receded.", "en"),
    ("Executive Summary", "Protection needs have ballooned.", "en"),
    (FS, "İhtiyaç geriliyor.", "tr"),
    (FS, "İhtiyaç eridi.", "tr"),
    ("Yönetici Özeti", "Geçen yıla göre daha düşük bir düzey görülüyor.", "tr"),
])
def test_what_a_held_out_review_got_past_the_first_rules_is_dropped(heading, sentence, language):
    assert not _kept(heading, sentence, language)


@pytest.mark.parametrize("heading,sentence", [
    ("Yönetici Özeti", "Bulgular birlikte okunduğunda ihtiyacın ölçeğini gösteriyor, yönünü değil."),
    (REF, "Mülteci sayısındaki azalış, geri dönüş verileriyle birlikte doğrulanmalıdır."),
    (FS, "Üç yıllık değer bir eğilimi değil, ihtiyacın ölçeğini betimliyor."),
    (FS, "Bu insani gösterge artık her yıl izlenmeli."),     # "insani", "artık": not change words
])
def test_turkish_interpretations_are_kept(heading, sentence):
    assert _kept(heading, sentence, language="tr")


@pytest.mark.parametrize("heading,sentence", [
    ("Yönetici Özeti", "Koruma ihtiyacı arttı."),
    ("Yönetici Özeti", "Mülteci sayısı yükseldi."),
    ("Yönetici Özeti", "Durum sabit kalıyor."),
    (REF, "Mülteci sayısı artıyor."),
    (REF, "Azalış istatistiksel olarak anlamlı değildir."),
    (REF, "Bu anlamlılık düzeyi yeterli değil."),
    (REF, "Sayı yarı yarıya indi."),
    (FS, "İhtiyaç iki katına çıktı."),
    (FS, "İhtiyaç 17,4 milyon kişiye ulaştı."),
    (IDP, "Yerinden edilenlerin çoğu Herat'ta."),
    (FS, "İhtiyaç rekor düzeyde."),
    (FS, "Gıda güvenliği ihtiyacı geriledi."),
])
def test_turkish_claims_are_dropped(heading, sentence):
    assert not _kept(heading, sentence, language="tr")


def test_a_total_is_never_claimed_in_a_report_of_plan_lines():
    lines = _findings(note_items=[{"kind": "plan_line", "name": "Protection"}])
    assert not _kept("Executive Summary", "This is the plan's overall protection figure.", findings=lines)
    assert not _kept("Yönetici Özeti", "Bu, planın toplam koruma rakamıdır.", "tr", findings=lines)
    assert not _kept("Yönetici Özeti", "Bu, planın genel koruma rakamıdır.", "tr", findings=lines)
    # Without plan lines the word is harmless ("Genel olarak" is always fine).
    assert _kept("Executive Summary", "Overall, the findings describe scale.")
    assert _kept("Yönetici Özeti", "Genel olarak bulgular ölçeği betimliyor.", "tr", findings=lines)


def test_years_that_are_not_comparable_allow_no_change_under_their_finding():
    f = samples.findings(samples.snapshot(not_comparable="2024, 2025: plan lines"))
    heading = f.sections[0].heading
    assert not _kept(heading, "Needs rose between the plans.", findings=f)
    assert _kept(heading, "Each year's figure should be read on its own.", findings=f)


def test_sentences_are_judged_one_by_one_and_logged_with_the_report(caplog):
    caplog.set_level(logging.INFO, logger="analytics.narrative_check")
    text = (f"## Executive Summary\n\nThe findings describe scale. Needs grew by 4,812 people. "
            f"They leave the direction open.\n\n## {REF}\n\n**Interpretation:** The series is short.\n")
    res = check_commentary(text, _findings(), ALLOWED, "en", label="Afghanistan / All sectors")
    assert res.by_heading == {
        "Executive Summary": "The findings describe scale. They leave the direction open.",
        REF: "The series is short."}          # the label is added in code, not kept twice
    assert res.removed == 1
    assert any("Afghanistan / All sectors" in r.getMessage() and "4,812" in r.getMessage()
               for r in caplog.records)


def test_sections_the_report_does_not_have_are_not_used():
    text = ("Preamble.\n\n## Methods\n\nA Pearson test was run.\n\n## Made-up heading\n\nText.\n\n"
            f"## {FS}\n\n- The scale is large.\n- Needs are at 17.4 million.\n")
    res = check_commentary(text, _findings(), ALLOWED, "en")
    assert res.by_heading == {FS: "The scale is large."}


def test_a_heading_is_matched_whatever_its_case_spacing_or_emphasis():
    res = check_commentary(f"## **{REF.upper()}**  \n\nThe series is short.", _findings(), ALLOWED, "en")
    assert res.by_heading == {REF: "The series is short."}


def test_the_what_changed_section_keeps_given_figures_and_drops_others():
    heading = "What changed since the last report"
    allowed = ALLOWED + " latest value 2.67 million people. PREVIOUS REPORT: 3.10 million people."
    text = (f"## {heading}\n\nRefugees fell from 3.10 million to 2.67 million people. "
            f"IDPs reached 9.9 million. The change is statistically significant.")
    res = check_commentary(text, _findings(), allowed, "en", comparison_heading=heading)
    assert res.comparison == "Refugees fell from 3.10 million to 2.67 million people."
    assert res.by_heading == {} and res.removed == 2
    # Without a previous report the heading is not part of the report.
    assert check_commentary(text, _findings(), allowed, "en").comparison is None


# The five review rounds' wrong claims (tests/analytics/claims_corpus.json: 109 sentences a
# reviewer wrote against live contexts, each a false statement about a finding): none may
# survive as interpretation, under its own finding or under the Executive Summary.
_CORPUS = json.loads((Path(__file__).parent / "claims_corpus.json").read_text(encoding="utf-8"))
_CTX = {k: (Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                               for s in v["sections"]], gaps=[], indicators_covered=[]),
            v["allowed"], v["language"]) for k, v in _CORPUS["contexts"].items()}
_WRONG = [s for s in _CORPUS["sentences"] if s["expect"] == "remove"]


@pytest.mark.parametrize("case", _WRONG, ids=[s["id"] for s in _WRONG])
def test_no_reviewed_wrong_claim_survives(case):
    f, allowed, language = _CTX[case["case"]]
    summary = "Yönetici Özeti" if language == "tr" else "Executive Summary"
    headings = {summary} | ({case["section"]} & {s.heading for s in f.sections})
    for heading in headings:
        res = check_commentary(f"## {heading}\n\n{case['sentence']}", f, allowed, language)
        assert not res.by_heading, heading


# The held-out round (2026-11-19): an independent reviewer wrote 168 false or misleading
# interpretation sentences, mostly without figures, before seeing this checker; 91 got past
# its first rules. The rules were then widened on this set, so it is a regression set, not
# a measure of what a new sentence does. The four left are what no word list catches: a
# false detail on a correct direction and an indicator the report does not have.
_HELD = json.loads((Path(__file__).parent / "claims_heldout.json").read_text(encoding="utf-8"))
_HELD_CTX = {k: (Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                                    for s in v["sections"]], gaps=[], indicators_covered=[],
                          note_items=v["note_items"]), v["allowed"], v["language"])
             for k, v in _HELD["contexts"].items()}
_KNOWN_ESCAPES = {
    "Nutrition needs are lower than they were two years ago.",
    "Malnutrition among children under five has also been falling.",
    "Beslenme ihtiyacı iki yıl önceki düzeyin altına indi.",
    "Beş yaş altı çocuklarda yetersiz beslenme de geriliyor.",
}
_HELD_WRONG = [pytest.param(s, marks=pytest.mark.xfail(strict=True, reason="no word list catches it"))
               if s["sentence"] in _KNOWN_ESCAPES else s
               for s in _HELD["sentences"] if s["expect"] == "drop"]


@pytest.mark.parametrize("case", _HELD_WRONG)
def test_held_out_wrong_claims_are_dropped(case):
    f, allowed, language = _HELD_CTX[case["case"]]
    heading = (("Yönetici Özeti" if language == "tr" else "Executive Summary")
               if case["heading"] == "SUMMARY" else case["heading"])
    assert not check_commentary(f"## {heading}\n\n{case['sentence']}", f, allowed, language).by_heading


def test_most_fine_held_out_sentences_survive():
    """Losing a fine sentence is cheap, but the paragraph must not become empty by rule."""
    fine = [s for s in _HELD["sentences"] if s["expect"] == "keep"]
    kept = 0
    for case in fine:
        f, allowed, language = _HELD_CTX[case["case"]]
        heading = (("Yönetici Özeti" if language == "tr" else "Executive Summary")
                   if case["heading"] == "SUMMARY" else case["heading"])
        kept += bool(check_commentary(f"## {heading}\n\n{case['sentence']}", f, allowed,
                                      language).by_heading)
    assert kept >= 0.6 * len(fine)
