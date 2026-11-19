"""The technical report's facts are sentences written in code, in English or Turkish."""
from analytics import report_text
from tests.analytics import samples


def test_a_trend_section_states_values_direction_test_and_verdict():
    f = samples.findings(samples.trend(), samples.share_trend())
    text = report_text.section_facts(f.sections[0].stat_result, "en")
    assert text == (
        "The latest value is 2.67 million people (2025); the first value in the window is 5.66 "
        "million people (2022). From 2022 to 2025, the trend is decreasing: Sen's slope is "
        "-817,000 people per year (95% confidence interval: too few points to compute), and "
        "Kendall's tau is -0.33. The Mann-Kendall test gives p=0.734 (Holm-adjusted p=0.734), so "
        "the trend is not statistically significant at the 0.05 level. The relative change along the "
        "trend line is -38.1%. The series has four observations.")


def test_the_same_trend_in_turkish_uses_turkish_figures_and_no_case_suffix_on_them():
    f = samples.findings(samples.trend(), samples.share_trend())
    text = report_text.section_facts(f.sections[0].stat_result, "tr")
    assert text == (
        "Son değer 2,67 milyon kişi (2025); penceredeki ilk değer 5,66 milyon kişi (2022). "
        "2022 – 2025 arasında eğilim azalış yönünde: Sen eğimi yılda -817.000 kişi (%95 güven "
        "aralığı: hesaplamak için nokta sayısı yetersiz), Kendall tau -0,33. Mann-Kendall testi "
        "p=0,734 veriyor (Holm düzeltmeli p=0,734); eğilim 0,05 düzeyinde istatistiksel olarak "
        "anlamlı değil. Eğilim çizgisi boyunca göreli değişim -%38,1. Seride dört gözlem var.")


def test_a_share_changes_in_percentage_points_in_both_languages():
    f = samples.findings(samples.share_trend())
    en = report_text.section_facts(f.sections[0].stat_result, "en")
    tr = report_text.section_facts(f.sections[0].stat_result, "tr")
    assert "32.0% (September 2026)" in en and "-4.65 percentage points per year" in en
    assert "(95% confidence interval: -7.99 percentage points to 0 percentage points)" in en
    assert "The change along the trend line is -21.0 percentage points." in en
    assert "%32,0 (Eylül 2026)" in tr and "yılda -4,65 yüzde puan" in tr
    assert "Eğilim çizgisi boyunca değişim -21,0 yüzde puan." in tr
    # One test in the report: no Holm adjustment is quoted.
    assert "Holm" not in en and "Holm" not in tr
    assert "gives p=0.059, so the trend is not statistically significant" in en


def test_a_significant_verdict_is_stated_as_significant():
    f = samples.findings(samples.trend(p_value=0.004, direction="increasing", slope=38700.0,
                                       first_value=29500.0, latest_value=181000.0))
    assert "so the trend is statistically significant at the 0.05 level" in report_text.section_facts(
        f.sections[0].stat_result, "en")
    assert "istatistiksel olarak anlamlı." in report_text.section_facts(
        f.sections[0].stat_result, "tr")


def test_a_trend_whose_latest_value_is_on_the_other_side_names_the_peak():
    r = samples.trend(direction="decreasing", first_value=7070000.0, latest_value=8590000.0,
                      periods=["2023-08-01", "2025-01-01", "2026-09-01"],
                      values=[7070000.0, 11600000.0, 8590000.0], resolution="month",
                      first_period="2023-08-01", last_period="2026-09-01",
                      latest_period="2026-09-01")
    f = samples.findings(r)
    en = report_text.section_facts(f.sections[0].stat_result, "en")
    tr = report_text.section_facts(f.sections[0].stat_result, "tr")
    assert ("The latest value is above the first, while the trend over the whole window is "
            "decreasing: the series' highest value is 11.6 million people (January 2025).") in en
    assert "serinin en yüksek değeri 11,6 milyon kişi (Ocak 2025)" in tr


