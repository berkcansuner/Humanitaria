"""The final reviewer's sentence corpus (round 2, last pass): sent_test.py, batch2.py,
batch3.py and batch4.py, run on the six finding sets it used (AFG Food and Nutrition and
Protection 2025-11-18 to 2026-11-18, HTI Protection 2025; English and Turkish), rebuilt
from live HDX HAPI rows on 2026-11-19. K: a correct sentence that must survive; R: a wrong
claim that must be removed."""
import json
from pathlib import Path

import pytest

from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

_DATA = json.loads((Path(__file__).parent / "review_sets_2026-11-19.json").read_text(encoding="utf-8"))
SETS = {k: {"context": v["context"], "findings": Findings(
    sections=[ReportSection(s["heading"], s["stat_result"], None, "") for s in v["sections"]],
    gaps=[], indicators_covered=[])} for k, v in _DATA.items()}

FE, FT, PE, PT, HE, HT = ("afgfood_recent_en", "afgfood_recent_tr", "afgprot_recent_en",
                          "afgprot_recent_tr", "hti2025_en", "hti2025_tr")
K, R = True, False


def heading(key, sel):
    if sel == "EXEC":
        return "Executive Summary" if key.endswith("en") else "Yönetici Özeti"
    if sel == "DATA":
        return "Data Coverage & Limitations" if key.endswith("en") else "Veri Kapsamı ve Sınırlılıklar"
    pref = {"IPC": ("Food insecurity", "Gıda güvensizliği"),
            "FSC": ("Food security", "Gıda güvenliği"),
            "NUT": ("Nutrition", "Beslenme"),
            "PRO": ("Protection", "Koruma"),
            "REF": ("Refugees", "Mülteciler"),
            "RET": ("Returnees", "Geri dönenler")}[sel]
    return next(s.heading for s in SETS[key]["findings"].sections if s.heading.startswith(pref))


