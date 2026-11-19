"""The round-3 reviewer's sentence corpus (sentences.py, extra.py, extra2.py) on the seven
contexts it used, rebuilt from live HDX HAPI with the current code. "keep": a correct
sentence that must survive; "remove": a wrong claim that must be removed."""
import json
from pathlib import Path

import pytest

from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

_DATA = json.loads((Path(__file__).parent / "review_r3b_sets.json").read_text(encoding="utf-8"))
CTX = {k: (Findings(sections=[ReportSection(s["heading"], s["stat_result"], None, "")
                              for s in v["sections"]], gaps=[], indicators_covered=[]),
           f"{v['context']}\n{v['directive']}", v["language"]) for k, v in _DATA.items()}

ES, ESTR, DC, M = "Executive Summary", "Yönetici Özeti", "Data Coverage & Limitations", "Methods"
FS = "Food security: people in need — Latest Values"
NU = "Nutrition: people in need — Latest Values"
IPC = "Food insecurity (IPC 3+, % of the analysed population) — Trend Analysis"
FST = "Gıda güvenliği: insani yardıma ihtiyaç duyan kişiler — Son Değerler"
NUT = "Beslenme: insani yardıma ihtiyaç duyan kişiler — Son Değerler"
IPCT = "Gıda güvensizliği (IPC 3+, analiz edilen nüfusun yüzdesi) — Eğilim Analizi"
PRO = "Protection: people in need — Latest Values"
PROT = "Koruma: insani yardıma ihtiyaç duyan kişiler — Son Değerler"
REF = "Refugees (people) — Trend Analysis"
RET = "Returnees (people) — Trend Analysis"
IDP = "Internally displaced people (IDPs) — Latest Values"
IDPR = "Internally displaced people (IDPs) — Regional Analysis"
FUN = "Humanitarian funding (USD) — Trend Analysis"
HREF = "Refugees (people) — Trend Analysis"
HIDP = "Internally displaced people (IDPs) — Trend Analysis"
HREG = "Internally displaced people (IDPs) — Regional Analysis"
IDPT = "Ülke içinde yerinden edilmiş kişiler (IDP) — Son Değerler"