def test_a_snapshot_compares_with_the_previous_value_and_says_why_no_test():
    f = samples.findings(samples.snapshot())
    assert report_text.section_facts(f.sections[0].stat_result, "en") == (
        "The latest value is 17.4 million people (2026), up from 14.8 million people in 2025. "
        "Earlier value: 15.8 million people (2024). Three observations are too few for a trend "
        "test.")
    assert report_text.section_facts(f.sections[0].stat_result, "tr") == (
        "Son değer 17,4 milyon kişi (2026); bir önceki değerin (14,8 milyon kişi, 2025) üzerinde. "
        "Daha önceki değer: 15,8 milyon kişi (2024). Üç gözlem eğilim testi için yetersiz.")


def test_years_that_are_not_comparable_are_never_compared():
    r = samples.snapshot(
        indicator="Protection: people in need", values=[14809904.0, 14213777.0, 14988378.0],
        exact=True, sector_en="protection", sector_tr="koruma",
        not_comparable="2024, 2025: possibly one of the plan's separate protection lines rather "
                       "than its overall figure; 2026: the plan's only protection figure; HDX "
                       "HAPI does not say which line each year's figure is",
        not_comparable_years={"line": ["2024", "2025"], "single": ["2026"]})
    f = samples.findings(r)
    en = report_text.section_facts(f.sections[0].stat_result, "en")
    tr = report_text.section_facts(f.sections[0].stat_result, "tr")
    assert en.startswith("The latest value is 14,988,378 people (2026). Earlier values: "
                         "14,213,777 people (2025), 14,809,904 people (2024). The values are not "
                         "comparable across years (2024, 2025: possibly one of")
    assert "up from" not in en and "down from" not in en
    assert tr.startswith("Son değer 14.988.378 kişi (2026). Daha önceki değerler: 14.213.777 kişi "
                         "(2025), 14.809.904 kişi (2024). Değerler yıllar arasında karşılaştırılamaz "
                         "(2024, 2025: planın genel rakamı yerine ayrı “koruma” satırlarından biri "
                         "olabilir; 2026: planın tek “koruma” rakamı;")
    assert "üzerinde" not in tr and "altında" not in tr


def test_a_regional_ranking_without_a_test_says_why():
    f = samples.findings(samples.region())
    assert report_text.section_facts(f.sections[0].stat_result, "en") == (
        "Highest regions as of January 2026: Herat (443,000 people), Balkh (363,000 people), "
        "Kabul (310,000 people). A statistical comparison between regions was not possible: one "
        "observation per region.")
    assert report_text.section_facts(f.sections[0].stat_result, "tr") == (
        "En yüksek bölgeler (Ocak 2026 itibarıyla): Herat (443.000 kişi), Balkh (363.000 kişi), "
        "Kabul (310.000 kişi). Bölgeler arasında istatistiksel karşılaştırma yapılamadı: her bölge "
        "için tek gözlem var.")


def test_a_tested_regional_difference_and_a_correlation_carry_their_verdicts():
    f = samples.findings(
        samples.region(p_value=0.001, kruskal_h=27.34, max_obs=6, first_period="2025-06-01",
                       last_period="2025-12-01"),
        samples.correlation())
    region = report_text.section_facts(f.sections[0].stat_result, "en")
    cor = report_text.section_facts(f.sections[1].stat_result, "en")
    assert "Highest regions (mean per region, June 2025 to December 2025):" in region
    assert ("The Kruskal-Wallis test of the difference between regions (H=27.34) gives p=0.001 "
            "(Holm-adjusted p=0.002), so the difference is statistically significant") in region
    assert cor.startswith("Pearson correlation between Refugees (people) and Returnees (people): "
                          "r=0.85 over eight common periods.")
    assert "so the correlation is statistically significant at the 0.05 level." in cor
    tr = report_text.section_facts(f.sections[1].stat_result, "tr")
    assert "Pearson korelasyonu: r=0,85 (sekiz ortak dönem)" in tr


