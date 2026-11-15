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
