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


def test_takes_cited_sentences_with_figures_from_distinct_sources_verbatim():
    out = key_findings_excerpt(REPORT, SOURCES)
    assert out["findings"] == [
        "Cholera spread to 12 states in 2026 [2][3].",
        "Only 30% of facilities remain functional [4].",
    ]


def test_lists_only_the_sources_those_sentences_cite_in_citation_order():
    out = key_findings_excerpt(REPORT, SOURCES)
    assert [s["n"] for s in out["sources"]] == [2, 3, 4]
    assert out["sources"][0] == {"n": 2, "publisher": "Org 2", "title": "Title 2",
                                 "date": "2026-10-02", "url": "https://reliefweb.int/report/2"}


def test_returns_no_findings_without_a_key_findings_section():
    out = key_findings_excerpt("## Executive Summary\nA claim [1].", SOURCES)
    assert out == {"findings": [], "sources": []}


TR_REPORT = """## Yönetici Özeti
Koruma ihtiyaçları ağırdır [1].

## Temel Bulgular
### Geri dönüşler
Aralık 2024'ten bu yana 1,2 milyon mülteci döndü [2]. İadeler Halep'te yoğunlaştı [3]. Ülke içinde yerinden edilmiş kişiler de döndü [1].

## Görünüm
Fonlama açığı sürüyor [2].
"""


def test_a_translated_report_takes_its_second_section_as_key_findings():
    # The report prompt fixes the order (Executive Summary, Key Findings, Outlook) and
    # translates every heading, so a Turkish report has no "Key Findings" heading.
    out = key_findings_excerpt(TR_REPORT, SOURCES)
    assert out["findings"] == [
        "Aralık 2024'ten bu yana 1,2 milyon mülteci döndü [2].",
        "İadeler Halep'te yoğunlaştı [3].",
    ]
    assert [s["n"] for s in out["sources"]] == [2, 3]


PICK_REPORT = """## Executive Summary
Overview [1].

## Key Findings
### Returns
More than 1.8 million refugees returned since December 2024 [1]. Needs remain high [1]. Programming follows the national vision [2]. In May 2026, 104 incidents were recorded [3]. Later, 40 people died [4].

## Outlook
Funding gaps persist [2].
"""


def test_second_finding_is_the_first_with_a_figure_from_a_new_source():
    out = key_findings_excerpt(PICK_REPORT, SOURCES)
    assert out["findings"] == [
        "More than 1.8 million refugees returned since December 2024 [1].",
        "In May 2026, 104 incidents were recorded [3].",
    ]
    assert [s["n"] for s in out["sources"]] == [1, 3]


def test_a_new_source_without_a_figure_comes_before_a_repeated_source():
    report = "## Key Findings\nA 5% rise [1]. Still 3 left [1]. Partners responded [2].\n"
    assert key_findings_excerpt(report, SOURCES)["findings"] == ["A 5% rise [1].",
                                                               "Partners responded [2]."]


def test_without_a_new_source_the_next_cited_sentence_is_taken():
    report = "## Key Findings\nA 5% rise [1]. Then a fall [1].\n"
    assert key_findings_excerpt(report, SOURCES)["findings"] == ["A 5% rise [1].", "Then a fall [1]."]


def _run_main(monkeypatch, tmp_path, *args):
    """main() with --reuse on a saved raw file: no model call, output in tmp_path."""
    import json
    import sys

    import scripts.generate_landing_report as script
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"generated": "2026-11-18", "date_from": "2025-11-18",
                               "date_to": "2026-11-18", "content": PICK_REPORT,
                               "sources": SOURCES}), encoding="utf-8")
    monkeypatch.setattr(script, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["generate_landing_report.py", "--raw", str(raw),
                                      "--reuse", *args])
    script.main()
    return sorted(p.name for p in tmp_path.glob("meReport*.json"))


def test_default_run_writes_the_english_syria_sample_the_landing_imports(monkeypatch, tmp_path):
    import json
    assert _run_main(monkeypatch, tmp_path) == ["meReport.en.json"]
    out = json.loads((tmp_path / "meReport.en.json").read_text(encoding="utf-8"))
    assert (out["country"], out["sector"], out["language"]) == (
        "Syrian Arab Republic", "Protection and Human Rights", "en")


def test_language_run_writes_its_own_file(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, "--language", "tr") == ["meReport.tr.json"]
