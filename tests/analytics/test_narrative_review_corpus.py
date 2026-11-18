"""The reviewers' sentence corpus (round 2 re-review), run against the live Afghanistan
Food and Nutrition and Protection findings of 2026-11-19 (2025-11-18 to 2026-11-18).
True: a correct sentence that must survive; False: a wrong claim that must go."""
import json
from pathlib import Path

import pytest

from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

_DATA = json.loads((Path(__file__).parent / "afg_findings_2026-11-19.json").read_text(encoding="utf-8"))


def _findings(key):
    d = _DATA[key]
    return Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                              for s in d["sections"]], gaps=[], indicators_covered=[]), d["context"]


FOOD, FOOD_CTX = _findings("food")
PROT, PROT_CTX = _findings("protection")
IPC = next(s.heading for s in FOOD.sections if "IPC" in s.heading)
REF = next(s.heading for s in PROT.sections if s.heading.startswith("Refugees"))
RET = next(s.heading for s in PROT.sections if s.heading.startswith("Returnees"))
PRO = next(s.heading for s in PROT.sections if s.heading.startswith("Protection"))
EXEC = "Executive Summary"

CASES = [
    ("food", IPC, "Food insecurity stood at 32.0% in September 2026 (down from 47.0% in March 2022).", True),
    ("food", IPC, "Food insecurity fell by 21.0 percentage points along the trend line between March 2022 and September 2026.", True),
    ("food", IPC, "The share decreased by about 4.65 percentage points per year.", True),
    ("food", IPC, "The latest value, 32.0%, is lower than the first value of 47.0%.", True),
    ("food", IPC, "About a third of the analysed population (32.0%) was in IPC Phase 3 or above in September 2026.", True),
    ("food", IPC, "Nearly half of the analysed population (47.0%) was in IPC Phase 3 or above in March 2022.", True),
    ("food", IPC, "The share of people in IPC Phase 3 or above declined from 47.0% to 32.0%.", True),
    ("food", IPC, "Food insecurity dropped to 32.0% in September 2026.", True),
    ("food", IPC, "Food insecurity was 32.0%, down 21.0 percentage points along the trend line.", True),
    ("food", IPC, "The decrease of 21.0 percentage points along the trend line is not significant (Holm-adjusted p=0.059).", True),
    ("food", IPC, "Food insecurity went from 47.0% to 32.0%, a decline of 21.0 percentage points along the trend line.", True),
    ("food", IPC, "In September 2026, 32.0% of the analysed population faced crisis or worse, compared with 47.0% in March 2022.", True),
    ("food", IPC, "The 95% confidence interval of the slope runs from -7.99 to 0 percentage points per year.", True),
    ("food", IPC, "Food insecurity remained high at 32.0% in September 2026, down from 47.0% in March 2022.", True),
    ("food", IPC, "Food insecurity fell from 47.0% to 32.0%, so roughly a third of the analysed population is still affected.", True),
    ("food", IPC, "The slope of -4.65 percentage points per year means the share fell.", True),
    ("food", IPC, "Food insecurity was 47.0% in March 2022; by September 2026 it had fallen to 32.0%.", True),
    ("food", IPC, "Up to 47.0% of the analysed population was food insecure in March 2022.", True),
    ("food", IPC, "The share rose to 47.0% in March 2022 before falling to 32.0% in September 2026.", True),
    ("food", IPC, "Food insecurity fell by 21.0 percentage points, from 47.0% to 32.0%.", True),
    ("food", IPC, "The share was 32.0% in September 2026, 21.0 percentage points lower along the trend line.", True),
    ("food", IPC, "Food insecurity fell by 32% between 2022 and 2026.", False),
    ("food", IPC, "Food insecurity dropped by 21.0% over the period.", False),
    ("food", IPC, "Food insecurity rose by 21.0 percentage points.", False),
    ("food", IPC, "Food insecurity increased by 4.65 percentage points per year.", False),
    ("food", IPC, "Food insecurity halved between 2022 and 2026.", False),
    ("food", IPC, "Food insecurity dropped to about half its 2022 level.", False),
    ("food", IPC, "Food insecurity fell by a third between 2022 and 2026.", False),
    ("food", IPC, "Food insecurity was cut in half.", False),
    ("food", IPC, "Food insecurity went down by half.", False),
    ("food", IPC, "Food insecurity decreased to half of its 2022 level.", False),
    ("food", IPC, "Food insecurity is now half what it was in 2022.", False),
    ("food", IPC, "Food insecurity was 21.0 percentage points higher in September 2026 than in March 2022.", False),
    ("food", IPC, "Food insecurity fell 32 percent.", False),
    ("food", IPC, "Food insecurity fell by nearly a third, from 47.0% to 32.0%.", False),
    ("food", IPC, "Food insecurity declined by 21.0 per cent.", False),
    ("food", IPC, "Food insecurity saw a 32% reduction.", False),
    ("food", IPC, "Food insecurity was reduced by half.", False),
    ("food", IPC, "Food insecurity fell to around half of the 2022 share.", False),
    ("food", IPC, "Food insecurity rose 21.0 percentage points along the trend line.", False),
    ("food", IPC, "Food insecurity fell by 21.0 percentage points, a 32% improvement.", False),
    ("food", EXEC, "Food insecurity fell by 32% between 2022 and 2026.", False),
    ("food", EXEC, "Food insecurity rose by 21.0 percentage points.", False),
    ("food", EXEC, "Food insecurity halved between 2022 and 2026.", False),
    # Turkish, IPC
    ("food", IPC, "Analiz edilen nüfusun üçte biri insani yardıma ihtiyaç duyuyordu.", True),
    ("food", IPC, "Eylül 2026'da analiz edilen nüfusun %32,0'ı IPC Aşama 3 ve üzerindeydi.", True),
    ("food", IPC, "Mart 2022'de nüfusun yarısına yakını (%47,0) IPC Aşama 3 ve üzerindeydi.", True),
    ("food", IPC, "Gıda güvensizliği trend çizgisi boyunca 21,0 yüzde puan azaldı.", True),
    ("food", IPC, "Oran yılda 4,65 yüzde puan geriledi.", True),
    ("food", IPC, "Gıda güvensizliği %47,0'dan %32,0'a düştü.", True),
    ("food", IPC, "Gıda güvensizliği artık %32,0 düzeyinde.", True),
    ("food", IPC, "Oran %32,0 ile hâlâ yüksek; bu düşük bir seviye sayılmaz.", True),
    ("food", IPC, "Nüfusun büyük bir kısmı, yani %32,0'ı, kriz düzeyinde ya da daha kötü durumdaydı.", True),
    ("food", IPC, "Düşüş istatistiksel olarak anlamlı değildir (Holm düzeltmeli p=0,059).", True),
    ("food", IPC, "Gıda güvensizliği Eylül 2026'da %32,0 oranında seyretti.", True),
    ("food", IPC, "İnsani durum, %32,0 ile ağırlığını koruyor.", True),
    ("food", IPC, "Gıda güvensizliği Mart 2022'deki %47,0'dan Eylül 2026'da %32,0'a geriledi.", True),
    ("food", IPC, "Nüfusun yarısına yakını, %47,0'ı, Mart 2022'de kriz düzeyindeydi; bu oran Eylül 2026'da %32,0'a indi.", True),
    ("food", IPC, "Gıda güvensizliği 21,0 yüzde puanlık bir düşüşle %32,0'a geriledi.", True),
    ("food", IPC, "Analiz edilen nüfusun yarısı insani yardıma muhtaç değildi.", True),
    ("food", IPC, "Gıda güvensizliği %32 azaldı.", False),
    ("food", IPC, "Gıda güvensizliği yarı yarıya azaldı.", False),
    ("food", IPC, "Gıda güvensizliği yarısına indi.", False),
    ("food", IPC, "Gıda güvensizliği 21,0 yüzde puan arttı.", False),
    ("food", IPC, "Gıda güvensizliği üçte bir oranında azaldı.", False),
    ("food", IPC, "Gıda güvensizliği yüzde 21'lik bir düşüş gösterdi.", False),
    ("food", IPC, "Gıda güvensizliği %21,0 düştü.", False),
    ("food", IPC, "Oran yarıya düştü.", False),
    ("food", IPC, "Gıda güvensizliği iki katına çıktı.", False),
    ("food", IPC, "Gıda güvensizliği yüzde 32 oranında geriledi.", False),
    ("food", IPC, "Gıda güvensizliği yılda 4,65 yüzde puan yükseldi.", False),
    ("food", IPC, "Gıda güvensizliği 2022'ye göre yarı yarıya geriledi.", False),
    ("food", IPC, "Gıda güvensizliği yarısına geriledi.", False),
    ("food", IPC, "Gıda güvensizliği yaklaşık yarısına düştü.", False),
    ("food", IPC, "Gıda güvensizliği yarı yarıya düşmüştür.", False),
    ("food", IPC, "Gıda güvensizliği 21,0 yüzde puanlık bir artış gösterdi.", False),
    ("food", IPC, "Gıda güvensizliğinde %32'lik bir azalma oldu.", False),
    # Turkish formal past forms (re-review regression)
    ("food", IPC, "Gıda güvensizliği %32 düşmüştür.", False),
    ("food", IPC, "Gıda güvensizliği %32 artmıştır.", False),
    ("food", IPC, "Gıda güvensizliği yarısına inmiştir.", False),
    ("food", IPC, "Gıda güvensizliği 21,0 yüzde puan artmıştır.", False),
    ("food", IPC, "Gıda güvensizliği yüzde 32 oranında düşmüştür.", False),
    ("food", IPC, "Gıda güvensizliği %32 geriledi.", False),
    ("food", IPC, "Gıda güvensizliği 21,0 yüzde puan yükselmiştir.", False),
    ("food", IPC, "Gıda güvensizliği yüzde 32 azalmıştır.", False),
    ("food", IPC, "Gıda güvensizliği %32 oranında düşüş gösterdi.", False),
    ("food", IPC, "Gıda güvensizliği yüzde 32 düştü.", False),
    ("food", IPC, "Gıda güvensizliği %32 azalmıştı.", False),
    ("food", IPC, "Gıda güvensizliği %32 düşmektedir.", False),
    ("food", IPC, "Gıda güvensizliği %32 artıyor.", False),
    # counts
    ("protection", REF, "The number of refugees fell by 38.1% along the trend line.", True),
    ("protection", REF, "Refugees fell from 5.66 million in 2022 to 2.67 million in 2025, roughly halving.", True),
    ("protection", REF, "Mülteci sayısı trend çizgisi boyunca %38,1 azaldı.", True),
    ("protection", REF, "Mülteci sayısı 2022'deki 5,66 milyondan 2025'te 2,67 milyona, yaklaşık yarısına indi.", True),
    ("protection", REF, "Mülteci sayısı 2022'deki 5,66 milyondan 2025'te 2,67 milyona indi.", True),
    ("protection", REF, "Mülteci sayısı 2022'de 5,66 milyon iken 2025'te 2,67 milyon oldu.", True),
    ("protection", REF, "Mülteci sayısı 5,66 milyondan 2,67 milyona indi.", True),
    ("protection", REF, "Refugees numbered 2.67 million in 2025, down 38.1% along the trend line.", True),
    ("protection", REF, "The number of refugees rose by 38.1% along the trend line.", False),
    ("protection", REF, "Mülteci sayısı trend çizgisi boyunca %38,1 arttı.", False),
    ("protection", REF, "Refugees tripled between 2022 and 2025.", False),
    ("protection", REF, "Refugees fell by a third.", False),
    ("protection", RET, "Returnees increased from 6510 people in 2022 to 1.95 million in 2025.", True),
    ("protection", RET, "Geri dönenlerin sayısı 2022'de 6.510 iken 2025'te 1,95 milyona yükseldi.", True),
    ("protection", RET, "Returnees doubled.", False),
    # a section whose years are not comparable
    ("protection", PRO, "The values are not comparable across years (2024, 2025: possibly one of the plan's separate protection lines rather than its overall figure; 2026: the plan's only protection figure), so no trend is reported.", True),
    ("protection", PRO, "Değerler yıllar arasında karşılaştırılamaz: 2024 ve 2025 planın ayrı koruma satırlarından biri olabilir, 2026 ise planın tek koruma rakamıdır; bu yüzden trend raporlanmadı.", True),
    ("protection", PRO, "The figure was 14.8 million in 2024, 14.2 million in 2025 and 15.0 million in 2026; these years are not comparable.", True),
    ("protection", PRO, "Koruma ihtiyacı 2024'te 14,8 milyon, 2025'te 14,2 milyon ve 2026'da 15,0 milyon kişiydi.", True),
    ("protection", PRO, "Protection needs rose from 14.2 million in 2025 to 15.0 million in 2026.", False),
    ("protection", PRO, "Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyona yükseldi.", False),
    ("protection", PRO, "Protection needs were higher in 2026 than in 2025.", False),
]