def test_the_summary_gives_period_headline_latest_values_tests_and_limitation():
    f = samples.findings(
        samples.snapshot(), samples.trend(), samples.share_trend(),
        headline=["Food security: people in need: 17.4 million people (2026)."],
        headline_items=[{"name": "Food security: people in need", "value": 17400000.0,
                         "unit": "people", "period": "2026-01-01", "resolution": "year",
                         "exact": False, "before": False, "not_comparable": False, "caveat": None,
                         "sector_en": "food security", "sector_tr": "gıda güvenliği"}])
    en = report_text.summary_facts(f, "en")
    assert en == (
        "Period analysed: 19 November 2025 to 19 November 2026. Food security: people in need: "
        "17.4 million people (2026). Latest values: Refugees (people): 2.67 million people "
        "(2025); Food insecurity (IPC 3+, % of the analysed population): 32.0% (September 2026). "
        "This report ran two statistical tests; neither is statistically significant at the 0.05 level "
        "after the Holm correction. The series are short, so the results are indicative.")
    tr = report_text.summary_facts(f, "tr")
    assert tr.startswith("Analiz edilen dönem: 19 Kasım 2025 – 19 Kasım 2026. Food security: "
                         "people in need: 17,4 milyon kişi (2026). Son değerler:")
    assert ("Bu raporda iki istatistiksel test yapıldı; 0,05 düzeyinde Holm düzeltmesinden sonra "
            "hiçbiri istatistiksel olarak anlamlı değil.") in tr


def test_the_summary_names_the_significant_findings_and_the_headline_caveats():
    f = samples.findings(
        samples.trend(p_value=0.001), samples.share_trend(),
        headline_items=[{"name": "Koruma: insani yardıma ihtiyaç duyan kişiler", "value": 466589.0,
                         "unit": "people", "period": "2025-01-01", "resolution": "year",
                         "exact": True, "before": True, "not_comparable": True,
                         "caveat": "not_overall", "sector_en": "protection",
                         "sector_tr": "koruma"}])
    tr = report_text.summary_facts(f, "tr")
    assert ("Koruma: insani yardıma ihtiyaç duyan kişiler: 466.589 kişi (2025, seçilen dönemden "
            "önce); önceki yıllar farklı bir temelde raporlandığı için karşılaştırılamaz; bu rakam "
            "planın genel “koruma” rakamı değil.") in tr
    assert "istatistiksel olarak anlamlı olanlar: Refugees (people) — Trend Analysis." in tr
    assert ("statistically significant at the 0.05 level after the Holm correction: Refugees (people) — "
            "Trend Analysis.") in report_text.summary_facts(f, "en")


def test_a_report_without_tests_says_so_in_summary_and_methods():
    f = samples.findings(samples.snapshot())
    assert "No statistical test was possible" in report_text.summary_facts(f, "en")
    assert "The series are short, so the values are descriptive." in report_text.summary_facts(f, "en")
    methods = report_text.methods_text(f, "en")
    assert methods.startswith("No statistical test was possible")
    assert "Mann-Kendall" not in methods and "Holm" not in methods
    assert "İstatistiksel test yapılamadı" in report_text.methods_text(f, "tr")


def test_methods_name_only_the_tests_that_ran():
    one = report_text.methods_text(samples.findings(samples.trend()), "en")
    assert "Mann-Kendall" in one and "no multiple-comparison correction applies" in one
    assert "Kruskal" not in one and "Pearson" not in one and "Holm" not in one
    three = samples.findings(samples.trend(), samples.region(p_value=0.01, kruskal_h=9.1, max_obs=5),
                             samples.correlation())
    en, tr = report_text.methods_text(three, "en"), report_text.methods_text(three, "tr")
    assert "Kruskal-Wallis" in en and "Pearson" in en and "Holm correction across all three tests" in en
    assert "üç testin tümüne birlikte Holm düzeltmesi" in tr
    # Who wrote what is said in the report itself.
    assert "its text is generated from them in code; no part of it is written by an AI model." in en
    assert "metin koddan üretildi; hiçbir bölümü yapay zekâ modeli yazmadı." in tr
    with_comparison = report_text.methods_text(three, "en", "What changed since the last report")
    assert ("only the section “What changed since the last report” is written by an AI model, "
            "comparing this report with the previous one.") in with_comparison


