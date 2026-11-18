"""Relative-change claims are checked, not only forbidden (owner feedback, round 2).

On the live Afghanistan Food and Nutrition context, "food insecurity fell by about 32%"
passed the number check (32 is the latest value, 32.0%) and "nearly halved" has no
number at all, so a wrong relative change about a share could reach a report.
The context below is the real one (HDX HAPI, 2026-11-18)."""
from pathlib import Path

import pytest

from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

CONTEXT = (Path(__file__).parent / "afg_food_nutrition_context.txt").read_text(encoding="utf-8")
DIRECTIVE = ("Generate the technical monitoring report narrative. Country: Afghanistan. "
             "Sector(s): Food and Nutrition. Period: 2025-11-18 to 2026-11-18.")

FS_H = "Food security: people in need — Latest Values"
NUT_H = "Nutrition: people in need — Latest Values"
IPC_H = "Food insecurity (IPC 3+, % of the analysed population) — Trend Analysis"


def _afg_findings():
    return Findings(sections=[
        ReportSection(FS_H, {"kind": "snapshot", "p_value": None, "tested": False,
                             "significant": False, "value_unit": "people",
                             "values": [15_823_677.0, 14_764_729.0, 17_412_653.0]}, None, ""),
        ReportSection(NUT_H, {"kind": "snapshot", "p_value": None, "tested": False,
                              "significant": False, "value_unit": "people",
                              "values": [7_399_632.0, 7_801_981.0, 7_464_230.0]}, None, ""),
        ReportSection(IPC_H, {"kind": "trend", "p_value": 0.059, "tested": True,
                              "significant": False, "unit": "percentage points",
                              "value_unit": "%", "slope": -4.65, "line_change": -20.97,
                              "pct_change": -48.3, "first_value": 47.0, "latest_value": 32.0},
                      None, ""),
    ], gaps=[], indicators_covered=["pin_food_security", "pin_nutrition", "food_security"])


def _kept(sentence: str, section: str | None, language: str = "en") -> bool:
    text = (f"## {section}\n\n{sentence}" if section else f"## Executive Summary\n\n{sentence}")
    return verify_narrative(text, _afg_findings(), f"{CONTEXT}\n{DIRECTIVE}", language).removed == 0


CORRECT_EN = [
    (IPC_H, "As of September 2026, 32.0% of the analysed population was in IPC Phase 3 or above."),
    (IPC_H, "The share fell from 47.0% in March 2022 to 32.0% in September 2026."),
    (IPC_H, "Along the trend line the share fell by 21.0 percentage points between March 2022 "
            "and September 2026."),
    (IPC_H, "The decline of 4.65 percentage points per year is not statistically significant "
            "(p=0.059, Holm-adjusted p=0.059)."),
    (IPC_H, "The 95% confidence interval of the slope runs from -7.99 to 0 percentage points."),
    (FS_H, "In 2026, 17.4 million people needed food security assistance, up from 14.8 million "
           "in 2025."),
    (None, "In September 2026, 32.0% of the analysed population faced acute food insecurity."),
    (None, "Food insecurity stood at 32% of the analysed population in September 2026."),
]
WRONG_EN = [
    (IPC_H, "Food insecurity fell by about 32% over the period."),
    (IPC_H, "This is a 21% decline in food insecurity."),
    (IPC_H, "Food insecurity nearly halved since 2022."),
    (IPC_H, "The share of people in IPC Phase 3+ was cut in half."),
    (None, "Food insecurity fell by 32% over five years."),
    (None, "Acute food insecurity dropped 48.3% along the trend line."),
    (FS_H, "The number of people in need of food security assistance doubled between 2024 "
           "and 2026."),
]
CORRECT_TR = [
    (IPC_H, "Eylül 2026 itibarıyla analiz edilen nüfusun %32,0'si IPC Aşama 3 ve üzerindeydi."),
    (IPC_H, "Oran Mart 2022'deki %47,0'den Eylül 2026'da %32,0'ye geriledi."),
    (IPC_H, "Eğilim çizgisi boyunca oran 21,0 yüzde puan azaldı."),
    (IPC_H, "Oran Eylül 2026'da %32 düzeyinde kaldı."),
    (FS_H, "2026'da 17,4 milyon kişinin gıda güvenliği yardımına ihtiyacı vardı."),
    (None, "Eylül 2026'da analiz edilen nüfusun yüzde 32'si akut gıda güvensizliği yaşıyordu."),
]
WRONG_TR = [
    (IPC_H, "Gıda güvensizliği %32 azaldı."),
    (IPC_H, "Gıda güvensizliğinde yüzde 32'lik bir düşüş yaşandı."),
    (IPC_H, "Gıda güvensizliği yarı yarıya azaldı."),
    (IPC_H, "Gıda güvensizliği 2022'den bu yana yarıya indi."),
    (None, "Gıda güvensizliği beş yılda %32 oranında azaldı."),
    (FS_H, "Gıda güvenliği yardımına ihtiyaç duyan kişi sayısı iki katına çıktı."),
    (FS_H, "İhtiyaç duyan kişi sayısı 2024'ten bu yana ikiye katlandı."),
]


