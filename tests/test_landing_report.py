"""Excerpt logic of scripts/generate_landing_report.py (no LLM, no DB)."""
from scripts.generate_landing_report import key_findings_excerpt

REPORT = """## Executive Summary
Health needs are severe [1].

## Key Findings
### Disease outbreaks
Cholera spread to 12 states in 2026 [2][3]. Partners scaled up vaccination. Measles cases rose in Darfur [1].

### Health facilities
Only 30% of facilities remain functional [4].

## Outlook
Funding gaps persist [2].
"""

SOURCES = [
    {"index": i, "title": f"Title {i}", "url": f"https://reliefweb.int/report/{i}",
     "date": f"2026-10-0{i}", "source": f"Org {i}"}
    for i in range(1, 5)
]


def test_takes_the_first_cited_sentences_of_key_findings_verbatim():
    out = key_findings_excerpt(REPORT, SOURCES)
    assert out["findings"] == [
        "Cholera spread to 12 states in 2026 [2][3].",
        "Measles cases rose in Darfur [1].",
    ]


def test_lists_only_the_sources_those_sentences_cite_in_citation_order():
    out = key_findings_excerpt(REPORT, SOURCES)
    assert [s["n"] for s in out["sources"]] == [2, 3, 1]
    assert out["sources"][0] == {"n": 2, "publisher": "Org 2", "title": "Title 2",
                                 "date": "2026-10-02", "url": "https://reliefweb.int/report/2"}


def test_returns_no_findings_without_a_key_findings_section():
    out = key_findings_excerpt("## Executive Summary\nA claim [1].", SOURCES)
    assert out == {"findings": [], "sources": []}
