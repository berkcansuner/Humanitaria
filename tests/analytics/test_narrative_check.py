"""The technical report's narrative is checked against the code-computed findings:
a sentence with a number the findings do not contain, or a significance claim that
contradicts the code's verdict, is removed (the prompt alone could not enforce it)."""
from analytics.narrative_check import verify_narrative
from analytics.technical_report import Findings, ReportSection

TREND_H = "Ülke içinde yerinden edilmiş kişiler (IDP) — Trend Analizi"
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
