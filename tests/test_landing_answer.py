"""Parsing logic of scripts/generate_landing_answer.py (no LLM, no DB)."""
from scripts.generate_landing_answer import parse_answer

SOURCES = [
    {"index": i, "title": f"Title {i}", "url": f"https://reliefweb.int/report/{i}",
     "date": f"2026-10-0{i}", "country": "Syrian Arab Republic", "source": f"Org {i}",
     "doctype": "report"}
    for i in range(1, 5)
]


def test_citations_become_cite_parts_without_the_space_before_them():
    out = parse_answer("Over 1 million refugees returned [1][3]. More followed [2].", SOURCES)
    assert out["parts"] == [
        {"text": "Over 1 million refugees returned"}, {"cite": 1}, {"cite": 3},
        {"text": ". More followed"}, {"cite": 2}, {"text": "."},
    ]


def test_grouped_citations_are_expanded():
    out = parse_answer("Returns rose [1, 2].", SOURCES)
    assert out["parts"] == [{"text": "Returns rose"}, {"cite": 1}, {"cite": 2}, {"text": "."}]


def test_bold_becomes_a_strong_part():
    out = parse_answer("In Syria, **1.2 million refugees** have returned [2].\n\n**Where:** Aleppo", SOURCES)
    assert out["parts"] == [
        {"text": "In Syria, "}, {"text": "1.2 million refugees", "strong": True},
        {"text": " have returned"}, {"cite": 2}, {"text": ".\n\n"},
        {"text": "Where:", "strong": True}, {"text": " Aleppo"},
    ]


def test_a_citation_inside_bold_text_is_still_a_cite_part():
    out = parse_answer("**1.2 million [2]** returned.", SOURCES)
    assert out["parts"] == [
        {"text": "1.2 million", "strong": True}, {"cite": 2}, {"text": " returned."},
    ]


def test_unknown_citation_numbers_are_dropped():
    out = parse_answer("Returns rose [9][1]. Then fell [7].", SOURCES)
    assert out["parts"] == [
        {"text": "Returns rose"}, {"cite": 1}, {"text": ". Then fell."},
    ]
    assert [s["n"] for s in out["sources"]] == [1]


def test_sources_are_the_cited_ones_in_number_order_with_publisher_and_country_meta():
    out = parse_answer("A [3]. B [1]. C [3].", SOURCES)
    assert out["sources"] == [
        {"n": 1, "title": "Title 1", "meta": "Org 1 · Syrian Arab Republic",
         "date": "2026-10-01", "url": "https://reliefweb.int/report/1"},
        {"n": 3, "title": "Title 3", "meta": "Org 3 · Syrian Arab Republic",
         "date": "2026-10-03", "url": "https://reliefweb.int/report/3"},
    ]


def test_text_is_kept_verbatim_apart_from_markers():
    text = "Aralık 2024'ten bu yana *  yaklaşık %41'i — Halep'e döndü [4]."
    out = parse_answer(text, SOURCES)
    assert "".join(p.get("text", "") for p in out["parts"]) == text.replace(" [4]", "")


def test_list_markers_at_line_start_become_list_item_parts():
    text = "Numbers:\n* **Refugees:** 1.8 million [1].\n- IDPs: 2 million [2].\n1. Third"
    out = parse_answer(text, SOURCES)
    assert out["parts"] == [
        {"text": "Numbers:\n"}, {"text": "* ", "list_item": True},
        {"text": "Refugees:", "strong": True}, {"text": " 1.8 million"}, {"cite": 1},
        {"text": ".\n"}, {"text": "- ", "list_item": True}, {"text": "IDPs: 2 million"},
        {"cite": 2}, {"text": ".\n"}, {"text": "1. ", "list_item": True}, {"text": "Third"},
    ]
    # Verbatim: the list marker text is kept, only flagged.
    joined = "".join(p.get("text", "") for p in out["parts"])
    assert joined == text.replace("**", "").replace(" [1]", "").replace(" [2]", "")


def test_a_star_inside_a_line_is_not_a_list_marker():
    out = parse_answer("Returns * rose [1].", SOURCES)
    assert out["parts"] == [{"text": "Returns * rose"}, {"cite": 1}, {"text": "."}]
