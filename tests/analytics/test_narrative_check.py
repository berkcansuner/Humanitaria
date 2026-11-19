"""The technical report's narrative is checked against the code-computed findings:
a sentence with a number the findings do not contain, or a significance claim that
contradicts the code's verdict, is removed (the prompt alone could not enforce it)."""
from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

TREND_H = "Ülke içinde yerinden edilmiş kişiler (IDP) — Eğilim Analizi"
REGION_H = "Ülke içinde yerinden edilmiş kişiler (IDP) — Bölgesel Analiz"

CONTEXT = (
    "COMPUTED STATISTICAL FINDINGS (do not recompute — narrate only):\n\n"
    f"## {TREND_H}\n"
    "Ülke içinde yerinden edilmiş kişiler (IDP): direction=increasing, Sen slope=1234.50 per year "
    "(95% CI: too few points), Kendall tau=0.80, Mann-Kendall p=0.012, Holm-adjusted p=0.024 "
    "→ SIGNIFICANT (α=0.05), change 2021-01-01 → 2025-01-01=%412.3, n=5.\n\n"
    f"## {REGION_H}\n"
    "Ülke içinde yerinden edilmiş kişiler (IDP): highest regions — North (2345678), South (120000); "
    "difference between regions Kruskal-Wallis H=1.20, p=0.270, Holm-adjusted p=0.270 → "
    "NOT SIGNIFICANT (α=0.05).\n"
)


def _findings(trend_sig=True, region_sig=False):
    return Findings(sections=[
        ReportSection(TREND_H, {"kind": "trend", "significant": trend_sig}, None, ""),
        ReportSection(REGION_H, {"kind": "region", "significant": region_sig}, None, ""),
    ], gaps=[], indicators_covered=["idps"])


def _check(text, language="en", **kw):
    return verify_narrative(text, _findings(**kw), CONTEXT, language)


def test_a_faithful_report_is_left_alone():
    text = (
        "## Executive Summary\n\nDisplacement rose significantly between 2021 and 2025.\n\n"
        f"## {TREND_H}\n\nThe number of IDPs increased by 1,234.50 people per year "
        "(Kendall tau 0.80). The trend is statistically significant (p=0.012, Holm-adjusted "
        "p=0.024).\n\n"
        f"## {REGION_H}\n\nNorth (2,345,678) leads, but the difference between regions is not "
        "statistically significant (H=1.20, p=0.270).\n\n"
        "## Methods\n\nSix indicators were tested at the 95% level, α=0.05."
    )
    out = _check(text)
    assert out.removed == 0
    assert out.content == text


def test_a_number_the_findings_do_not_contain_is_removed():
    text = (f"## {TREND_H}\n\nThe number of IDPs increased by 1,500 people per year. "
            "The trend is statistically significant (p=0.012).")
    out = _check(text)
    assert out.removed == 1
    assert "1,500" not in out.content
    assert "statistically significant (p=0.012)" in out.content


def test_turkish_number_formats_scale_words_and_rounding_are_accepted():
    text = (f"## {TREND_H}\n\nIDP sayısı yılda 1.234,5 kişi arttı ve toplam değişim %412,3 oldu "
            "(p=0,01). Artış istatistiksel olarak anlamlıdır.\n\n"
            f"## {REGION_H}\n\nKuzey yaklaşık 2,3 milyon kişiyle başı çekiyor; bölgeler arası "
            "fark anlamlı değildir.")
    out = _check(text, language="tr")
    assert out.removed == 0, out.content


def test_a_significance_claim_against_the_verdict_is_removed():
    text = (f"## {REGION_H}\n\nNorth leads the ranking. The difference between regions is "
            "statistically significant.\n\n"
            f"## {TREND_H}\n\nThe increase is not statistically significant.")
    out = _check(text)
    assert out.removed == 2
    assert "North leads the ranking." in out.content
    assert "significant" not in out.content