@pytest.mark.parametrize("section,sentence", CORRECT_EN)
def test_correct_english_sentences_survive(section, sentence):
    assert _kept(sentence, section)


@pytest.mark.parametrize("section,sentence", WRONG_EN)
def test_wrong_english_relative_claims_are_removed(section, sentence):
    assert not _kept(sentence, section)


@pytest.mark.parametrize("section,sentence", CORRECT_TR)
def test_correct_turkish_sentences_survive(section, sentence):
    assert _kept(sentence, section, "tr")


@pytest.mark.parametrize("section,sentence", WRONG_TR)
def test_wrong_turkish_relative_claims_are_removed(section, sentence):
    assert not _kept(sentence, section, "tr")


# --- "All sectors": computed relative changes of counts stay legitimate. ---

REF_H = "Refugees (people) — Trend Analysis"
RET_H = "Returnees (people) — Trend Analysis"
COUNTS_CONTEXT = (
    f"## {REF_H}\nRefugees (people): direction=increasing, Sen slope=500000 per year, "
    "relative change along the trend line 2022-01-01 → 2025-01-01=+236.8%, observed first value "
    "1000000 people (2022-01-01), latest value 3100000 people (2025-01-01), n=4.\n\n"
    f"## {RET_H}\nReturnees (people): direction=decreasing, Sen slope=-300000 per year, "
    "relative change along the trend line 2022-01-01 → 2025-01-01=-48.0%, observed first value "
    "2000000 people (2022-01-01), latest value 1000000 people (2025-01-01), n=4.\n"
)


def _counts_kept(sentence: str, section: str | None) -> bool:
    findings = Findings(sections=[
        ReportSection(REF_H, {"kind": "trend", "p_value": 0.2, "significant": False,
                              "unit": "", "value_unit": "people", "pct_change": 236.8,
                              "line_change": None, "first_value": 1e6, "latest_value": 3.1e6},
                      None, ""),
        ReportSection(RET_H, {"kind": "trend", "p_value": 0.2, "significant": False,
                              "unit": "", "value_unit": "people", "pct_change": -48.0,
                              "line_change": None, "first_value": 2e6, "latest_value": 1e6},
                      None, ""),
    ], gaps=[], indicators_covered=["refugees", "returnees"])
    text = f"## {section or 'Executive Summary'}\n\n{sentence}"
    return verify_narrative(text, findings, COUNTS_CONTEXT, "en").removed == 0


def test_a_computed_relative_change_of_a_count_still_passes():
    assert _counts_kept("Refugee numbers rose by 236.8% along the trend line.", REF_H)
    assert _counts_kept("Refugees rose by +236.8% along the trend line.", None)
    assert _counts_kept("Returnees fell 48.0% along the trend line.", RET_H)


def test_multiplicative_words_about_counts_need_the_observed_values():
    assert _counts_kept("The number of refugees tripled between 2022 and 2025.", REF_H)
    assert _counts_kept("Returnees halved between 2022 and 2025.", RET_H)
    assert not _counts_kept("Returnees tripled between 2022 and 2025.", RET_H)
    assert not _counts_kept("Refugee numbers halved between 2022 and 2025.", REF_H)


def test_a_relative_change_the_code_did_not_compute_is_removed_for_counts_too():
    # 3,100,000 / 1,000,000 is +210%, but the model was not given that figure.
    assert not _counts_kept("Refugees rose by 210% between 2022 and 2025.", REF_H)


# --- Round 2 decision: the plan-line note is restated in Data Coverage & Limitations and
# must survive the check. ---