@pytest.mark.parametrize("key,heading,sentence,keep", CASES)
def test_reviewer_corpus(key, heading, sentence, keep):
    findings, context = (FOOD, FOOD_CTX) if key == "food" else (PROT, PROT_CTX)
    language = "tr" if any(c in sentence for c in "ğışçöüİ") else "en"
    result = verify_narrative(f"## {heading}\n\n{sentence}", findings, context, language)
    assert (result.removed == 0) == keep


# --- Round 3: the same corpus on the reader-form context (values "15.0 million people",
# dates "January 2026", the look-back said once), rebuilt from live HDX HAPI. ---

_DATA_R3 = json.loads((Path(__file__).parent / "afg_findings_r3.json").read_text(encoding="utf-8"))


def _findings_r3(key):
    d = _DATA_R3[key]
    return Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                              for s in d["sections"]], gaps=[], indicators_covered=[]), d["context"]


FOOD_R3, FOOD_R3_CTX = _findings_r3("food")
PROT_R3, PROT_R3_CTX = _findings_r3("protection")


@pytest.mark.parametrize("key,heading,sentence,keep", CASES)
def test_reviewer_corpus_on_the_round3_context(key, heading, sentence, keep):
    findings, context = (FOOD_R3, FOOD_R3_CTX) if key == "food" else (PROT_R3, PROT_R3_CTX)
    language = "tr" if any(c in sentence for c in "ğışçöüİ") else "en"
    result = verify_narrative(f"## {heading}\n\n{sentence}", findings, context, language)
    assert (result.removed == 0) == keep


