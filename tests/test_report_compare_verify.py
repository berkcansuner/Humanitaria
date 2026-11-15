"""Report series: the narrow check on "What changed" after generation.

Five live checks (2026-11-15) showed the main report prompt applying the
comparison rules unevenly from run to run (an August 2025 earthquake presented as
"a significant new event" in one run, gone in the next). A second, single-purpose
call reads only the section's numbered sentences and returns the numbers to drop;
the code does the dropping, so the check can never add or reword text, and the
[n] markers of kept sentences stay as they were.
"""
import anyio

from rag.report_compare import (
    NO_CONFIRMED_CHANGE, build_check_prompt, remove_sentences, split_sentences,
    verify_comparison,
)

HEADING = "What changed since the last report"
SECTION = (
    "Needs remain at 21.9 million in 2026, unchanged [1]. A significant new event is "
    "the 31 August 2025 earthquake [2].\n\n"
    "Shipments stranded in Pakistan since October 2025 have now arrived [3]. Per capita "
    "income dropped by 5.6 percent [4]."
)
CONTENT = (
    "## Executive Summary\nThe crisis continues [1].\n\n"
    f"## {HEADING}\n{SECTION}\n\n"
    "## Key Findings\n### Health\nOutbreaks continued [2].\n"
)


def _run(content=CONTENT, checker=None, **kw):
    kw.setdefault("heading", HEADING)
    kw.setdefault("date_from", "2026-07-15")
    kw.setdefault("date_to", "2026-11-15")
    kw.setdefault("language", "en")
    return anyio.run(lambda: verify_comparison(content, checker=checker, **kw))


def _checker(result, seen=None):
    async def check(prompt):
        if seen is not None:
            seen.append(prompt)
        if isinstance(result, Exception):
            raise result
        return result
    return check


# --- sentence handling --------------------------------------------------------

def test_split_keeps_paragraphs_and_decimals():
    assert split_sentences("A rose to 5.6 percent [1]. B fell [2].\n\nC held.") == [
        (0, "A rose to 5.6 percent [1]."), (0, "B fell [2]."), (1, "C held."),
    ]


def test_remove_drops_sentences_and_empty_paragraphs():
    body = "A [1]. B [2].\n\nC [3]."
    assert remove_sentences(body, {2}, "en") == "A [1].\n\nC [3]."
    assert remove_sentences(body, {3}, "en") == "A [1]. B [2]."


def test_remove_everything_leaves_one_plain_sentence():
    assert remove_sentences("A [1]. B [2].", {1, 2}, "en") == NO_CONFIRMED_CHANGE["en"]
    assert remove_sentences("A [1].", {1}, "tr") == NO_CONFIRMED_CHANGE["tr"]


# --- the check ----------------------------------------------------------------

def test_check_drops_the_flagged_sentences_only_in_the_section():
    out = _run(checker=_checker({"remove": [2, 4], "why": {"2": "2025 event"}}))
    assert "31 August 2025 earthquake" not in out
    assert "5.6 percent" not in out
    assert "Shipments stranded in Pakistan since October 2025 have now arrived [3]." in out
    assert "Needs remain at 21.9 million in 2026, unchanged [1]." in out
    # the rest of the report is untouched
    assert out.startswith("## Executive Summary\nThe crisis continues [1].\n\n")
    assert out.endswith("## Key Findings\n### Health\nOutbreaks continued [2].\n")


def test_check_prompt_numbers_the_sentences_and_names_the_period():
    seen = []
    _run(checker=_checker({"remove": []}, seen))
    prompt = seen[0]
    assert "2026-07-15 to 2026-11-15" in prompt
    assert "2. A significant new event is the 31 August 2025 earthquake [2]." in prompt
    assert "4. Per capita income dropped by 5.6 percent [4]." in prompt


def test_check_prompt_keeps_real_changes_and_no_longer_reported():
    prompt = build_check_prompt(["x."], "2026-07-15", "2026-11-15")
    assert "dated before 2026-07-15" in prompt
    assert "no longer reported" in prompt
    assert "stranded" in prompt  # an earlier start with a change inside the period stays


def test_nothing_flagged_leaves_content_identical():
    assert _run(checker=_checker({"remove": []})) == CONTENT


def test_failed_check_never_blocks_the_report():
    assert _run(checker=_checker(RuntimeError("503 high demand"))) == CONTENT


def test_malformed_answers_are_ignored_safely():
    assert _run(checker=_checker({"nope": 1})) == CONTENT
    assert _run(checker=_checker(None)) == CONTENT
    # out-of-range and non-numeric ids are skipped, valid ones applied
    out = _run(checker=_checker({"remove": [99, "x", "2", 0]}))
    assert "earthquake" not in out and "Shipments stranded" in out


def test_report_without_the_section_skips_the_check():
    seen = []
    content = "## Executive Summary\nText [1].\n"
    assert _run(content=content, checker=_checker({"remove": [1]}, seen)) == content
    assert seen == []


def test_section_at_the_end_of_the_report():
    content = f"## Executive Summary\nX [1].\n\n## {HEADING}\nA [1]. B [2].\n"
    out = _run(content=content, checker=_checker({"remove": [2]}))
    assert out == f"## Executive Summary\nX [1].\n\n## {HEADING}\nA [1].\n"


def test_turkish_heading():
    heading = "Son rapordan bu yana neler değişti"
    content = f"## Yönetici Özeti\nX [1].\n\n## {heading}\nA [1]. B [2].\n\n## Bulgular\nY.\n"
    out = _run(content=content, heading=heading, language="tr",
               checker=_checker({"remove": [1, 2]}))
    assert f"## {heading}\n{NO_CONFIRMED_CHANGE['tr']}\n\n## Bulgular" in out