GEN_H = "Protection: people in need — Latest Values"
LINE_CONTEXT = (
    f"## {GEN_H}\nProtection: people in need: 1 observation (2025-01-01) — too few for "
    "a trend test (at least 4 are needed), so no trend or statistical test is reported. Values: "
    "2025-01-01 467000 people. Latest value as of the chosen period: 467000 people (2025-01-01).\n\n"
    "DATA NOTES:\n- Protection: people in need, 2025: the plan reports protection in separate "
    "lines (Child Protection 1610000, Gender Based Violence 1540000); the figure here (467000) is "
    "below one of the plan's protection lines, so it is not the plan's overall protection figure, "
    "which is higher; this report does not add the lines up, because people can be counted in "
    "more than one.\n"
)


@pytest.mark.parametrize("language,sentence", [
    ("en", "The plan reports protection in separate lines: child protection (1.61 million people) "
           "and gender-based violence (1.54 million people)."),
    ("en", "The 467,000 figure is not the plan's overall protection figure, which is higher, and "
           "the lines are not added up because people can be counted in more than one."),
    ("tr", "Plan korumayı ayrı satırlarda raporluyor: çocuk koruma 1,61 milyon ve toplumsal "
           "cinsiyete dayalı şiddet 1,54 milyon kişi."),
    ("tr", "467 bin rakamı planın genel koruma toplamı değildir; toplam daha yüksektir ve aynı "
           "kişi birden fazla satırda sayılabildiği için satırlar toplanmadı."),
])
def test_the_plan_line_note_survives_in_data_coverage(language, sentence):
    findings = Findings(sections=[ReportSection(GEN_H, {"kind": "snapshot", "p_value": None,
                                                        "tested": False, "value_unit": "people",
                                                        "values": [349_999.0]}, None, "")],
                        gaps=[], indicators_covered=["pin_protection"])
    text = f"## Data Coverage & Limitations\n\n{sentence}"
    assert verify_narrative(text, findings, LINE_CONTEXT, language).removed == 0


# --- Round 2 decision: fractional changes ("by a third", "üçte bir") get the same rule as
# halved/doubled. ---

def test_a_fraction_as_a_level_is_not_a_change_claim():
    assert _kept("About a third of the analysed population faced acute food insecurity in "
                 "September 2026.", None)
    assert _kept("Eylül 2026'da analiz edilen nüfusun üçte biri akut gıda güvensizliği "
                 "yaşıyordu.", None, "tr")


@pytest.mark.parametrize("section,sentence,language", [
    (IPC_H, "Food insecurity fell by a third between 2022 and 2026.", "en"),
    (IPC_H, "A quarter fewer people were food insecure in 2026.", "en"),
    (IPC_H, "Gıda güvensizliği 2022'den bu yana üçte bir oranında azaldı.", "tr"),
    (FS_H, "People in need of food security assistance rose by two-thirds.", "en"),
    (FS_H, "İhtiyaç duyan kişi sayısı dörtte bir arttı.", "tr"),
])
def test_an_unsupported_fractional_change_is_removed(section, sentence, language):
    assert not _kept(sentence, section, language)


def test_a_fractional_change_of_a_count_needs_the_observed_values():
    # Returnees 2,000,000 -> 1,000,000 (ratio 0.5); refugees 1,000,000 -> 3,100,000.
    assert _counts_kept("Returnees fell by half between 2022 and 2025.", RET_H)
    assert not _counts_kept("Returnees fell by a third between 2022 and 2025.", RET_H)
    assert not _counts_kept("Refugee numbers rose by a quarter.", REF_H)


def test_a_supported_fractional_change_of_a_count_is_kept():
    findings_ctx = (f"## {RET_H}\nReturnees (people): observed first value 3000000 people "
                    "(2022-01-01), latest value 2000000 people (2025-01-01), n=4.\n")
    findings = Findings(sections=[ReportSection(RET_H, {
        "kind": "trend", "p_value": 0.2, "significant": False, "unit": "", "value_unit": "people",
        "pct_change": None, "line_change": None, "first_value": 3e6, "latest_value": 2e6},
        None, "")], gaps=[], indicators_covered=["returnees"])
    for sentence, language in (("Returnees fell by a third between 2022 and 2025.", "en"),
                               ("Geri dönenlerin sayısı üçte bir oranında azaldı.", "tr")):
        text = f"## {RET_H}\n\n{sentence}"
        assert verify_narrative(text, findings, findings_ctx, language).removed == 0