# Sentences in the reader forms the round-3 context gives (EN and the Turkish the model
# writes from it): all must survive.
FOOD_IPC_R3 = next(s.heading for s in FOOD_R3.sections if "IPC" in s.heading)
FOOD_FSC_R3 = next(s.heading for s in FOOD_R3.sections if s.heading.startswith("Food security"))
PROT_IDP_R3 = next(s.heading for s in PROT_R3.sections if s.heading.endswith("Latest Values")
                   and "IDP" in s.heading)
PROT_REG_R3 = next(s.heading for s in PROT_R3.sections if "Regional" in s.heading)
READER_FORMS = [
    ("food", FOOD_FSC_R3, "Food security needs stood at 17.4 million people in 2026, up from 14.8 million in 2025.", "en"),
    ("food", FOOD_FSC_R3, "In 2026, 17.4 million people needed food security assistance.", "en"),
    ("food", FOOD_FSC_R3, "Gıda güvenliği alanında 2026 yılında 17,4 milyon kişi yardıma ihtiyaç duyuyordu.", "tr"),
    ("food", FOOD_FSC_R3, "İhtiyaç 2025'teki 14,8 milyondan 2026'da 17,4 milyon kişiye yükseldi.", "tr"),
    ("food", FOOD_IPC_R3, "In September 2026, 32.0% of the analysed population was in IPC Phase 3 or above, against 47.0% in March 2022.", "en"),
    ("food", FOOD_IPC_R3, "Eylül 2026'da analiz edilen nüfusun %32,0'ı IPC Aşama 3 ve üzerindeydi; Mart 2022'de bu oran %47,0'dı.", "tr"),
    ("food", FOOD_IPC_R3, "Over the look-back window, March 2022 to September 2026, the share fell by 21.0 percentage points along the trend line.", "en"),
    ("protection", PROT_IDP_R3, "In January 2026, 3.06 million people were internally displaced, down from 3.11 million in May 2025.", "en"),
    ("protection", PROT_IDP_R3, "Ocak 2026'da 3,06 milyon kişi ülke içinde yerinden edilmiş durumdaydı.", "tr"),
    ("protection", PROT_REG_R3, "As of January 2026, Herat hosted the most IDPs, with 443,000 people.", "en"),
    ("protection", PROT_REG_R3, "Ocak 2026 itibarıyla en çok IDP 443.000 kişiyle Herat'taydı.", "tr"),
    ("protection", PROT_REG_R3, "Herat (443 bin kişi), Balkh (363 bin) ve Kabil (310 bin) en yüksek bölgelerdi.", "tr"),
]