CASES = [

    # --- English, IPC share
    (FE, "IPC", "In September 2026, 32.0% of the analysed population was in IPC Phase 3 or above.", K),
    (FE, "IPC", "The share was 47.0% in March 2022.", K),
    (FE, "IPC", "Along the trend line the share fell by 21.0 percentage points between March 2022 and September 2026.", K),
    (FE, "IPC", "The Sen slope is -4.65 percentage points per year.", K),
    (FE, "IPC", "Food insecurity has been decreasing by 4.65 percentage points per year.", K),
    (FE, "IPC", "At 32.0%, the share remains at a higher level than partners consider acceptable.", K),
    (FE, "IPC", "The lower bound of the 95% confidence interval is -7.99 percentage points per year.", K),
    (FE, "IPC", "The decline of 21.0 percentage points along the trend line is not statistically significant (Holm-adjusted p=0.059).", K),
    (FE, "IPC", "Fellow partners report that 32.0% of the analysed population remained in crisis or worse.", K),
    (FE, "IPC", "Partners are increasingly concerned that 32.0% of the analysed population is in crisis or worse.", K),
    (FE, "IPC", "Food insecurity stood at 32.0% in September 2026 against 47.0% in March 2022, so a rose-coloured reading would be premature.", K),
    (FE, "IPC", "Food insecurity declined by around 32% from 2022 to 2026.", R),
    (FE, "IPC", "Food insecurity rose by 4.65 percentage points per year.", R),
    (FE, "IPC", "Food insecurity was halved between March 2022 and September 2026.", R),
    (FE, "IPC", "Food insecurity dropped to roughly half of its March 2022 level.", R),
    (FE, "IPC", "Food insecurity fell 21.0 percentage points, a 32% improvement.", R),
    (FE, "IPC", "Food insecurity fell by 21.0 percent.", R),
    (FE, "IPC", "The share went down by about a third.", R),
    (FE, "IPC", "Food insecurity was 21.0 percentage points higher in 2026 than in 2022.", R),
    (FE, "NUT", "Nutrition needs rose from 7.4 million in 2024 to 7.8 million in 2025 before easing to 7.46 million in 2026.", K),
    (FE, "FSC", "Food security needs fell from 15.8 million in 2024 to 14.8 million in 2025, then rose to 17.4 million in 2026.", K),
    (FE, "EXEC", "Food insecurity fell by 21.0 percentage points along the trend line, a change that is not statistically significant.", K),
    (FE, "EXEC", "Food insecurity fell by 32% between 2022 and 2026.", R),
    # --- English, AFG protection (not comparable) and counts
    (PE, "PRO", "The plan's figure was 14.8 million people in 2024, 14.2 million in 2025 and 15.0 million in 2026.", K),
    (PE, "PRO", "These values are not comparable across years, so no trend is reported.", K),
    (PE, "PRO", "In 2026 the figure, 15.0 million people, is the plan's only protection figure.", K),
    (PE, "PRO", "The 2024 and 2025 figures may be one of the plan's separate protection lines, so the overall protection figure may be higher than this line.", K),
    (PE, "PRO", "The overall protection figure for 2025 is not in HDX HAPI and may be higher.", K),
    (PE, "PRO", "The figure for 2025 is 14.2 million people; HDX HAPI does not say which of the plan's lines it is.", K),
    (PE, "PRO", "Because the plan reports child protection, gender-based violence, housing, land and property, and mine action separately, the figures for 2024 and 2025 may not be the protection total.", K),
    (PE, "PRO", "Mine action, one of the separate lines, covered 4.37 million people in 2025.", K),
    (PE, "PRO", "Partners are increasingly concerned about the 15.0 million people in need of protection in 2026.", K),
    (PE, "PRO", "In 2026 the plan reported a single protection figure of 15.0 million, with no separate lines.", K),
    (PE, "PRO", "Up to 15.0 million people needed protection services in 2026.", K),
    (PE, "PRO", "The 2026 figure is higher than the 2025 figure, but the two years are not comparable.", K),
    (PE, "PRO", "Protection needs increased from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "PRO", "Needs dropped between 2024 and 2025, from 14.8 million to 14.2 million.", R),
    (PE, "PRO", "The number of people in need of protection was lower in 2025 (14.2 million) than in 2024 (14.8 million).", R),
    (PE, "PRO", "Protection needs went from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "PRO", "There was a rise from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "PRO", "Protection needs remained broadly stable at around 14 to 15 million people from 2024 to 2026.", R),
    (PE, "PRO", "Protection needs grew between 2025 and 2026.", R),
    (PE, "EXEC", "Protection needs rose from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "DATA", "Protection needs rose from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "DATA", "The overall protection figure may be higher than this line.", K),
    (PE, "REF", "Refugees fell from 5.66 million in 2022 to 2.67 million in 2025.", K),
    (PE, "REF", "The number of refugees roughly halved between 2022 and 2025.", K),
    (PE, "REF", "Refugees rose by 38.1% along the trend line.", R),
    (PE, "REF", "Refugees declined by about two-thirds.", R),
    (PE, "RET", "Returnees rose from 6,510 people in 2022 to 1.95 million in 2025.", K),
    (PE, "RET", "Returnees increased by 38.1%.", R),
    # --- English, HTI protection (not comparable)
    (HE, "PRO", "The values are 250,000 people in 2024 and 467,000 people in 2025, but the years are not comparable.", K),
    (HE, "PRO", "In 2025 the figure was 466,589 people.", K),
    (HE, "PRO", "HDX HAPI holds two totals for 2025: 349,999 without a breakdown and 466,589 as the total of its breakdown.", K),
    (HE, "PRO", "Both figures are below the child protection line, so neither is the plan's overall protection figure.", K),
    (HE, "PRO", "The 2025 figure of 467,000 is lower than the child protection line of 1.61 million, so it is not the plan's overall figure.", K),
    (HE, "PRO", "The figure rose to 467,000 in 2025.", R),
    (HE, "PRO", "Protection needs nearly doubled from 250,000 in 2024 to 467,000 in 2025.", R),
    (HE, "PRO", "Protection needs in 2025 (467,000) were almost twice those of 2024 (250,000).", R),
    # --- Turkish, IPC share
    (FT, "IPC", "Eylül 2026'da analiz edilen nüfusun %32,0'ı IPC Aşama 3 veya üzerindeydi.", K),
    (FT, "IPC", "Gıda güvensizliği oranı Mart 2022'de %47,0 idi.", K),
    (FT, "IPC", "Oran, eğilim çizgisi boyunca 21,0 yüzde puan gerilemiştir.", K),
    (FT, "IPC", "Gıda güvensizliği yılda 4,65 yüzde puan azalmaktadır.", K),
    (FT, "IPC", "Gıda güvensizliği %32,0'a inmiştir.", K),
    (FT, "IPC", "Gıda güvensizliği %47,0'dan %32,0'a gerilemiştir.", K),
    (FT, "IPC", "İnsani yardım ortakları için %32,0 hâlâ büyük bir oran ve artık kabul edilebilir düzeyin üzerinde.", K),
    (FT, "IPC", "Azami değer Mart 2022'deki %47,0 oldu; en düşük değer ise Eylül 2026'daki %32,0.", K),
    (FT, "IPC", "Bu düşünce, %32,0 oranının yüksekliği nedeniyle önem taşıyor.", K),
    (FT, "IPC", "Analiz edilen nüfusun %32,0'ı kriz düzeyinde; gerilim ve çatışma ortamı sürüyor.", K),
    (FT, "IPC", "İnanç toplulukları da %32,0 düzeyindeki gıda güvensizliğinden etkileniyor.", K),
    (FT, "IPC", "Gıda güvensizliğindeki gerileme, Eylül 2026'da %32,0 düzeyine ulaştı.", K),
    (FT, "IPC", "Gıda güvensizliğinin 21,0 yüzde puan azalması istatistiksel olarak anlamlı değildir.", K),
    (FT, "IPC", "Gıda güvensizliği %32 oranında azalmıştır.", R),
    (FT, "IPC", "Gıda güvensizliği yüzde 32 gerilemiştir.", R),
    (FT, "IPC", "Gıda güvensizliği yüzde 32 düşmekte.", R),
    (FT, "IPC", "Gıda güvensizliği %32 düşüyor.", R),
    (FT, "IPC", "Gıda güvensizliğinin %32 azalması dikkat çekicidir.", R),
    (FT, "IPC", "Gıda güvensizliğinin %32 düştüğü görülmektedir.", R),
    (FT, "IPC", "Gıda güvensizliği yarı yarıya azalmıştır.", R),
    (FT, "IPC", "Oran 2022'deki düzeyinin yarısına inmiştir.", R),
    (FT, "IPC", "Gıda güvensizliği 21,0 yüzde puan yükselmektedir.", R),
    (FT, "IPC", "Gıda güvensizliği 21,0 yüzde puanlık bir artış göstermiştir.", R),
    (FT, "IPC", "Gıda güvensizliğinin yılda 4,65 yüzde puan arttığı görülüyor.", R),
    # --- Turkish, counts with suffixed scale words
    (FT, "FSC", "Gıda güvenliği alanında ihtiyaç duyan kişi sayısı 2025'teki 14,8 milyondan 2026'da 17,4 milyona çıkmıştır.", K),
    (FT, "FSC", "İhtiyaç duyan kişi sayısı 2024'te 15,8 milyon iken 2026'da 17,4 milyona yükselmiştir.", K),
    (FT, "NUT", "Beslenme alanında ihtiyaç 2025'teki 7,8 milyondan 2026'da 7,46 milyona inmiştir.", K),
    (FT, "NUT", "Beslenme alanında 7,46 milyonluk bir ihtiyaç bulunuyor.", K),
    # --- Turkish, AFG protection (not comparable)
    (PT, "PRO", "Koruma alanında insani yardıma ihtiyaç duyan kişi sayısı 2024'te 14,8 milyon, 2025'te 14,2 milyon, 2026'da 15,0 milyondu.", K),
    (PT, "PRO", "Bu yıllara ait değerler karşılaştırılamaz; bu nedenle trend testi yapılmamıştır.", K),
    (PT, "PRO", "Planın genel koruma rakamı bu satırdan daha yüksek olabilir.", K),
    (PT, "PRO", "2024 ve 2025 rakamları planın ayrı koruma satırlarından biri olabilir; 2026 rakamı ise planın tek koruma rakamıdır.", K),
    (PT, "PRO", "İnsani yardım ortakları 2026'da 15,0 milyon kişinin korumaya ihtiyaç duyduğunu bildiriyor.", K),
    (PT, "PRO", "Koruma ihtiyacının 2025'te 14,2 milyon olarak raporlandığı, 2026'da ise 15,0 milyon olduğu görülmektedir.", K),
    (PT, "PRO", "Bu rakamlar ortaya çıkan ihtiyacın büyüklüğünü gösteriyor: 2026'da 15,0 milyon kişi.", K),
    (PT, "PRO", "Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyona yükselmekle birlikte yıllar karşılaştırılamaz.", K),
    (PT, "PRO", "Koruma ihtiyacı 2025'ten 2026'ya artmıştır.", R),
    (PT, "PRO", "Koruma ihtiyacı 14,2 milyondan 15,0 milyona çıkmıştır.", R),
    (PT, "PRO", "Koruma ihtiyacında 2026'da bir artış görülmüştür.", R),
    (PT, "PRO", "Koruma ihtiyacı 2024'teki 14,8 milyondan 2025'te 14,2 milyona gerilemektedir.", R),
    (PT, "PRO", "Koruma ihtiyacı 2025'e göre 2026'da daha fazlaydı.", R),
    (PT, "EXEC", "Koruma ihtiyacı 2025'teki 14,2 milyondan 2026'da 15,0 milyona yükseldi.", R),
    # --- Turkish, HTI protection (not comparable)
    (HT, "PRO", "Koruma ihtiyacı 2024'teki 250.000 kişiden 2025'te 467.000 kişiye neredeyse iki katına çıkmıştır.", R),
    (HT, "PRO", "2024'te 250.000, 2025'te 467.000 kişi koruma ihtiyacı içindeydi; iki yıl karşılaştırılamaz.", K),
    (HT, "PRO", "2025 rakamı (466.589) çocuk koruma satırının altında olduğu için planın genel koruma rakamı değildir.", K),
    # batch2.py

    (PE, "PRO", "A rose-coloured reading of the 15.0 million people in need in 2026 would be misleading.", K),
    (PE, "PRO", "Fellow agencies report 15.0 million people in need of protection in 2026.", K),
    (PE, "PRO", "At a higher level of detail, the plan reports child protection and gender-based violence separately.", K),
    (PE, "PRO", "The lower bound of the 2026 estimate is not published; the figure is 15.0 million.", K),
    (PE, "PRO", "The 2025 figure, 14.2 million, may be one of the plan's separate protection lines rather than its overall figure.", K),
    (PE, "PRO", "The overall protection total is likely higher than 14.2 million for 2025.", K),
    (PE, "PRO", "Climate change and conflict drive the protection needs of 15.0 million people in 2026.", K),
    (HE, "PRO", "The 2025 figure is below the child protection line of 1.61 million, so the overall protection figure is higher.", K),
    (PT, "PRO", "Koruma ihtiyacı 2026'da 15,0 milyon kişiyle büyük ve artık göz ardı edilemeyecek düzeydedir.", K),
    (PT, "PRO", "İnsani durum ağırdır; 2026'da 15,0 milyon kişi korumaya ihtiyaç duymaktadır.", K),
    (PT, "PRO", "Gerilim ve azami belirsizlik ortamında 2026 rakamı 15,0 milyondur.", K),
    (PT, "PRO", "Düşük tahminlere göre bile 2026'da 15,0 milyon kişi ihtiyaç içindeydi.", K),
    (PT, "PRO", "İnanç önderleri 2026'da 15,0 milyon kişinin korumaya ihtiyaç duyduğunu vurguluyor.", K),
    (PT, "PRO", "2025 rakamı (14,2 milyon) planın genel koruma rakamından düşük olabilir.", K),
    (PT, "PRO", "Bu düşünceyle, 2026 rakamı olan 15,0 milyon tek koruma rakamı olarak okunmalıdır.", K),
    (PT, "PRO", "Koruma ihtiyacı 2025'ten 2026'ya artmaktadır.", R),
    (PT, "PRO", "Koruma ihtiyacı 2025'ten 2026'ya artmakta.", R),
    (PT, "PRO", "Koruma ihtiyacı 2025'ten 2026'ya artıyor.", R),
    (PT, "PRO", "Koruma ihtiyacının 2026'da arttığı görülmektedir.", R),
    (PT, "PRO", "Koruma ihtiyacının 2025'te azalması dikkat çekicidir.", R),
    (PT, "PRO", "Koruma ihtiyacı 2024'ten 2025'e düşmüştür.", R),
    (HT, "PRO", "Koruma ihtiyacı 2024'te 250.000 iken 2025'te 467.000'e yükselmiştir.", R),
    (HT, "PRO", "Koruma ihtiyacı 2024'ten 2025'e neredeyse iki katına çıktı.", R),
    (HE, "PRO", "Protection needs rose by 86.8% from 2024 to 2025.", R),
    # batch3.py: changes between non-comparable years, all to be removed
    (PE, "PRO", "There was a fall from 14.8 million in 2024 to 14.2 million in 2025.", R),
    (PE, "PRO", "There was a drop from 14.8 million in 2024 to 14.2 million in 2025.", R),
    (PE, "PRO", "There was an increase from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "PRO", "There was a decrease from 14.8 million in 2024 to 14.2 million in 2025.", R),
    (PE, "PRO", "Protection needs reached 15.0 million in 2026, after 14.2 million in 2025.", R),
    (PE, "PRO", "Protection needs climbed from 14.2 million in 2025 to 15.0 million in 2026.", R),
    (PE, "PRO", "Protection needs tripled.", R),
    (PE, "PRO", "Protection needs were greater in 2026 (15.0 million) than in 2025 (14.2 million).", R),
    # batch4.py: roundings of the notes' full figures, all to be kept
    (HE, "DATA", "HDX HAPI also holds a second total of about 350,000 people for 2025.", K),
    (HE, "DATA", "HDX HAPI also holds a second total of 349,999 people for 2025.", K),
    (HE, "DATA", "HDX HAPI also holds a second total of about 0.35 million people for 2025.", K),
    (HE, "DATA", "In 2025 the plan lists child protection at 1,611,000 people.", K),
    (HE, "DATA", "In 2025 the plan lists child protection at 1.61 million people.", K),
    (PE, "DATA", "In 2025 gender-based violence covered 14,170,000 people.", K),
    (HT, "DATA", "HDX HAPI 2025 için ikinci bir toplam olarak yaklaşık 350 bin kişi veriyor.", K),
]


@pytest.mark.parametrize("key,sel,sentence,keep", CASES)
def test_final_reviewer_corpus(key, sel, sentence, keep):
    lang = "tr" if key.endswith("tr") else "en"
    res = verify_narrative(f"## {heading(key, sel)}\n\n{sentence}", SETS[key]["findings"],
                           SETS[key]["context"], lang)
    assert (res.removed == 0) == keep


# --- Round 3: the same corpus on the reader-form contexts, rebuilt from live HDX HAPI. ---

_DATA_R3 = json.loads((Path(__file__).parent / "review_sets_r3.json").read_text(encoding="utf-8"))
SETS_R3 = {k: {"context": v["context"], "findings": Findings(
    sections=[ReportSection(s["heading"], s["stat_result"], None, "") for s in v["sections"]],
    gaps=[], indicators_covered=[])} for k, v in _DATA_R3.items()}


@pytest.mark.parametrize("key,sel,sentence,keep", CASES)
def test_final_reviewer_corpus_on_the_round3_context(key, sel, sentence, keep):
    lang = "tr" if key.endswith("tr") else "en"
    res = verify_narrative(f"## {heading(key, sel)}\n\n{sentence}", SETS_R3[key]["findings"],
                           SETS_R3[key]["context"], lang)
    assert (res.removed == 0) == keep
