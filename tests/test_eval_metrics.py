"""Tests for retrieval ranking metrics (rag/eval_metrics.py)."""
import math

import pytest

from rag.eval_metrics import recall_at_k, reciprocal_rank, ndcg_at_k


RANKED = ["a", "b", "c", "d", "e"]
RELEVANT = {"b", "d"}


def test_recall_at_k_partial():
    assert recall_at_k(RANKED, RELEVANT, 3) == pytest.approx(0.5)  # only b in top-3


def test_recall_at_k_full():
    assert recall_at_k(RANKED, RELEVANT, 5) == pytest.approx(1.0)


def test_recall_at_k_zero_when_none_in_topk():
    assert recall_at_k(RANKED, RELEVANT, 1) == pytest.approx(0.0)


def test_recall_at_k_no_relevant_is_zero():
    assert recall_at_k(RANKED, set(), 5) == 0.0


def test_reciprocal_rank_first_relevant_at_rank_2():
    assert reciprocal_rank(RANKED, RELEVANT) == pytest.approx(0.5)


def test_reciprocal_rank_zero_when_none_found():
    assert reciprocal_rank(RANKED, {"z"}) == 0.0


def test_reciprocal_rank_one_when_first_is_relevant():
    assert reciprocal_rank(["b", "a"], RELEVANT) == pytest.approx(1.0)


def test_ndcg_at_k_perfect_ranking_is_one():
    assert ndcg_at_k(["a", "b", "c"], {"a", "b"}, 3) == pytest.approx(1.0)


def test_ndcg_at_k_zero_when_none_found():
    assert ndcg_at_k(RANKED, {"z"}, 5) == 0.0


def test_ndcg_at_k_matches_manual_dcg():
    # relevant at ranks 2 and 4: DCG = 1/log2(3) + 1/log2(5)
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)  # 2 relevant, ideal at ranks 1,2
    assert ndcg_at_k(RANKED, RELEVANT, 5) == pytest.approx(dcg / idcg)