def test_the_not_comparable_statement_survives():
    heading = "Protection: people in need — Latest Values"
    context = (f"## {heading}\nProtection: people in need: 3 observations from 2024-01-01 to "
               "2026-01-01 — the values are not comparable across years (2024, 2025: one of the "
               "plan's separate protection lines, possibly its overall figure; 2026: the plan's "
               "only protection figure), so no trend or statistical test is reported. Values: "
               "2024-01-01 14800000 people; 2025-01-01 14200000 people; 2026-01-01 15000000 people.\n")
    findings = Findings(sections=[ReportSection(heading, {"kind": "snapshot", "p_value": None,
                                                          "tested": False, "value_unit": "people",
                                                          "values": [14.8e6, 14.2e6, 15.0e6]},
                                                None, "")], gaps=[], indicators_covered=["pin_protection"])
    for sentence, language in (
            ("The 2024 and 2025 figures are one of the plan's separate protection lines, while the "
             "2026 figure of 15.0 million is the plan's only protection figure, so the values are "
             "not comparable across years.", "en"),
            ("2024 ve 2025 rakamları planın ayrı koruma satırlarından biri, 2026'daki 15,0 milyon ise "
             "planın tek koruma rakamı olduğundan değerler yıllar arasında karşılaştırılamaz.", "tr")):
        text = f"## {heading}\n\n{sentence}"
        assert verify_narrative(text, findings, context, language).removed == 0


# --- Review of round 2: level sentences the check deleted, and "to half" it missed. ---

MUST_SURVIVE = [
    (None, "Analiz edilen nüfusun üçte biri insani yardıma ihtiyaç duyuyordu.", "tr"),
    (IPC_H, "Nüfusun yarısına yakını Eylül 2026'da IPC Aşama 3 ve üzerindeydi.", "tr"),
    (IPC_H, "Nüfusun yarıya yakın bir kısmı 2022'de IPC Aşama 3 ve üzerindeydi.", "tr"),
    (IPC_H, "Gıda güvensizliği artık %32 düzeyinde.", "tr"),
    (IPC_H, "Oran Eylül 2026'da %32 ile düşük düzeyde kaldı.", "tr"),
    (IPC_H, "Eylül 2026'da %32 büyük bir paydı.", "tr"),
    (IPC_H, "Azami oran Mart 2022'de %47,0 oldu.", "tr"),
    (IPC_H, "Eylül 2026'da %32 gerilim bölgelerinde yaşıyordu.", "tr"),
    (IPC_H, "Food insecurity stood at 32.0% (down from 47.0% in March 2022).", "en"),
    (IPC_H, "The share was 32.0% in September 2026, down from 47.0% in March 2022.", "en"),
    (IPC_H, "A fellow analysis put the share at 32.0% in September 2026.", "en"),
    (IPC_H, "The 32% cutoff marks IPC Phase 3 or above in September 2026.", "en"),
    (IPC_H, "The 32.0% figure arose from the September 2026 analysis, as the prose says.", "en"),
    (IPC_H, "About 32% uptake of IPC Phase 3 classification was reported in September 2026.", "en"),
    (None, "Humanitarian access was supported by half of the partners in 2026.", "en"),
]
MUST_GO = [
    (IPC_H, "Food insecurity dropped to half its 2022 level.", "en"),
    (IPC_H, "Food insecurity fell to roughly half its 2022 level.", "en"),
    (IPC_H, "Food insecurity was cut by half.", "en"),
    (IPC_H, "Gıda güvensizliği 2022'den bu yana yarısına indi.", "tr"),
    (IPC_H, "Gıda güvensizliği yarısına geriledi.", "tr"),
    (IPC_H, "Gıda güvensizliği yarıya düştü.", "tr"),
    (IPC_H, "Gıda güvensizliği %32 oranında indi.", "tr"),
]


@pytest.mark.parametrize("section,sentence,language", MUST_SURVIVE)
def test_level_sentences_survive(section, sentence, language):
    assert _kept(sentence, section, language)


@pytest.mark.parametrize("section,sentence,language", MUST_GO)
def test_to_half_claims_are_removed(section, sentence, language):
    assert not _kept(sentence, section, language)