S = [
    # --- AFG Food and Nutrition, EN ---
    ("A1", "A", ES, "In Afghanistan, 17.4 million people needed food security assistance in 2026 and 7.46 million needed nutrition assistance.", "keep"),
    ("A2", "A", ES, "This report covers the period from 19 November 2025 to 19 November 2026.", "keep"),
    ("A3", "A", ES, "Because the chosen one-year period holds too few observations, the values and trends below cover a five-year look-back window from 19 November 2021 to 19 November 2026.", "keep"),
    ("A4", "A", ES, "In 2026, 17.9 million people needed food security assistance.", "remove"),
    ("A5", "A", ES, "Food security needs reached 17.4 million people in 2027.", "remove"),
    ("A6", "A", ES, "The share of the analysed population in IPC Phase 3 or above fell from 47.0% in March 2022 to 32.0% in September 2026, a decrease of 21.0 percentage points along the trend line that is not statistically significant (p=0.059).", "keep"),
    ("A7", "A", ES, "The share in IPC Phase 3 or above fell significantly, by 21.0 percentage points.", "remove"),
    ("A8", "A", ES, "Food insecurity fell by 32% over the period.", "remove"),
    ("A9", "A", ES, "The latest IPC analysis, from October 2026, placed 32.0% of the analysed population in Phase 3 or above.", "remove"),
    ("A10", "A", FS, "Food security: people in need stood at 17.4 million people in 2026, up from 14.8 million people in 2025; the figure was 15.8 million people in 2024.", "keep"),
    ("A11", "A", FS, "These values cover the look-back window.", "keep"),
    ("A12", "A", FS, "Three observations are too few for a trend test.", "keep"),
    ("A13", "A", FS, "Food security needs rose significantly between 2025 and 2026.", "remove"),
    ("A14", "A", FS, "The increase from 14.8 million to 17.4 million is not statistically significant.", "remove"),
    ("A15", "A", FS, "Food security needs rose by 17.6% between 2025 and 2026.", "remove"),
    ("A16", "A", FS, "Food security needs fell to 14.8 million people in 2026.", "remove"),
    ("A17", "A", NU, "Nutrition: people in need was 7.46 million people in 2026, down from 7.80 million people in 2025 and slightly above the 7.40 million people of 2024.", "keep"),
    ("A18", "A", NU, "Nutrition needs were 7.6 million people in 2026.", "remove"),
    ("A19", "A", IPC, "Food insecurity (IPC 3+, % of the analysed population) stood at 32.0% in September 2026, against 47.0% in March 2022.", "keep"),
    ("A20", "A", IPC, "Over the look-back window the trend is decreasing, with a Sen slope of -4.65 percentage points per year (95% CI -7.99 to 0 percentage points), but the Mann-Kendall test was not statistically significant (p=0.059).", "keep"),
    ("A21", "A", IPC, "The decline was not found to be statistically significant (p=0.059).", "keep"),
    ("A22", "A", IPC, "The decline is statistically significant (p=0.059).", "remove"),
    ("A23", "A", IPC, "Although not large, the decline is statistically significant.", "remove"),
    ("A24", "A", IPC, "The share fell by 21.0 percentage points along the trend line, and this decline is not statistically significant.", "keep"),
    ("A25", "A", IPC, "The share rose by 21.0 percentage points along the trend line.", "remove"),
    ("A26", "A", IPC, "With no correction needed, the decline is significant.", "remove"),
    ("A27", "A", IPC, "Nine observations over the look-back window, from March 2022 to September 2026, enter the test.", "keep"),
    ("A28", "A", IPC, "The decline is not only visible on the chart but statistically significant.", "remove"),
    ("A29", "A", IPC, "As a single test, its p-value of 0.059 is not adjusted, and the decline is not statistically significant at α=0.05.", "keep"),
    ("A30", "A", DC, "The chosen period holds one observation for each series, so the values and trends cover the look-back window from 19 November 2021 to 19 November 2026.", "keep"),
    ("A31", "A", DC, "IPC analyses covered different parts of the country in different periods (analysed population 41.4 to 49.7 million), so the share is used rather than the number of people.", "keep"),
    ("M1", "A", M, "The trend was tested with the Mann-Kendall test, its slope estimated as Sen's slope per year, and Kendall's tau used as the effect size.", "keep"),
    ("M2", "A", M, "Only one statistical test was run, so no multiple-comparison correction applies; significance is decided on its p-value at α=0.05.", "keep"),
    ("M3", "A", M, "Because only one test was run, no Holm correction was applied.", "keep"),
    ("M4", "A", M, "Regional differences were tested with the Kruskal-Wallis test.", "remove"),
    ("M5", "A", M, "Correlations between indicators were measured with Pearson's coefficient.", "remove"),
    ("M6", "A", M, "The tests assume independent observations and serial correlation is not corrected for, so the results are indicative.", "keep"),
    ("M7", "A", M, "A Holm correction was applied across all tests in this report.", "remove"),
    ("M8", "A", M, "No multiple-comparison correction such as Holm's was needed, since a single test was run.", "keep"),
    ("M9", "A", "Methodology", "Regional differences were tested with the Kruskal-Wallis test.", "remove"),
    ("M10", "A", "Methods Note", "Regional differences were tested with the Kruskal-Wallis test.", "remove"),
    ("M11", "A", "Methods", "Data were retrieved from HDX HAPI; significance is decided at α=0.05.", "keep"),
    # --- AFG Protection, EN ---
    ("P1", "P", ES, "Protection: people in need stood at 15.0 million people in 2026; earlier years are reported on a different basis and are not comparable.", "keep"),
    ("P2", "P", ES, "Protection: people in need rose to 15.0 million people in 2026 from 14.2 million in 2025.", "remove"),
    ("P3", "P", ES, "Protection: people in need rose to 15.0 million people in 2026, up from 2025.", "remove"),
    ("P3b", "P", ES, "Protection needs increased to 15.0 million people in 2026.", "remove"),
    ("P3c", "P", ES, "Protection needs grew to 15.0 million people in 2026, the highest level since 2024.", "remove"),
    ("P4", "P", ES, "In 2026, 15.0 million people needed protection assistance, although the figures for earlier years are not comparable.", "keep"),
    ("P5", "P", ES, "For protection needs, refugees, returnees and internally displaced people the chosen period holds too few observations, so their values and trends cover a look-back window from 19 November 2021 to 19 November 2026.", "keep"),
    ("P6", "P", ES, "Refugees numbered 2.67 million in 2025, before the chosen period, against 5.66 million in 2022; the decreasing trend is not statistically significant (p=0.734, Holm-adjusted p=0.734).", "keep"),
    ("P7", "P", ES, "Refugees fell to 2.67 million in 2026.", "remove"),
    ("P8", "P", ES, "None of the tested trends is statistically significant.", "keep"),
    ("P8b", "P", ES, "Neither of the two tested trends is statistically significant after the Holm correction.", "keep"),
    ("P9", "P", PRO, "Protection: people in need was 15.0 million people in 2026; the earlier figures were 14.2 million people in 2025 and 14.8 million people in 2024, but the values are not comparable across years.", "keep"),
    ("P10", "P", PRO, "Protection needs rose from 14.2 million in 2025 to 15.0 million in 2026.", "remove"),
    ("P11", "P", PRO, "The values cover the look-back window; with three observations that are not comparable across years, no trend is tested.", "keep"),
    ("P12", "P", PRO, "Protection needs were higher in 2026 than in 2025.", "remove"),
    ("P13", "P", REF, "Refugees (people) numbered 2.67 million people in 2025, before the chosen period, against 5.66 million people in 2022.", "keep"),
    ("P14", "P", REF, "The decreasing trend over the look-back window (Sen slope -817,000 people per year) is not statistically significant (p=0.734, Holm-adjusted p=0.734).", "keep"),
    ("P15", "P", REF, "The relative change along the trend line was -38.1%.", "keep"),
    ("P16", "P", REF, "Refugees fell by 38.1%, a significant decline.", "remove"),
    ("P17", "P", REF, "Refugees fell by 53% between 2022 and 2025.", "remove"),
    ("P18", "P", REF, "Refugee numbers roughly halved between 2022 and 2025.", "keep"),
    ("P19", "P", RET, "Returnees rose from 6,510 people in 2022 to 1.95 million people in 2025, before the chosen period.", "keep"),
    ("P20", "P", RET, "The increasing trend, with a Sen slope of 477,000 people per year, is not statistically significant (p=0.089; Holm-adjusted p=0.179).", "keep"),
    ("P21", "P", RET, "Returnee numbers did not fall; the increase is statistically significant.", "remove"),
    ("P22", "P", RET, "Returnees rose to 1.95 million people in 2025, a significant increase (p=0.089).", "remove"),
    ("P23", "P", IDP, "Internally displaced people (IDPs) numbered 3.06 million people in January 2026, down from 3.11 million people in May 2025; there were 2.97 million in January 2025.", "keep"),
    ("P24", "P", IDP, "IDPs numbered 3.06 million people in March 2026.", "remove"),
    ("P25", "P", IDPR, "Herat (443,000 people), Balkh (363,000 people) and Kabul (310,000 people) hosted the most IDPs as of January 2026; a statistical comparison between regions was not possible because each region has one observation.", "keep"),
    ("P26", "P", IDPR, "Herat hosted significantly more IDPs than other regions.", "remove"),
    ("P27", "P", M, "The two trend tests were adjusted together with the Holm correction, and significance is decided on the Holm-adjusted p-value at α=0.05.", "keep"),
    ("P28", "P", M, "Regional differences were assessed with the Kruskal-Wallis test.", "remove"),
    ("P29", "P", DC, "The plan reports protection in separate lines; the 2025 figure (14,213,777) may be another of these lines rather than the overall protection figure, and the lines are not added up.", "keep"),
    ("P30", "P", DC, "In 2025 the plan's Gender Based Violence line was 14.2 million people.", "keep"),
    # --- AFG All sectors, 1 year, EN ---
    ("L1", "L", ES, "None of the four trends tested was statistically significant after the Holm correction.", "keep"),
    ("L2", "L", ES, "No trend was statistically significant.", "keep"),
    ("L3", "L", FUN, "Humanitarian funding (USD) fell to 1.16 billion USD in 2025, before the chosen period, from 3.82 billion USD in 2022.", "keep"),
    ("L4", "L", FUN, "Humanitarian funding fell by 70% between 2022 and 2025.", "remove"),
    ("L5", "L", FUN, "Funding fell by about two-thirds between 2022 and 2025.", "keep"),
    ("L6", "L", FUN, "The decreasing trend (Sen slope -717 million USD per year) is not statistically significant (p=0.089, Holm-adjusted p=0.268).", "keep"),
    ("L7", "L", ES, "Funding declined significantly.", "remove"),
    ("L8", "L", ES, "The share of the analysed population in IPC Phase 3 or above was 32.0% in September 2026, with a decreasing trend that was not statistically significant (p=0.059; Holm-adjusted p=0.237).", "keep"),
    ("L9", "L", M, "Trends were tested with the Mann-Kendall test and Sen's slope; the Holm correction was applied across all four tests, with significance decided at α=0.05.", "keep"),
    ("L10", "L", M, "Correlations between indicators were measured with Pearson's r.", "remove"),
    ("L11", "L", ES, "Funding fell to 1.16 billion USD in 2026.", "remove"),
    # --- Haiti Protection 2025 (significant verdicts) ---
    ("H1", "H", HREF, "Although not large, the increase is statistically significant (p=0.027).", "keep"),
    ("H2", "H", HIDP, "The increasing trend in IDPs is statistically significant (p=0.009, Holm-adjusted p=0.017).", "keep"),
    ("H3", "H", HREF, "The increase in refugees is not statistically significant.", "remove"),
    ("H4", "H", HREG, "The difference between regions is not just visible but statistically significant (p=0.001).", "keep"),
    ("H5", "H", ES, "Protection: people in need was 467,000 people in 2025; it is not the plan's overall protection figure, and earlier years are reported on a different basis and are not comparable.", "keep"),
    ("H6", "H", HIDP, "Even with no correction for serial correlation, the rise is significant.", "keep"),
    ("H7", "H", ES, "Protection needs nearly doubled from 250,000 people in 2024 to 467,000 people in 2025.", "remove"),
    ("H8", "H", ES, "The number of refugees from Haiti rose significantly, to 181,000 in 2025 (p=0.027).", "keep"),
    ("F1", "F", HREG, "Regional differences in IDP numbers are statistically significant (Kruskal-Wallis H=100.08, p<0.001, Holm-adjusted p<0.001).", "keep"),
    ("F2", "F", M, "Regions were compared with the Kruskal-Wallis test, and the Holm correction was applied across all five tests.", "keep"),
    ("F3", "F", M, "Correlations were computed with Pearson's coefficient.", "remove"),
    # --- Turkish ---
    ("T1", "AT", ESTR, "Afganistan'da 2026'da 17,4 milyon kişi gıda güvenliği yardımına, 7,46 milyon kişi beslenme yardımına ihtiyaç duyuyordu.", "keep"),
    ("T2", "AT", ESTR, "Rapor 19 Kasım 2025 ile 19 Kasım 2026 arasını kapsamaktadır.", "keep"),
    ("T3", "AT", ESTR, "Seçilen dönemde yeterli gözlem olmadığından değerler ve eğilimler 19 Kasım 2021 – 19 Kasım 2026 geriye bakış penceresini kapsar.", "keep"),
    ("T4", "AT", ESTR, "2026'da 17,9 milyon kişi gıda güvenliği yardımına ihtiyaç duyuyordu.", "remove"),
    ("T5", "AT", ESTR, "Analiz edilen nüfusun IPC 3+ evresindeki payı Eylül 2026'da %32,0 oldu; bu oran Mart 2022'de %47,0 idi.", "keep"),
    ("T6", "AT", FST, "Gıda güvenliği: insani yardıma ihtiyaç duyan kişiler 2026'da 17,4 milyon kişiye ulaştı; bu sayı 2025'te 14,8 milyon, 2024'te 15,8 milyon kişiydi.", "keep"),
    ("T7", "AT", FST, "Üç gözlem eğilim testi için yetersizdir.", "keep"),
    ("T8", "AT", IPCT, "Eğilim çizgisi boyunca değişim -21,0 yüzde puandır; düşüş istatistiksel olarak anlamlı değildir (p=0,059).", "keep"),
    ("T9", "AT", IPCT, "Düşüş istatistiksel olarak anlamlıdır (p=0,059).", "remove"),
    ("T10", "AT", IPCT, "IPC 3+ payı %32 azaldı.", "remove"),
    ("T11", "AT", IPCT, "IPC 3+ payı Mart 2022'deki %47,0'dan Eylül 2026'da %32,0'a geriledi.", "keep"),
    ("T12", "AT", NUT, "Beslenme ihtiyacı 2026'da 7,46 milyon kişiyle 2025'teki 7,80 milyon kişinin altına indi.", "keep"),
    ("T13", "AT", "Yöntem", "Bölgesel farklılıklar Kruskal-Wallis testiyle incelendi.", "remove"),
    ("T14", "AT", "Yöntem", "Yalnızca bir test yapıldığı için Holm düzeltmesi uygulanmadı.", "keep"),
    ("T15", "AT", "Yöntem", "Eğilim Mann-Kendall testiyle sınandı, eğim Sen eğimiyle hesaplandı; Kendall tau etki büyüklüğüdür.", "keep"),
    ("T16", "AT", "Yöntem Notu", "Bölgesel farklılıklar Kruskal-Wallis testiyle incelendi.", "remove"),
    ("T17", "AT", "Metodoloji", "Göstergeler arasındaki ilişki Pearson korelasyonuyla ölçüldü.", "remove"),
    ("T18", "AT", FST, "Gıda güvenliği ihtiyacı 2026'da 17,9 milyon kişiye ulaştı.", "remove"),
    ("T19", "AT", IPCT, "IPC 3+ payı Eylül 2026'da %33,0 oldu.", "remove"),
    ("T20", "AT", IPCT, "Düşüş eğilimi istatistiksel olarak anlamlı bulunmadı.", "keep"),
    ("T21", "AT", IPCT, "Kesin olmasa da düşüş anlamlıdır.", "remove"),
    ("T22", "AT", IPCT, "IPC 3+ payı eğilim çizgisi boyunca 21,0 yüzde puan azaldı.", "keep"),
    ("T23", "AT", IPCT, "IPC 3+ payı eğilim çizgisi boyunca 21,0 yüzde puan arttı.", "remove"),
    ("T24", "AT", IPCT, "Seçilen dönem tek gözlem içerdiğinden değerler geriye bakış penceresini kapsar.", "keep"),
    ("T25", "AT", "Yöntem", "Tek bir istatistiksel test yapıldığından çoklu karşılaştırma düzeltmesi uygulanmadı; anlamlılık α=0,05 düzeyinde p değerine göre belirlendi.", "keep"),
    ("T26", "PT", ESTR, "Koruma ihtiyacı 2026'da 15,0 milyon kişiydi; önceki yıllar farklı bir temelde raporlandığından karşılaştırılamaz.", "keep"),
    ("T27", "PT", ESTR, "Koruma ihtiyacı 2025'ten bu yana artarak 2026'da 15,0 milyon kişiye ulaştı.", "remove"),
    ("T28", "PT", ESTR, "Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyona yükseldi.", "remove"),
    ("T29", "PT", PROT, "Koruma: insani yardıma ihtiyaç duyan kişiler 2026'da 15,0 milyon, 2025'te 14,2 milyon ve 2024'te 14,8 milyon kişiydi; ancak bu değerler yıllar arasında karşılaştırılabilir değildir.", "keep"),
    ("T30", "PT", PROT, "Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyona yükseldi.", "remove"),
    ("T31", "PT", IDPT, "Ülke içinde yerinden edilmiş kişiler Ocak 2026'da 3,06 milyon kişiydi; Mayıs 2025'te 3,11 milyon kişiydi.", "keep"),
    ("T32", "PT", ESTR, "Hiçbir eğilim istatistiksel olarak anlamlı değildir.", "keep"),
    ("T33", "PT", ESTR, "Mülteci sayısı 2025'te 2,67 milyon kişiye geriledi; bu değer seçilen dönemden öncedir.", "keep"),
    ("T34", "PT", ESTR, "Mülteci sayısı 2025'te 2,76 milyon kişiydi.", "remove"),
]

