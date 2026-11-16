"""Pure helpers of scripts/build_eval_labels.py (judge-output parsing, candidate pooling)."""
from langchain_core.documents import Document

from scripts.build_eval_labels import parse_indices, pool_candidates


def test_parse_indices_reads_a_bare_array():
    assert parse_indices("[0, 2, 5]") == [0, 2, 5]


def test_parse_indices_tolerates_prose_and_fences():
    assert parse_indices("Relevant:\n```json\n[1, 3]\n```") == [1, 3]


def test_parse_indices_returns_empty_on_garbage():
    assert parse_indices("none of them") == []
    assert parse_indices('{"relevant": [1]}') == []


def _doc(doc_id, title="T"):
    return Document(page_content="body", metadata={"doc_id": doc_id, "title": title, "date": "2026-10-01"})


def test_pool_dedupes_by_doc_id_across_lists_in_order():
    pool = pool_candidates([[_doc("a"), _doc("b"), _doc("a")], [_doc("b"), _doc("c")]])
    assert [c["doc_id"] for c in pool] == ["a", "b", "c"]


def test_pool_skips_chunks_without_doc_id():
    pool = pool_candidates([[Document(page_content="x", metadata={}), _doc("a")]])
    assert [c["doc_id"] for c in pool] == ["a"]


def test_judge_holes_judges_only_unseen_docs_and_records_them():
    from unittest.mock import patch
    from scripts.eval_rag import _judge_holes

    entry = {"query": "q", "relevant_doc_ids": ["a"], "judged_doc_ids": ["a", "b"]}
    seen_batches = []

    def fake_judge(judge, query, batch):
        seen_batches.append([c["doc_id"] for c in batch])
        return [1]   # second hole ("d") is relevant

    with patch("scripts.build_eval_labels.judge_relevant", fake_judge):
        n = _judge_holes(entry, [_doc("a"), _doc("c"), _doc("b"), _doc("d")], judge=None)
    assert n == 2
    assert seen_batches == [["c", "d"]]
    assert entry["relevant_doc_ids"] == ["a", "d"]
    assert set(entry["judged_doc_ids"]) == {"a", "b", "c", "d"}


def test_judge_holes_skips_the_judge_when_nothing_is_new():
    from scripts.eval_rag import _judge_holes
    entry = {"query": "q", "relevant_doc_ids": [], "judged_doc_ids": ["a"]}
    assert _judge_holes(entry, [_doc("a")], judge=None) == 0
