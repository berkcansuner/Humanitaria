"""The one model-written section of a technical report ("What changed since the last
report") is checked by presence rules; everything else in the report is written in code."""
import logging

import pytest

from analytics.narrative_check import check_comparison
from tests.analytics import samples

H = "What changed since the last report"
ALLOWED = ("Refugees (people): latest value 2.67 million people (2025), against 5.66 million "
           "people in 2022. Country: Afghanistan. --- PREVIOUS REPORT (2025-01-01 to 2025-06-30) "
           "--- Refugees stood at 3.10 million people. Herat hosted 443,000 displaced people.")


def _check(text, language="en", findings=None, allowed=ALLOWED, heading=H):
    return check_comparison(text, findings or samples.findings(samples.trend()), allowed,
                            language, heading)


def _kept(sentence, language="en", **kwargs):
    heading = kwargs.pop("heading", "Son rapordan bu yana neler değişti" if language == "tr" else H)
    return _check(f"## {heading}\n\n{sentence}", language, heading=heading, **kwargs).content is not None


@pytest.mark.parametrize("sentence", [
    "Refugees went from 3.10 million people in the previous period to 2.67 million people in 2025.",
    "The refugee figure fell from 3.10 million to 2.67 million.",
    "Returnees are new to the series: the previous report did not cover them.",
    "Nothing comparable changed for Herat, where the previous report gave 443,000 displaced people.",
])
def test_a_comparison_of_given_figures_is_kept(sentence):
    assert _kept(sentence)


@pytest.mark.parametrize("sentence", [
    "Refugees fell to 2.9 million people.",                               # a number not given
    "Refugees fell by 430,000 people.",                                   # a computed difference
    "Refugees fell by 14 percent.",
    "The decline is statistically significant.",
    "The decline is not significant.",
    "The Mann-Kendall test shows a decline.",
    "The fall from 3.10 million to 2.67 million is proven beyond doubt.",
    "The fall may simply be noise.",
    "Refugee numbers have nearly halved since the previous report.",
    "Most of the change happened in Herat.",
    "This is a record low.",
    "The fall is driven by large-scale returns.",
    "The rise in returns explains the fall from 3.10 million to 2.67 million.",
    "Many refugees moved on to Pakistan.",                                # a name not given
])
def test_what_the_comparison_must_not_say_is_dropped(sentence):
    assert not _kept(sentence)


@pytest.mark.parametrize("sentence,keep", [
    ("Mülteci sayısı önceki dönemdeki 3,10 milyondan 2,67 milyona indi.", True),
    ("Önceki rapor geri dönenleri kapsamıyordu; bu gösterge seride yenidir.", True),
    ("Mülteci sayısı 2,9 milyona indi.", False),
    ("Azalış istatistiksel olarak anlamlıdır.", False),
    ("Düşüş kesindir.", False),
    ("Mülteci sayısı yarı yarıya azaldı.", False),
    ("Azalışın nedeni kitlesel geri dönüşlerdir.", False),
])
def test_turkish_comparison_sentences(sentence, keep):
    assert _kept(sentence, "tr") is keep


def test_a_total_is_never_claimed_in_a_report_of_plan_lines():
    lines = samples.findings(samples.trend(), note_items=[{"kind": "plan_line", "name": "Protection"}])
    assert not _kept("The overall refugee figure is 2.67 million people.", findings=lines)
    assert not _kept("Planın toplam rakamı 2,67 milyon kişidir.", "tr", findings=lines)
    assert _kept("Overall, the refugee figure is 2.67 million people.")       # no plan lines here


def test_only_the_comparison_section_is_used_and_sentences_are_judged_one_by_one(caplog):
    caplog.set_level(logging.INFO, logger="analytics.narrative_check")
    text = ("## Executive Summary\n\nNeeds exploded to 99 million.\n\n"
            f"## **{H.upper()}**\n\nRefugees went from 3.10 million to 2.67 million people. "
            "IDPs reached 9.9 million.\n\nReturnees are new to the series.\n\n"
            "## Methods\n\nA Pearson test was run.")
    res = check_comparison(text, samples.findings(samples.trend()), ALLOWED, "en", H,
                           label="Afghanistan / All sectors")
    assert res.content == ("Refugees went from 3.10 million to 2.67 million people.\n\n"
                           "Returnees are new to the series.")
    assert res.removed == 1
    assert any("Afghanistan / All sectors" in r.getMessage() and "9.9" in r.getMessage()
               for r in caplog.records)


def test_text_without_any_heading_is_read_as_the_section_and_an_empty_one_is_none():
    assert _check("Refugees went from 3.10 million to 2.67 million people.").content == (
        "Refugees went from 3.10 million to 2.67 million people.")
    assert _check(f"## {H}\n\nRefugees fell to 1.5 million.").content is None
    assert _check("## Another heading\n\nRefugees fell from 3.10 million.").content is None
