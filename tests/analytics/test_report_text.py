"""The technical report's facts are sentences written in code, in English or Turkish."""
from analytics import report_text
from tests.analytics import samples


def test_a_trend_section_states_values_direction_test_and_verdict():
    f = samples.findings(samples.trend(), samples.share_trend())
    text = report_text.section_facts(f.sections[0].stat_result, "en")
    assert text == (
        "The latest value is 2.67 million people (2025). The first value in the window is 5.66 "
        "million people (2022). From 2022 to 2025, the trend is decreasing: Sen's slope is "
        "-817,000 people per year (95% confidence interval: too few points to compute), and "
        "Kendall's tau is -0.33. The Mann-Kendall test gives p=0.734 (Holm-adjusted p=0.734), so "
        "the trend is not statistically significant at the 0.05 level. The relative change along the "
        "trend line is -38.1%. The series has four observations.")


def test_the_same_trend_in_turkish_uses_turkish_figures_and_no_case_suffix_on_them():
    f = samples.findings(samples.trend(), samples.share_trend())
    text = report_text.section_facts(f.sections[0].stat_result, "tr")
    assert text == (
        "Son değer 2,67 milyon kişi (2025). Penceredeki ilk değer 5,66 milyon kişi (2022). "
        "2022 – 2025 arasında eğilim azalış yönünde: Sen eğimi yılda -817.000 kişi (%95 güven "
        "aralığı: hesaplamak için nokta sayısı yetersiz), Kendall tau -0,33. Mann-Kendall testi "
        "p=0,734 veriyor (Holm düzeltmeli p=0,734). Eğilim 0,05 düzeyinde istatistiksel olarak "
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
    assert ("Mann-Kendall testi p=0,004 veriyor. Eğilim 0,05 düzeyinde istatistiksel olarak "
            "anlamlı.") in report_text.section_facts(f.sections[0].stat_result, "tr")


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
    assert ("Son değer ilk değerin üzerinde olsa da pencerenin tamamındaki eğilim azalış yönünde. "
            "Serinin en yüksek değeri 11,6 milyon kişi (Ocak 2025). Mann-Kendall testi") in tr


def test_a_snapshot_compares_with_the_previous_value_and_says_why_no_test():
    f = samples.findings(samples.snapshot())
    assert report_text.section_facts(f.sections[0].stat_result, "en") == (
        "The latest value is 17.4 million people (2026), up from 14.8 million people in 2025. "
        "Earlier value: 15.8 million people (2024). Three observations are too few for a trend "
        "test.")
    assert report_text.section_facts(f.sections[0].stat_result, "tr") == (
        "Son değer 17,4 milyon kişi (2026), bir önceki değerin (14,8 milyon kişi, 2025) üzerinde. "
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
    # Each kind of year is explained in a sentence of its own, from not_comparable_years.
    assert en == (
        "The latest value is 14,988,378 people (2026). Earlier values: 14,213,777 people (2025), "
        "14,809,904 people (2024). The values are not comparable across years. 2024, 2025: "
        "possibly one of the plan's separate protection lines rather than its overall figure. "
        "2026: the plan's only protection figure. HDX HAPI does not say which line each year's "
        "figure is. No trend is tested.")
    assert "up from" not in en and "down from" not in en
    assert tr == (
        "Son değer 14.988.378 kişi (2026). Daha önceki değerler: 14.213.777 kişi (2025), "
        "14.809.904 kişi (2024). Değerler yıllar arasında karşılaştırılamaz. 2024, 2025: planın "
        "genel rakamı yerine ayrı “koruma” satırlarından biri olabilir. 2026: planın tek “koruma” "
        "rakamı. HDX HAPI her yılın rakamının hangi satır olduğunu belirtmiyor. Bu nedenle eğilim "
        "testi yapılmadı.")
    assert "üzerinde" not in tr and "altında" not in tr
    # Without the per-year detail the reason is the plain one, still with no comparison.
    plain = samples.findings(samples.snapshot(not_comparable="reported on a different basis"))
    en = report_text.section_facts(plain.sections[0].stat_result, "en")
    tr = report_text.section_facts(plain.sections[0].stat_result, "tr")
    assert en.endswith("(2024). The values are not comparable across years. The years are reported "
                       "on a different basis. No trend is tested.")
    assert "up from" not in en and "down from" not in en
    assert tr.endswith("(2024). Değerler yıllar arasında karşılaştırılamaz. Yıllar farklı bir "
                       "temelde raporlandı. Bu nedenle eğilim testi yapılmadı.")
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
    assert tr.endswith("Test p=0,004 veriyor (Holm düzeltmeli p=0,004). Korelasyon 0,05 düzeyinde "
                       "istatistiksel olarak anlamlı.")
    assert report_text.section_facts(f.sections[0].stat_result, "tr").endswith(
        "Bölgeler arasındaki fark için Kruskal-Wallis testi H=27,34, p=0,001 veriyor (Holm "
        "düzeltmeli p=0,002). Fark 0,05 düzeyinde istatistiksel olarak anlamlı.")


_FOOD = {"name": "Food security: people in need", "value": 17400000.0, "unit": "people",
         "period": "2026-01-01", "resolution": "year", "exact": False, "before": False,
         "not_comparable": False, "caveat": None, "sector_en": "food security",
         "sector_tr": "gıda güvenliği"}
_PROTECTION = {"name": "Koruma: insani yardıma ihtiyaç duyan kişiler", "value": 466589.0,
               "unit": "people", "period": "2025-01-01", "resolution": "year", "exact": True,
               "before": True, "not_comparable": True, "caveat": "not_overall",
               "sector_en": "protection", "sector_tr": "koruma"}
_LOOK_BACK = {"chosen_points": 0, "date_from": "2021-11-19", "date_to": "2026-11-19"}


def test_the_summary_gives_period_headline_latest_values_tests_and_limitation():
    # The legacy headline string is not what either language prints: both build the
    # headline from headline_items.
    f = samples.findings(
        samples.snapshot(), samples.trend(), samples.share_trend(),
        headline=["LEGACY HEADLINE STRING."], headline_items=[_FOOD])
    en = report_text.summary_facts(f, "en")
    assert en == (
        "Period analysed: 19 November 2025 to 19 November 2026.\n\n"
        "Latest values:\n\n"
        "- Food security: people in need: 17.4 million people (2026).\n"
        "- Refugees (people): 2.67 million people (2025).\n"
        "- Food insecurity (IPC 3+, % of the analysed population): 32.0% (September 2026).\n\n"
        "This report ran two statistical tests. Neither is statistically significant at the 0.05 "
        "level after the Holm correction. The series are short, so the results are indicative.")
    tr = report_text.summary_facts(f, "tr")
    assert tr == (
        "Analiz edilen dönem: 19 Kasım 2025 – 19 Kasım 2026.\n\n"
        "Son değerler:\n\n"
        "- Food security: people in need: 17,4 milyon kişi (2026).\n"
        "- Refugees (people): 2,67 milyon kişi (2025).\n"
        "- Food insecurity (IPC 3+, % of the analysed population): %32,0 (Eylül 2026).\n\n"
        "Bu raporda iki istatistiksel test yapıldı. İkisi de 0,05 düzeyinde Holm düzeltmesinden "
        "sonra istatistiksel olarak anlamlı değil. Seriler kısa olduğundan sonuçlar gösterge "
        "niteliğindedir.")
    assert "LEGACY" not in en and "LEGACY" not in tr


def test_the_summary_lists_the_latest_values_as_bullets_with_the_sectors_own_first():
    f = samples.findings(samples.trend(), samples.share_trend(), samples.snapshot(),
                         headline_items=[_PROTECTION, _FOOD])
    for language, label in (("en", "Latest values:"), ("tr", "Son değerler:")):
        summary = report_text.summary_facts(f, language)
        blocks = summary.split("\n\n")
        assert blocks[1] == label
        lines = blocks[2].split("\n")
        assert len(lines) == 4 and all(line.startswith("- ") for line in lines)
        # The sector's own figures come first, in their order, then the other series. The
        # snapshot of a headline series is not listed a second time.
        assert [line[2:].split(": ")[0] for line in lines] == [
            "Koruma", "Food security", "Refugees (people)",
            "Food insecurity (IPC 3+, % of the analysed population)"]
        assert summary.count("Food security: people in need") == 1
        # Every bullet ends with a full stop, a one-clause one too.
        assert all(line.endswith(".") and not line.endswith("..") for line in lines)
        # The list is closed by a paragraph, not by another bullet.
        assert not blocks[3].startswith("- ") and len(blocks) == 4


def test_the_summary_names_the_significant_findings_and_the_headline_caveats():
    f = samples.findings(samples.trend(p_value=0.001), samples.share_trend(),
                         headline_items=[_PROTECTION])
    assert report_text.summary_facts(f, "tr") == (
        "Analiz edilen dönem: 19 Kasım 2025 – 19 Kasım 2026.\n\n"
        "Son değerler:\n\n"
        "- Koruma: insani yardıma ihtiyaç duyan kişiler: 466.589 kişi (2025, seçilen dönemden "
        "önce). Önceki yıllar farklı bir temelde raporlandığı için karşılaştırılamaz. Bu rakam "
        "planın genel “koruma” rakamı değil.\n"
        "- Refugees (people): 2,67 milyon kişi (2025).\n"
        "- Food insecurity (IPC 3+, % of the analysed population): %32,0 (Eylül 2026).\n\n"
        "Bu raporda iki istatistiksel test yapıldı. 0,05 düzeyinde Holm düzeltmesinden sonra "
        "istatistiksel olarak anlamlı olanlar:\n\n"
        "- Refugees (people) — Trend Analysis\n\n"
        "Seriler kısa olduğundan sonuçlar gösterge niteliğindedir.")
    assert report_text.summary_facts(f, "en") == (
        "Period analysed: 19 November 2025 to 19 November 2026.\n\n"
        "Latest values:\n\n"
        "- Koruma: insani yardıma ihtiyaç duyan kişiler: 466,589 people (2025, before the chosen "
        "period). Earlier years are reported on a different basis and are not comparable. This "
        "figure is not the plan's overall protection figure.\n"
        "- Refugees (people): 2.67 million people (2025).\n"
        "- Food insecurity (IPC 3+, % of the analysed population): 32.0% (September 2026).\n\n"
        "This report ran two statistical tests. These are statistically significant at the 0.05 "
        "level after the Holm correction:\n\n"
        "- Refugees (people) — Trend Analysis\n\n"
        "The series are short, so the results are indicative.")
    # A figure that only may not be the overall one says so, in both languages.
    maybe = samples.findings(samples.trend(), headline_items=[
        {**_PROTECTION, "before": False, "not_comparable": False, "caveat": "maybe_not_overall"}])
    assert ("466,589 people (2025). This figure may not be the plan's overall protection figure."
            ) in report_text.summary_facts(maybe, "en")
    assert ("466.589 kişi (2025). Bu rakam planın genel “koruma” rakamı olmayabilir."
            ) in report_text.summary_facts(maybe, "tr")


def test_the_summary_of_one_test_and_of_a_look_back_are_whole_sentences():
    one = samples.findings(samples.trend())
    assert report_text.summary_facts(one, "en").endswith(
        "This report ran one statistical test (Refugees (people) — Trend Analysis). Its result is "
        "not statistically significant at the 0.05 level. The series are short, so the results "
        "are indicative.")
    assert report_text.summary_facts(one, "tr").endswith(
        "Bu raporda bir istatistiksel test yapıldı (Refugees (people) — Trend Analysis). Sonuç "
        "0,05 düzeyinde istatistiksel olarak anlamlı değil. Seriler kısa olduğundan sonuçlar "
        "gösterge niteliğindedir.")
    # Three tests, none significant: "None" / "Hiçbiri" (two say "Neither" / "İkisi de").
    three = samples.findings(samples.trend(), samples.share_trend(), samples.correlation(p_value=0.5))
    assert ("This report ran three statistical tests. None is statistically significant at the "
            "0.05 level after the Holm correction. The series") in report_text.summary_facts(three, "en")
    assert ("Bu raporda üç istatistiksel test yapıldı. Hiçbiri 0,05 düzeyinde Holm düzeltmesinden "
            "sonra istatistiksel olarak anlamlı değil. Seriler") in report_text.summary_facts(three, "tr")
    looked = samples.findings(samples.trend(look_back=_LOOK_BACK), default_years=5)
    en, tr = report_text.summary_facts(looked, "en"), report_text.summary_facts(looked, "tr")
    assert en.startswith("Period analysed: 19 November 2025 to 19 November 2026 (no period was "
                         "chosen: the last five years).\n\nLatest values:\n\n- Refugees (people): "
                         "2.67 million people (2025, before the chosen period).\n\n")
    assert ("The chosen period holds too few observations for Refugees (people), so their values "
            "and trends cover the longer look-back window 19 November 2021 to 19 November 2026. "
            "The series are short") in en
    assert tr.startswith("Analiz edilen dönem: 19 Kasım 2025 – 19 Kasım 2026 (dönem seçilmedi: son "
                         "beş yıl).\n\nSon değerler:\n\n- Refugees (people): 2,67 milyon kişi "
                         "(2025, seçilen dönemden önce).\n\n")
    assert ("Seçilen dönemdeki gözlem sayısı şu göstergeler için yetersiz: Refugees (people). Bu "
            "göstergelerin değerleri ve eğilimleri daha uzun geriye bakış penceresini kapsıyor "
            "(19 Kasım 2021 – 19 Kasım 2026). Seriler kısa") in tr


def test_a_report_without_tests_says_so_in_summary_and_methods():
    f = samples.findings(samples.snapshot())
    assert ("No statistical test was possible. The findings are reported as their observed "
            "values.") in report_text.summary_facts(f, "en")
    assert ("İstatistiksel test yapılamadı. Bulgular gözlenen değerleriyle raporlanıyor. Seriler "
            "kısa olduğundan değerler betimleyicidir.") in report_text.summary_facts(f, "tr")
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
    assert en.endswith("its text is generated from them in code. No part of it is written by an "
                       "AI model.")
    assert tr.endswith("metin koddan üretildi. Hiçbir bölümü yapay zekâ modeli yazmadı.")
    with_comparison = report_text.methods_text(three, "en", "What changed since the last report")
    assert with_comparison.endswith(
        "its text is generated from them in code. Only the section “What changed since the last "
        "report” is written by an AI model, comparing this report with the previous one.")
    assert "No part of it" not in with_comparison
    tr_comparison = report_text.methods_text(three, "tr", "Son rapordan bu yana ne değişti")
    assert tr_comparison.endswith(
        "metin koddan üretildi. Yalnızca “Son rapordan bu yana ne değişti” bölümünü, bu rapor ile "
        "önceki raporu karşılaştıran bir yapay zekâ modeli yazdı.")
    assert "Hiçbir bölümü" not in tr_comparison
    # The methods are sentences of their own.
    assert one == (
        "Trend: Mann-Kendall test. The slope is Sen's slope per year on the real dates of the "
        "periods, and Kendall's tau is the effect size. One statistical test was run, so no "
        "multiple-comparison correction applies. Significance is decided on its p-value at the "
        "0.05 level. The data come from HDX HAPI (the Humanitarian Data Exchange's data API), and "
        "the datasets used are in the source list. The values, tests and verdicts in this report "
        "are computed in code, and its text is generated from them in code. No part of it is "
        "written by an AI model.")
    assert ("Holm correction across all three tests in this report. Significance is decided on "
            "the Holm-adjusted p-value at the 0.05 level.") in en
    assert ("Holm düzeltmesi uygulandı. Anlamlılık 0,05 düzeyinde Holm düzeltmeli p-değerine göre "
            "belirlendi.") in tr


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
    # Both languages are built from gap_items and note_items, not from the legacy strings.
    assert report_text.coverage_text(f, "en") == (
        "Data gaps:\n\n"
        "- Geri dönenler (kişi): no data in the period.\n"
        "- Koruma: too few observations for a trend test (n=3).\n\n"
        "Data notes:\n\n"
        "- IDP (look-back window): Only the DTM operation “X” is used. One other operation "
        "counts displacement differently and is not mixed in. Six incomplete rounds covering "
        "under 80% of its regions are left out.\n"
        "- Gıda: IPC analyses covered different parts of the country in different periods "
        "(analysed population 41.4 to 49.7 million), so the share of the analysed population is "
        "used, not the number of people.\n"
        "- Koruma: HDX HAPI holds two totals for 2025: 349,999 without a breakdown and 466,589 as "
        "the total of its breakdown (used). The HNO's published sector figure may differ.\n"
        "- Koruma, 2025: the plan reports protection in separate lines (Child Protection "
        "1,611,291). This figure (466,589) is below one of them, so it is not the plan's overall "
        "protection figure. HDX HAPI does not say which of the plan's lines it is. This report "
        "does not add the lines up, because people can be counted in more than one.\n\n"
        "Limitation: the series are short. The tests assume independent observations, and serial "
        "correlation between consecutive periods is not corrected for, so the results are "
        "indicative.")
    assert report_text.coverage_text(f, "tr") == (
        "Veri boşlukları:\n\n"
        "- Geri dönenler (kişi): dönemde veri yok.\n"
        "- Koruma: eğilim testi için gözlem sayısı yetersiz (n=3).\n\n"
        "Veri notları:\n\n"
        "- IDP (geriye bakış penceresi): Yalnızca “X” adlı DTM operasyonu kullanıldı. Yerinden "
        "edilmeyi farklı sayan 1 başka operasyon karıştırılmadı. Bölgelerinin %80'inden azını "
        "kapsayan 6 eksik tur dışarıda bırakıldı.\n"
        "- Gıda: IPC analizleri farklı dönemlerde ülkenin farklı bölümlerini kapsadı (analiz "
        "edilen nüfus 41,4 – 49,7 milyon). Bu nedenle kişi sayısı değil, analiz edilen nüfus "
        "içindeki pay kullanıldı.\n"
        "- Koruma: HDX HAPI 2025 için iki toplam içeriyor: kırılımsız 349.999 ve kırılım toplamı "
        "466.589 (kullanılan). HNO'nun yayımladığı sektör rakamı farklı olabilir.\n"
        "- Koruma, 2025: plan “koruma” başlığını ayrı satırlarda raporluyor (Child Protection "
        "1.611.291). Bu rakam (466.589) bu satırlardan birinin altında olduğundan planın genel "
        "“koruma” rakamı değil. HDX HAPI bunun planın hangi satırı olduğunu belirtmiyor. Kişiler "
        "birden fazla satırda sayılabildiği için bu raporda satırlar toplanmadı.\n\n"
        "Sınırlılık: seriler kısadır. Testler gözlemlerin bağımsız olduğunu varsayar ve ardışık "
        "dönemler arasındaki seri korelasyon düzeltilmez. Bu nedenle sonuçlar gösterge "
        "niteliğindedir.")


def test_a_series_whose_years_are_not_comparable_gives_that_as_its_gap():
    f = samples.findings(
        samples.snapshot(not_comparable="reported on a different basis"),
        gap_items=[{"name": "Food security: people in need", "code": "too_few", "n": 3},
                   {"name": "Funding (USD)", "code": "not_retrieved"},
                   {"name": "Conflict events", "code": "analysis_error"}])
    en, tr = report_text.coverage_text(f, "en"), report_text.coverage_text(f, "tr")
    assert en == (
        "Data gaps:\n\n"
        "- Food security: people in need: years not comparable, so no trend was tested.\n"
        "- Funding (USD): could not be retrieved from HDX HAPI.\n"
        "- Conflict events: analysis error.\n\n"
        "Limitation: the series are short, so the values are descriptive.")
    assert tr == (
        "Veri boşlukları:\n\n"
        "- Food security: people in need: yıllar karşılaştırılabilir olmadığından eğilim testi "
        "yapılmadı.\n"
        "- Funding (USD): HDX HAPI'den alınamadı.\n"
        "- Conflict events: analiz hatası.\n\n"
        "Sınırlılık: seriler kısa olduğundan değerler betimleyicidir.")


def test_the_report_is_assembled_in_a_fixed_order():
    f = samples.findings(samples.snapshot(), samples.trend())
    bare = report_text.assemble(f, "en")
    order = [bare.index(f"## {h}") for h in (
        "Executive Summary", f.sections[0].heading, f.sections[1].heading,
        "Data Coverage & Limitations", "Methods")]
    assert order == sorted(order)
    assert bare.endswith("in code. No part of it is written by an AI model.")
    # A next-period report's "What changed" section sits right after the summary, and the
    # Methods then name it as the model-written part.
    full = report_text.assemble(f, "en", ("What changed since the last report", "Needs are new."))
    assert ("indicative.\n\n## What changed since the last report\n\nNeeds are new.\n\n"
            f"## {f.sections[0].heading}") in full
    assert full.endswith("in code. Only the section “What changed since the last report” is "
                         "written by an AI model, comparing this report with the previous one.")
    assert "No part of it" not in full
    assert report_text.assemble(f, "en", ("What changed since the last report", " ")) == bare
    tr = report_text.assemble(f, "tr")
    assert tr.startswith("## Yönetici Özeti\n\nAnaliz edilen dönem:")
    assert "## Veri Kapsamı ve Sınırlılıklar" in tr and "## Yöntem" in tr
    assert tr.endswith("metin koddan üretildi. Hiçbir bölümü yapay zekâ modeli yazmadı.")


def _every_kind():
    """A report with every kind of section, gap, note and headline caveat."""
    return samples.findings(
        samples.trend(p_value=0.001, look_back=_LOOK_BACK),
        samples.share_trend(),
        # Its latest value is on the other side of the first than the trend points.
        samples.trend(indicator="Returnees (people)", direction="increasing", slope=120000.0,
                      first_value=900000.0, latest_value=700000.0, pct_change=12.0,
                      periods=["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"],
                      values=[900000.0, 400000.0, 500000.0, 700000.0]),
        samples.snapshot(),
        samples.snapshot(indicator="Health: people in need", look_back=_LOOK_BACK,
                         periods=["2023-01-01", "2024-01-01", "2025-01-01", "2026-01-01"],
                         values=[5.0e6, 5.0e6, 5.0e6, 5.0e6]),
        samples.snapshot(
            indicator="Protection: people in need", values=[14809904.0, 14213777.0, 14988378.0],
            exact=True, sector_en="protection", sector_tr="koruma",
            not_comparable="2023: a; 2024, 2025: b; 2026: c",
            not_comparable_years={"below": ["2023"], "line": ["2024", "2025"], "single": ["2026"]}),
        samples.snapshot(indicator="WASH: people in need", not_comparable="a different basis"),
        samples.region(),
        samples.region(indicator="Returnees by region", p_value=0.001, kruskal_h=27.34, max_obs=6,
                       first_period="2025-06-01", last_period="2025-12-01"),
        samples.region(indicator="Refugees by region", max_obs=3),
        samples.correlation(),
        default_years=5,
        # The legacy strings carry semicolons. The report is not built from them.
        headline=["Protection: people in need: 466,589 people (2025); not comparable."],
        gaps=["Returnees (people): no data in the period; nothing to show"],
        notes=["IDP: only the DTM operation 'X' is used; 2 other operation(s) are not mixed in"],
        headline_items=[
            {"name": "Protection: people in need", "value": 466589.0, "unit": "people",
             "period": "2025-01-01", "resolution": "year", "exact": True, "before": True,
             "not_comparable": True, "caveat": "not_overall", "sector_en": "protection",
             "sector_tr": "koruma"},
            {"name": "Child protection: people in need", "value": 1611291.0, "unit": "people",
             "period": "2026-01-01", "resolution": "year", "exact": True, "before": False,
             "not_comparable": False, "caveat": "maybe_not_overall", "sector_en": "protection",
             "sector_tr": "koruma"}],
        gap_items=[{"name": "Funding (USD)", "code": "not_retrieved"},
                   {"name": "Returnees (people)", "code": "no_data"},
                   {"name": "Food security: people in need", "code": "too_few", "n": 3},
                   {"name": "WASH: people in need", "code": "not_comparable"},
                   {"name": "Conflict events", "code": "analysis_error"}],
        note_items=[
            {"name": "IDP", "window": "look_back", "kind": "dtm", "operation": "X",
             "other_operations": 2, "incomplete_rounds": 1},
            {"name": "IDP", "window": "chosen", "kind": "dtm", "operation": "X",
             "other_operations": 1, "incomplete_rounds": 6},
            {"name": "Food", "window": None, "kind": "ipc", "low": 41.4e6, "high": 49.7e6},
            {"name": "Protection", "window": None, "kind": "totals",
             "years": [{"year": "2025", "blank": 349999.0, "total": 466589.0, "used": "total"},
                       {"year": "2026", "blank": 500000.0, "total": 400000.0, "used": ""}]},
            {"name": "Protection", "window": None, "kind": "plan_line", "year": "2025",
             "lines": [("Child Protection", 1611291.0), ("Mine Action", 900000.0)],
             "figure": 466589.0, "below": True, "sector_en": "protection", "sector_tr": "koruma"},
            {"name": "Protection", "window": None, "kind": "plan_line", "year": "2026",
             "lines": [("Child Protection", 1611291.0)], "figure": 2466589.0, "below": False,
             "sector_en": "protection", "sector_tr": "koruma"}])


_EVERY_KIND_SAYS = {
    "en": ["Over the look-back window, 2022 to 2025,", "percentage points per year",
           "the series' lowest value is 400,000 people (2023)", "up from 14.8 million people",
           "The values do not vary, so no trend is tested.",
           "2023: one of the plan's separate protection lines, not its overall figure.",
           "The years are reported on a different basis.", "one observation per region",
           "fewer than two regions have two or more observations", "(H=27.34)",
           "Pearson correlation between", "could not be retrieved from HDX HAPI.\n",
           "no data in the period.\n", "(n=3).\n", "so no trend was tested.\n",
           "analysis error.\n\n",
           "Two other operations count displacement differently and are not mixed in. One "
           "incomplete round covering under 80% of its regions is left out.\n",
           "One other operation counts displacement differently and is not mixed in. Six "
           "incomplete rounds covering under 80% of its regions are left out.\n",
           "Only the DTM operation “X” is used.", "IPC analyses covered",
           "HDX HAPI holds two totals for 2026", "is below one of them",
           "may be another of the plan's protection lines",
           "Earlier years are reported on a different basis and are not comparable.",
           "This figure may not be the plan's overall protection figure.",
           "The chosen period holds too few observations for",
           "These are statistically significant at the 0.05 level after the Holm correction:\n\n"
           "- Refugees (people) — Trend Analysis\n- Returnees by region — Regional Analysis\n"
           "- Correlation — Refugees (people) ↔ Returnees (people)\n\n"],
    "tr": ["Geriye bakış penceresinde (2022 – 2025)", "yüzde puan",
           "Serinin en düşük değeri 400.000 kişi (2023)", "bir önceki değerin (14,8 milyon",
           "Değerler değişmediği için eğilim testi yapılmadı.",
           "2023: planın ayrı “koruma” satırlarından biri, genel rakam değil.",
           "Yıllar farklı bir temelde raporlandı.", "her bölge için tek gözlem var",
           "iki veya daha fazla gözlemi olan bölge sayısı ikiden az", "H=27,34",
           "Pearson korelasyonu", "HDX HAPI'den alınamadı.\n", "dönemde veri yok.\n",
           "(n=3).\n", "olmadığından eğilim testi yapılmadı.\n", "analiz hatası.\n\n",
           "Yalnızca “X” adlı DTM operasyonu kullanıldı.", "IPC analizleri",
           "HDX HAPI 2026 için iki toplam içeriyor", "bu satırlardan birinin altında",
           "başka bir “koruma” satırı olabilir",
           "Önceki yıllar farklı bir temelde raporlandığı için karşılaştırılamaz.",
           "Bu rakam planın genel “koruma” rakamı olmayabilir.",
           "Seçilen dönemdeki gözlem sayısı şu göstergeler için yetersiz:",
           "istatistiksel olarak anlamlı olanlar:\n\n"
           "- Refugees (people) — Trend Analysis\n- Returnees by region — Regional Analysis\n"
           "- Correlation — Refugees (people) ↔ Returnees (people)\n\n"],
}


def test_no_sentence_of_a_report_is_joined_by_a_semicolon():
    """An owner rule for all visible text: every section kind, gap, note and caveat, in both
    languages, with and without a "What changed" section."""
    for language in ("en", "tr"):
        bare = report_text.assemble(_every_kind(), language)
        full = report_text.assemble(_every_kind(), language, ("What changed", "Needs are new."))
        # The fixture really exercises every branch it is meant to.
        for said in _EVERY_KIND_SAYS[language]:
            assert said in bare, said
        assert bare.count("\n## ") == 13 and full.count("\n## ") == 14
        assert ";" not in bare and ";" not in full
        # Every bullet ends with a full stop, except the significant findings' headings.
        bullets = [line for line in bare.split("\n") if line.startswith("- ")]
        headings = [line for line in bullets if not line.endswith(".")]
        assert len(bullets) == 22 and len(headings) == 3
        assert all("—" in line and ".." not in line for line in headings)
    # The same holds for a report with no test at all.
    untested = samples.findings(samples.snapshot())
    assert ";" not in report_text.assemble(untested, "en") + report_text.assemble(untested, "tr")
