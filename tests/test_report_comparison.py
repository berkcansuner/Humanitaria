"""Report series, step 2: the comparison block a next-period report sends to the model.

The previous report's stored text goes to the model as *context for comparison*,
never as a source: its [n] markers point at the old report's source list, so they
are stripped, and the model is told not to cite it.
"""
from rag.report_service import (
    COMPARISON_HEADINGS, PREVIOUS_REPORT_MAX_CHARS, build_comparison_block,
)


def _prev(content="## Executive Summary\nNeeds rose to 2 million [1][2].", **kw):
    row = {"id": "r-prev", "title": "Sudan · All sectors · 2026-04-01 – 2026-06-30",
           "date_from": "2026-04-01", "date_to": "2026-06-30", "content": content}
    row.update(kw)
    return row


def test_block_names_previous_period_and_carries_its_text():
    block = build_comparison_block(_prev(), "en")
    assert "2026-04-01 to 2026-06-30" in block
    assert "Needs rose to 2 million" in block


def test_block_labels_previous_report_as_not_a_source():
    block = build_comparison_block(_prev(), "en")
    assert "NOT a source" in block
    assert "never cite it" in block.lower()


def test_block_strips_old_citation_markers():
    """Old [n] numbers refer to the previous report's sources; left in, the model
    could copy them and they would be renumbered onto unrelated current sources."""
    block = build_comparison_block(_prev("Needs rose [1][2], deaths fell [12]."), "en")
    assert "[1]" not in block and "[2]" not in block and "[12]" not in block
    assert "Needs rose, deaths fell." in block


def test_block_heading_follows_report_language():
    assert COMPARISON_HEADINGS["en"] in build_comparison_block(_prev(), "en")
    assert COMPARISON_HEADINGS["tr"] in build_comparison_block(_prev(), "tr")
    assert COMPARISON_HEADINGS["en"] not in build_comparison_block(_prev(), "tr")


def test_block_places_section_after_each_types_opening_section():
    assert "Executive Summary" in build_comparison_block(_prev(), "en", "situation")
    assert "Overview" in build_comparison_block(_prev(), "en", "indicator_monitoring")
    assert "'Context'" in build_comparison_block(_prev(), "en", "needs_assessment")
    assert "Executive Summary" in build_comparison_block(_prev(), "en", "technical_monitoring")


def test_block_truncates_long_previous_text():
    long = "x" * (PREVIOUS_REPORT_MAX_CHARS + 5000)
    block = build_comparison_block(_prev(long), "en")
    assert "x" * PREVIOUS_REPORT_MAX_CHARS in block
    assert "x" * (PREVIOUS_REPORT_MAX_CHARS + 1) not in block
    assert "truncated" in block


def test_document_types_cite_new_values_from_context():
    block = build_comparison_block(_prev(), "en", "situation")
    assert "cite" in block and "[n]" in block


def test_technical_type_does_not_ask_for_citations():
    """Technical reports have no [n] sources; new values come from the findings."""
    block = build_comparison_block(_prev(), "en", "technical_monitoring")
    assert "[n]" not in block
    assert "findings" in block.lower()


def test_missing_period_is_said_plainly():
    block = build_comparison_block(_prev(date_from=None, date_to=None), "en")
    assert "unspecified" in block


def test_block_names_the_new_period_when_given():
    """Without the new period the model cannot tell a new event from an old one
    that a current document happens to mention."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "2026-07-15 to 2026-11-15" in block


def test_block_requires_like_with_like_comparison():
    """Live check 2026-11-15: an annual report for 2025 and an update on a 2025
    earthquake (both published in the new period) were set beside the previous
    report's 2026 figures as if they were changes."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "LIKE WITH LIKE" in block
    assert "not its publication date" in block
    assert "earlier year or event is background, not a change" in block


def test_block_closes_the_not_covered_before_loophole():
    """Live check 2 (2026-11-15): the model kept an August 2025 earthquake in the
    section because "the previous report did not cover it". First mention in this
    series does not make an older event new."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "does NOT make it new" in block
    assert "dated before 2026-07-15" in block


def test_block_forbids_comparing_different_reference_periods():
    """Live check 2: a 2025 calendar-year returns figure was compared with the
    previous report's "3.4 million over sixteen months"."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "different reference periods" in block


def test_block_keeps_undated_figures_out_of_changes():
    """Live check 4 (2026-11-15): "36 confirmed polio cases" (the source gives no
    period) was called "a new specific health concern"."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "gives no reference date" in block


def test_block_says_a_newly_quantified_figure_is_not_a_change():
    """Live check 4: "per capita income has dropped by 5.6 per cent" (no period in
    the source) was listed as a change because it was now given as a number."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "not a change in the situation" in block


def test_block_requires_the_no_longer_reported_part():
    """Live checks 3-4: what dropped out of the reporting appeared in one run and
    not the next."""
    block = build_comparison_block(_prev(), "en", date_from="2026-07-15", date_to="2026-11-15")
    assert "Always say what is no longer reported" in block