@pytest.mark.parametrize("key,heading,sentence,language", READER_FORMS)
def test_reader_form_sentences_survive(key, heading, sentence, language):
    findings, context = (FOOD_R3, FOOD_R3_CTX) if key == "food" else (PROT_R3, PROT_R3_CTX)
    assert verify_narrative(f"## {heading}\n\n{sentence}", findings, context, language).removed == 0


# --- Round 3: an Executive Summary opening with the sector's headline and its caveat
# survives; the same figure presented as a rise from the previous year does not. ---

@pytest.mark.parametrize("sentence,language,keep", [
    ("Protection needs stood at 15.0 million people in 2026; earlier years are reported on a "
     "different basis and are not comparable.", "en", True),
    ("Koruma ihtiyacı 2026'da 15,0 milyon kişiydi; önceki yıllar farklı bir temelde raporlandığı "
     "için karşılaştırılamaz.", "tr", True),
    ("Protection needs rose to 15.0 million people in 2026 from 14.2 million in 2025.", "en", False),
    ("Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyon kişiye yükseldi.", "tr", False),
])
def test_the_headline_sentence_with_its_caveat_survives(sentence, language, keep):
    assert "HEADLINE" in PROT_R3_CTX
    heading = "Executive Summary" if language == "en" else "Yönetici Özeti"
    res = verify_narrative(f"## {heading}\n\n{sentence}", PROT_R3, PROT_R3_CTX, language)
    assert (res.removed == 0) == keep