def test_turkish_negation_after_the_claim_is_read():
    text = (f"## {TREND_H}\n\nArtış istatistiksel olarak anlamlı bir eğilim göstermemektedir.\n\n"
            f"## {REGION_H}\n\nBölgeler arası fark anlamlı değildir.")
    out = _check(text, language="tr")
    assert out.removed == 1                     # the trend IS significant
    assert "göstermemektedir" not in out.content
    assert "anlamlı değildir" in out.content


def test_summary_may_not_claim_significance_when_no_finding_is_significant():
    text = "## Executive Summary\n\nDisplacement rose significantly.\n\nRegions differ."
    assert _check(text, trend_sig=False).removed == 1
    assert _check(text, trend_sig=True).removed == 0


def test_significance_noun_and_small_counts_are_not_claims_or_numbers():
    text = ("## Methods\n\nThe significance threshold is α=0.05 and 3 tests were run; "
            "statistical significance was assessed with the Holm correction.")
    assert _check(text, trend_sig=False).removed == 0


def test_headings_are_kept_and_an_emptied_finding_gets_a_placeholder_and_a_note():
    text = f"## {TREND_H}\n\nThe slope is 999.99 per year.\n\n## Methods\n\nα=0.05."
    out = _check(text)
    assert out.removed == 1
    assert f"## {TREND_H}" in out.content and "## Methods" in out.content
    assert "could not be verified" in out.content       # placeholder under the heading
    assert out.content.rstrip().endswith("_")             # italic note at the end
    assert "1 sentence" in out.content


def test_turkish_note():
    out = _check(f"## {TREND_H}\n\nEğim yılda 999,99 kişidir.", language="tr")
    assert "doğrulanamayan 1 cümle" in out.content


def test_bullet_lines_are_checked_one_by_one():
    text = "## Data Coverage & Limitations\n\n- Refugees: n=5 periods.\n- Funding: n=17 periods."
    out = _check(text)
    assert out.removed == 1
    assert "- Refugees: n=5 periods." in out.content and "17" not in out.content.split("_Note")[0]


def test_placeholder_only_where_this_sections_sentences_were_removed():
    # The region section is empty in the model's text; the removal happens elsewhere.
    text = f"## {REGION_H}\n\n## {TREND_H}\n\nThe slope is 999.99 per year. It rose."
    out = _check(text)
    assert out.removed == 1
    region_part = out.content.split(f"## {TREND_H}")[0]
    assert "could not be verified" not in region_part


def test_turkish_formatted_and_rounded_figures_pass():
    # The prompt now asks for numbers in the report language's format, with large
    # figures rounded: 1234.50 -> "1.234,5", "yaklaşık 1,2 bin"; 2345678 -> "2,35 milyon".
    text = (f"## {TREND_H}\n\nIDP sayısı yılda 1.234,5 kişi, yani yaklaşık 1,2 bin kişi arttı; "
            "artış istatistiksel olarak anlamlıdır (p=0,012).\n\n"
            f"## {REGION_H}\n\nKuzey yaklaşık 2,35 milyon kişiyle başı çekiyor.")
    assert _check(text, language="tr").removed == 0


def test_rounding_that_changes_the_value_is_still_caught():
    # "1,3 bin" is 1,300, not 1,234.5 rounded to one decimal of a thousand (1,2).
    text = f"## {TREND_H}\n\nIDP sayısı yılda yaklaşık 1,3 bin kişi arttı."
    assert _check(text, language="tr").removed == 1


def test_scale_words_on_a_range_in_the_context_are_honoured():
    # Live check (Yemen, 2026-11-16): the context said "analysed population 9.5 to 35.0
    # million"; the Turkish note "9,5 milyon ile 35,0 milyon" was removed as unverified.
    findings = Findings(sections=[], gaps=[], indicators_covered=[])
    context = "DATA NOTES:\n- IPC analyses covered (analysed population 9.5 to 35.0 million).\n"
    text = "## Veri Kapsamı\n\nAnaliz edilen nüfus 9,5 milyon ile 35,0 milyon arasında değişti."
    out = verify_narrative(text, findings, context, "tr")
    assert out.removed == 0, out.content
    # A figure written out in full against a scaled context value also passes.
    out = verify_narrative("## X\n\nNüfus 35.000.000 kişiydi.", findings, context, "tr")
    assert out.removed == 0, out.content