def test_coverage_lists_gaps_and_notes_in_the_report_language():
    f = samples.findings(
        samples.trend(),
        gaps=["Returnees (people): no data in the period"],
        notes=["Internally displaced people (IDPs): only the DTM operation 'X' is used; 1 other "
               "operation(s) count displacement differently and are not mixed in"],
        gap_items=[{"name": "Geri dönenler (kişi)", "code": "no_data"},
                   {"name": "Koruma", "code": "too_few", "n": 3}],
        note_items=[
            {"name": "IDP", "window": "look_back", "kind": "dtm", "operation": "X",
             "other_operations": 1, "incomplete_rounds": 6},
            {"name": "Gıda", "window": None, "kind": "ipc", "low": 41.4e6, "high": 49.7e6},
            {"name": "Koruma", "window": None, "kind": "totals",
             "years": [{"year": "2025", "blank": 349999.0, "total": 466589.0, "used": "total"}]},
            {"name": "Koruma", "window": None, "kind": "plan_line", "year": "2025",
             "lines": [("Child Protection", 1611291.0)], "figure": 466589.0, "below": True,
             "sector_en": "protection", "sector_tr": "koruma"}])
    en = report_text.coverage_text(f, "en")
    assert en.startswith("Data gaps:\n\n- Geri dönenler (kişi): no data in the period\n- Koruma: too "
                         "few observations for a trend test (n=3)\n\nData notes:\n\n- ")
    assert en.endswith("so the results are indicative.")
    tr = report_text.coverage_text(f, "tr")
    assert "- Geri dönenler (kişi): dönemde veri yok" in tr
    assert "- Koruma: eğilim testi için gözlem sayısı yetersiz (n=3)" in tr
    assert ("- IDP (geriye bakış penceresi): yalnızca “X” adlı DTM operasyonu kullanıldı; yerinden "
            "edilmeyi farklı sayan 1 başka operasyon karıştırılmadı; bölgelerinin %80'inden azını "
            "kapsayan 6 eksik tur dışarıda bırakıldı") in tr
    assert "(analiz edilen nüfus 41,4 – 49,7 milyon)" in tr
    assert "2025: kırılımsız 349.999 ve kırılım toplamı 466.589 (kullanılan)" in tr
    assert ("Koruma, 2025: plan “koruma” başlığını ayrı satırlarda raporluyor (Child Protection "
            "1.611.291); bu rakam (466.589) bu satırlardan birinin altında olduğundan planın genel "
            "“koruma” rakamı değil") in tr
    assert "Sınırlılık: seriler kısadır" in tr


def test_the_report_is_assembled_in_a_fixed_order():
    f = samples.findings(samples.snapshot(), samples.trend())
    bare = report_text.assemble(f, "en")
    order = [bare.index(f"## {h}") for h in (
        "Executive Summary", f.sections[0].heading, f.sections[1].heading,
        "Data Coverage & Limitations", "Methods")]
    assert order == sorted(order)
    assert "AI model." in bare and "no part of it is written by an AI model" in bare
    # A next-period report's "What changed" section sits right after the summary, and the
    # Methods then name it as the model-written part.
    full = report_text.assemble(f, "en", ("What changed since the last report", "Needs are new."))
    assert ("indicative.\n\n## What changed since the last report\n\nNeeds are new.\n\n"
            f"## {f.sections[0].heading}") in full
    assert "only the section “What changed since the last report” is written by an AI model" in full
    assert report_text.assemble(f, "en", ("What changed since the last report", " ")) == bare
    tr = report_text.assemble(f, "tr")
    assert tr.startswith("## Yönetici Özeti\n\nAnaliz edilen dönem:")
    assert "## Veri Kapsamı ve Sınırlılıklar" in tr and "## Yöntem" in tr