# extra.py: Methods rule with the previous report attached (a "Run next period" report),
# and the natural ways of saying the years are not comparable.
_PREVIOUS = ("\n\nCOMPARISON WITH THE PREVIOUS REPORT. ... previous report:\n## Methods\n\nTrends were "
             "tested with Mann-Kendall; regions with Kruskal-Wallis; correlations with Pearson; Holm "
             "correction across all 1 tests.")
EXTRA = [
    ("X1", "A", M, "Regional differences were tested with the Kruskal-Wallis test, and the Holm correction was applied.", "remove", ""),
    ("X2", "A", M, "Regional differences were tested with the Kruskal-Wallis test, and the Holm correction was applied.", "remove", _PREVIOUS),
    ("X3", "P", PRO, "The 2026 figure should not be read as an increase, because earlier years are reported on a different basis.", "keep", ""),
    ("X4", "P", PRO, "Because earlier years are reported on a different basis, no rise or fall between them can be stated.", "keep", ""),
    ("X5", "P", PRO, "Earlier figures cannot be compared with 2026, so no increase is reported.", "keep", ""),
    ("X6", "P", ES, "Protection needs stood at 15.0 million people in 2026, a figure that cannot be compared with earlier years.", "keep", ""),
    ("X7", "P", ESTR, "Koruma ihtiyacı 2026'da 15,0 milyon kişiydi; önceki yıllarla karşılaştırılması mümkün değildir.", "keep", ""),
    ("X8", "P", PRO, "2026 rakamı önceki yıllarla karşılaştırılamadığından bir artış olarak yorumlanmamalıdır.", "keep", ""),
    # extra2.py: one or two values of the not-comparable series narrated as a change
    ("Y1", "P", ES, "Protection needs rose from 14.8 to 15.0 million people between 2024 and 2026.", "remove", ""),
    ("Y2", "P", ES, "Protection needs rose from 14.2 million in 2025 to 15.0 million in 2026.", "remove", ""),
    ("Y3", "P", ES, "Protection needs reached 15.0 million people in 2026, up from 14.2 million.", "remove", ""),
    ("Y4", "P", ES, "Protection needs climbed to 15.0 million people in 2026 after 14.2 million in 2025.", "remove", ""),
]


@pytest.mark.parametrize("sid,key,section,sentence,expect", S)
def test_reviewer_round3_corpus(sid, key, section, sentence, expect):
    f, allowed, lang = CTX[key]
    res = verify_narrative(f"## {section}\n\n{sentence}\n", f, allowed, lang, label=f"review/{sid}")
    assert ("remove" if res.removed else "keep") == expect, sid


@pytest.mark.parametrize("sid,key,section,sentence,expect,extra", EXTRA)
def test_reviewer_round3_extras(sid, key, section, sentence, expect, extra):
    f, allowed, lang = CTX[key]
    res = verify_narrative(f"## {section}\n\n{sentence}", f, allowed + extra, lang)
    assert ("remove" if res.removed else "keep") == expect, sid