# --- 2026-11-18: a regional comparison that could not be tested (one observation per
# region) was narrated as "not statistically significant". An untested finding has no
# verdict: neither claim survives the check, the plain statement does. ---

SNAPSHOT_H = "Internally displaced people (IDPs) — Regional Analysis"
SNAPSHOT_CONTEXT = (
    f"## {SNAPSHOT_H}\n"
    "Internally displaced people (IDPs): ranking snapshot as of 2026-03-31 — highest regions: "
    "Herat (443000), Balkh (363000), Kabul (310000); a statistical comparison between regions "
    "was not possible: one observation per region.\n"
)


def _untested_check(text, language="en"):
    findings = Findings(sections=[ReportSection(
        SNAPSHOT_H, {"kind": "region", "significant": False, "tested": False}, None, "")],
        gaps=[], indicators_covered=["idps"])
    return verify_narrative(text, findings, SNAPSHOT_CONTEXT, language)


def test_an_untested_finding_is_never_called_not_significant():
    text = (f"## {SNAPSHOT_H}\n\nHerat (443,000) has the most IDPs, followed by Balkh "
            "(363,000). The difference between regions is not statistically significant.")
    out = _untested_check(text)
    assert out.removed == 1
    assert "not statistically significant" not in out.content
    assert "Herat (443,000) has the most IDPs" in out.content


def test_an_untested_finding_said_to_be_untested_is_kept():
    text = (f"## {SNAPSHOT_H}\n\nHerat (443,000) has the most IDPs as of 31 March 2026. "
            "A statistical comparison between regions was not possible, as each region has "
            "one observation.")
    assert _untested_check(text).removed == 0
    tr = (f"## {SNAPSHOT_H}\n\n31 Mart 2026 itibarıyla en çok IDP Herat'ta (443.000). "
          "Her bölgede tek gözlem olduğundan bölgeler arasında istatistiksel bir "
          "karşılaştırma yapılamadı.")
    assert _untested_check(tr, "tr").removed == 0


def test_an_untested_finding_is_never_called_significant_either():
    text = f"## {SNAPSHOT_H}\n\nHerat stands out significantly from the other regions."
    assert _untested_check(text).removed == 1



# --- Round 3: a Methods sentence naming a test the METHOD NOTES do not list is removed. ---

ONE_TEST_CONTEXT = (CONTEXT + "\nMETHOD NOTES:\n- Trend: Mann-Kendall test; the slope is Sen's slope "
                    "per year on the real dates of the periods; Kendall tau is the effect size.\n"
                    "- One statistical test was run, so no multiple-comparison correction applies; "
                    "significance is decided on its p-value at α=0.05.\n")


def _methods(sentence, language="en", heading="Methods"):
    return verify_narrative(f"## {heading}\n\n{sentence}", _findings(), ONE_TEST_CONTEXT, language)


def test_a_methods_sentence_naming_an_unused_test_is_removed():
    for sentence, language, heading in (
            ("Regional differences were assessed with the Kruskal-Wallis test.", "en", "Methods"),
            ("Correlations were measured with Pearson's coefficient.", "en", "Methods"),
            ("The Holm correction was applied across all tests.", "en", "Methods"),
            ("Bölgesel farklar Kruskal-Wallis testiyle değerlendirildi.", "tr", "Yöntemler"),
            ("Çoklu karşılaştırmalar için Holm düzeltmesi uygulandı.", "tr", "Yöntem")):
        assert _methods(sentence, language, heading).removed == 1, sentence


def test_a_methods_sentence_naming_a_used_test_stays():
    for sentence, language, heading in (
            ("The trend was tested with the Mann-Kendall test and Sen's slope.", "en", "Methods"),
            ("A single test was run, so no multiple-comparison correction applies.", "en", "Methods"),
            ("Eğilim Mann-Kendall testiyle ve Sen eğimiyle sınandı.", "tr", "Yöntemler")):
        assert _methods(sentence, language, heading).removed == 0, sentence


# --- Round 3: each removed sentence is logged with the report it came from and the rule. ---

