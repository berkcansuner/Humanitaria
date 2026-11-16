"""Report retrieval ranking (rag.report_service._rank_for_report).

Eval 2026-11-16 (6 countries × situation/indicator, May–Nov 2026): the latest
document of each originator organisation (OCHA, IOM, UNHCR, WFP, UNICEF, WHO,
IPC, FAO, clusters...) reached the report context 9% of the time; Yemen's indicator
table missed IOM's 340,000 update. Relevance 0.6 + recency in the window 0.2 +
originator 0.2, at most 2 documents per organisation: 27%, originator share
54% -> 79%, mean relevance 0.833 -> 0.844."""
from langchain_core.documents import Document

from rag.report_service import _cap_keeping_newest_originators, _rank_for_report

OCHA = "UN Office for the Coordination of Humanitarian Affairs"


def _d(i, source, date, rel):
    return Document(page_content=f"c{i}", metadata={"doc_id": str(i), "source": source,
                                                    "date": date, "_relevance_score": rel})


def _ids(docs):
    return [d.metadata["doc_id"] for d in docs]


def test_recent_originator_beats_an_older_equally_relevant_news_item():
    docs = [_d(1, "Some NGO", "2026-06-01", 0.80), _d(2, OCHA, "2026-11-10", 0.80)]
    assert _ids(_rank_for_report(docs, "2026-05-01", "2026-11-16", 1)) == ["2"]


def test_relevance_still_dominates():
    docs = [_d(1, OCHA, "2026-11-15", 0.10), _d(2, "Some NGO", "2026-11-01", 0.95)]
    assert _ids(_rank_for_report(docs, "2026-05-01", "2026-11-16", 1)) == ["2"]


def test_at_most_two_per_organisation_while_others_remain():
    docs = [_d(i, OCHA, "2026-11-10", 0.9) for i in range(1, 4)] + [_d(4, "Some NGO", "2026-07-01", 0.5)]
    out = _ids(_rank_for_report(docs, "2026-05-01", "2026-11-16", 3))
    assert out[:2] == ["1", "2"] and "4" in out and "3" not in out


def test_the_cap_never_leaves_slots_empty():
    docs = [_d(i, OCHA, "2026-11-10", 0.9) for i in range(1, 4)]
    assert len(_rank_for_report(docs, "2026-05-01", "2026-11-16", 3)) == 3


def test_no_window_and_no_scores_still_rank():
    # No dates chosen, and a failed rerank (no scores): recency and origin still order.
    docs = [Document(page_content="a", metadata={"doc_id": "1", "source": "Some NGO", "date": "2026-01-01"}),
            Document(page_content="b", metadata={"doc_id": "2", "source": OCHA, "date": "2026-11-01"})]
    assert _ids(_rank_for_report(docs, None, None, 2)) == ["2", "1"]


IOM = "International Organization for Migration"


def test_cap_keeps_an_originators_newest_document_below_the_cut():
    # Yemen 2026-11-17: IOM's 340,000 update sat at dense rank 101 of a 100-document cap.
    docs = [_d(1, "Some NGO", "2026-11-01", 0), _d(2, IOM, "2026-10-01", 0),
            _d(3, "Other NGO", "2026-11-02", 0), _d(4, IOM, "2026-11-13", 0)]
    assert _ids(_cap_keeping_newest_originators(docs, 3)) == ["1", "2", "4"]


def test_cap_reserves_nothing_for_non_originators_or_when_the_pool_fits():
    docs = [_d(1, OCHA, "2026-11-01", 0), _d(2, "Some NGO", "2026-11-15", 0),
            _d(3, "Other NGO", "2026-11-16", 0)]
    assert _ids(_cap_keeping_newest_originators(docs, 2)) == ["1", "2"]
    assert _ids(_cap_keeping_newest_originators(docs, 5)) == ["1", "2", "3"]