def test_each_removed_sentence_is_logged_with_its_report_and_rule(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="analytics.narrative_check")
    text = (f"## {TREND_H}\n\nThe number of IDPs increased by 1,500 people per year.\n\n"
            "## Methods\n\nCorrelations were measured with Pearson's coefficient.")
    findings = _findings()
    out = verify_narrative(text, findings, ONE_TEST_CONTEXT, "en",
                           label="Afghanistan / Protection and Human Rights / technical_monitoring")
    assert out.removed == 2
    logged = [r.getMessage() for r in caplog.records if r.name == "analytics.narrative_check"]
    assert any("Afghanistan / Protection and Human Rights / technical_monitoring" in m
               and "a number not in the findings" in m and "1,500" in m for m in logged)
    assert any("a test the method notes do not list" in m and "Pearson" in m for m in logged)


# --- Round 3 review (C1, I3): the reviewer's claims.py sentences. ---

import pytest  # noqa: E402
from analytics.narrative_check import _claim  # noqa: E402


@pytest.mark.parametrize("sentence,claim", [
    ("Although not large, the decline is statistically significant.", "significant"),
    ("With no correction needed, the decline is significant.", "significant"),
    ("Returnee numbers did not fall; the increase is statistically significant.", "significant"),
    ("Although not large, the increase is statistically significant (p=0.027).", "significant"),
    ("The difference between regions is not just visible but statistically significant (p=0.001).", "significant"),
    ("None of the tested trends is statistically significant.", "not significant"),
    ("Neither of the two tested trends is statistically significant after the Holm correction.", "not significant"),
    ("None of the four trends tested was statistically significant after the Holm correction.", "not significant"),
    ("Neither tested trend is statistically significant.", "not significant"),
    ("No trend was statistically significant.", "not significant"),
    ("Not one of the trends is statistically significant.", "not significant"),
    ("There is no statistically significant trend in any indicator.", "not significant"),
    ("The refugee trend is not significant, but the IDP trend is significant.", None),
    ("No regional data exist for refugees, but the refugee increase is significant.", "significant"),
    ("Test edilen eğilimlerin hiçbiri istatistiksel olarak anlamlı değildir.", "not significant"),
    ("Hiçbir eğilim istatistiksel olarak anlamlı değildir.", "not significant"),
])
def test_a_negation_counts_only_in_the_claims_own_clause(sentence, claim):
    assert _claim(sentence) == claim


# --- Round 3 review (I1, I2, I5): the Methods rule reads only this report's METHOD NOTES,
# allows a method named only to say it was not applied, and knows more heading forms. ---

_PREVIOUS_REPORT = ("\nWrite the report.\n\nCOMPARISON WITH THE PREVIOUS REPORT. previous report:\n"
                    "## Methods\n\nTrends were tested with Mann-Kendall; regions with Kruskal-Wallis; "
                    "correlations with Pearson; Holm correction across all 1 tests.")


def test_the_methods_rule_ignores_a_previous_report_after_the_notes():
    text = "## Methods\n\nRegional differences were tested with the Kruskal-Wallis test."
    out = verify_narrative(text, _findings(), ONE_TEST_CONTEXT + _PREVIOUS_REPORT, "en")
    assert out.removed == 1


@pytest.mark.parametrize("sentence,language,heading", [
    ("Because only one test was run, no Holm correction was applied.", "en", "Methods"),
    ("No multiple-comparison correction such as Holm's was needed, since a single test was run.", "en", "Methods"),
    ("Yalnızca bir test yapıldığı için Holm düzeltmesi uygulanmadı.", "tr", "Yöntem"),
])
def test_a_method_named_only_as_not_applied_stays(sentence, language, heading):
    assert _methods(sentence, language, heading).removed == 0


@pytest.mark.parametrize("heading", ["Methods Note", "Methodology Note", "Yöntem Notu", "Metodoloji",
                                     "YÖNTEM"])
def test_more_methods_headings_are_recognised(heading):
    assert _methods("Regional differences were tested with the Kruskal-Wallis test.", "en",
                    heading).removed == 1
