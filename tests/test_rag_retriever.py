import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from rag.retriever import (
    PgVectorRetriever, build_retriever, build_sql_filter,
    dedupe_by_document, rerank_by_relevance, rerank_text,
)
from config import get_settings


class TestApplyDateFilter:
    """Defensive post-retrieval date filter (rag.retriever.apply_date_filter).

    SQL already applies a numeric date_ts range; this is the in-Python backstop. Comparison is lexicographic on YYYY-MM-DD strings."""

    def _doc(self, date):
        meta = {"date": date} if date is not None else {}
        return Document(page_content="x", metadata=meta)

    def test_none_filter_returns_all_unchanged(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01"), self._doc("2020-01-01")]
        assert apply_date_filter(docs, None) == docs

    def test_non_dict_filter_returns_all(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01")]
        assert apply_date_filter(docs, "2024-01-01") == docs  # defensive: not a dict

    def test_empty_or_missing_gte_returns_all(self):
        from rag.retriever import apply_date_filter
        docs = [self._doc("2024-01-01"), self._doc("2019-05-05")]
        assert apply_date_filter(docs, {"$gte": ""}) == docs
        assert apply_date_filter(docs, {}) == docs

    def test_gte_drops_older_keeps_boundary_and_newer(self):
        from rag.retriever import apply_date_filter
        older, boundary, newer = self._doc("2023-12-31"), self._doc("2024-01-01"), self._doc("2024-06-15")
        out = apply_date_filter([older, boundary, newer], {"$gte": "2024-01-01"})
        assert out == [boundary, newer]  # boundary is inclusive ($gte), older is dropped

    def test_doc_missing_date_is_dropped_when_gte_set(self):
        from rag.retriever import apply_date_filter
        dated, undated = self._doc("2025-01-01"), self._doc(None)
        out = apply_date_filter([dated, undated], {"$gte": "2024-01-01"})
        assert out == [dated]  # no 'date' → treated as "0000-00-00" → below the floor


class TestRetriever:
    def test_build_retriever_defaults(self):
        settings = get_settings()
        r = build_retriever(filter={"country": "Iran"})
        assert isinstance(r, PgVectorRetriever)
        assert r.filters == {"country": "Iran"}
        assert (r.k, r.fetch_k) == (settings.TOP_K_RETRIEVAL, settings.MMR_FETCH_K)

    def test_build_retriever_no_filter(self):
        assert build_retriever().filters is None

    def test_build_retriever_k_override(self):
        # Caller raises k to fetch a larger candidate pool; fetch_k must stay
        # strictly larger so MMR has headroom to diversify.
        r = build_retriever(k=20)
        assert r.k == 20 and r.fetch_k >= 20 * 3

    def test_build_retriever_date_filter_widens_pool(self):
        # A date filter thins the pool in Python afterwards, so fetch even more.
        dated = build_retriever(filter={"date": {"$gte": "2024-01-01"}}, k=20).fetch_k
        assert dated > build_retriever(k=20).fetch_k

    def test_build_retriever_fetch_k_capped_for_wide_k(self):
        # An indicator report's wide pool (candidate_k 64) with a date filter would be
        # 64*12 = 768; MMR over that many on a constrained CPU blew the request timeout.
        fetch_k = build_retriever(filter={"date": {"$gte": "2024-01-01"}}, k=64).fetch_k
        assert fetch_k == get_settings().MMR_FETCH_K_CAP

    def test_ainvoke_runs_the_search_with_the_retriever_settings(self):
        import asyncio
        doc = Document(page_content="x", metadata={"doc_id": "a"})
        with patch("rag.retriever.search", return_value=[doc]) as mock_search:
            r = build_retriever(filter={"country": "Yemen"}, k=7)
            assert asyncio.run(r.ainvoke("food")) == [doc]
        mock_search.assert_called_once_with("food", {"country": "Yemen"}, 7, r.fetch_k, None)

    def test_build_retriever_lambda_override_reaches_the_search(self):
        # The chat pipeline uses its own MMR lambda (CHAT_MMR_LAMBDA); reports keep MMR_LAMBDA.
        import asyncio
        assert build_retriever().lambda_mult is None
        with patch("rag.retriever.search", return_value=[]) as mock_search:
            r = build_retriever(k=7, lambda_mult=0.7)
            asyncio.run(r.ainvoke("food"))
        mock_search.assert_called_once_with("food", None, 7, r.fetch_k, 0.7)

    @pytest.mark.parametrize("override, expected", [(None, "settings"), (0.9, 0.9)])
    def test_search_uses_the_lambda_override_else_the_setting(self, override, expected):
        from rag import retriever
        rows = [MagicMock(dist=0.1 * i, emb="[1, 0]", content="c", metadata={"doc_id": str(i)})
                for i in range(2)]   # k < rows, so MMR runs
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows
        conn.__enter__.return_value = conn
        with patch.object(retriever, "get_embeddings") as emb,              patch.object(retriever, "connect", return_value=conn),              patch.object(retriever, "maximal_marginal_relevance", return_value=[0]) as mmr:
            emb.return_value.embed_query.return_value = [1.0, 0.0]
            retriever.search("q", None, 1, 1, override)
        want = get_settings().MMR_LAMBDA if expected == "settings" else expected
        assert mmr.call_args.kwargs["lambda_mult"] == want


class TestSqlFilter:
    def test_empty(self):
        assert build_sql_filter({}) == ([], {})
        assert build_sql_filter(None) == ([], {})

    def test_country_alias_matches_both_names(self):
        clauses, params = build_sql_filter({"country": "Iran"})
        assert clauses == ["country = ANY(:countries)"]
        assert params == {"countries": ["Iran", "Iran (Islamic Republic of)"]}

    def test_country_without_alias(self):
        assert build_sql_filter({"country": "Yemen"})[1] == {"countries": ["Yemen"]}

    def test_date_becomes_numeric_date_ts_range(self):
        clauses, params = build_sql_filter({"date": {"$gte": "2024-01-01", "$lte": "2024-06-30"}})
        assert clauses == ["date_ts >= :date_from", "date_ts <= :date_to"]
        assert params == {"date_from": 20240101, "date_to": 20240630}

    def test_theme_matches_primary_theme_or_theme_list(self):
        clauses, params = build_sql_filter({"theme": "Health"})
        assert clauses == ["(theme = :theme OR :theme = ANY(themes))"]
        assert params == {"theme": "Health"}

    def test_equality_columns(self):
        clauses, params = build_sql_filter({"doctype": "report", "source": "OCHA", "format": "News"})
        assert clauses == ["doctype = :doctype", "source = :source", "format = :format"]
        assert params == {"doctype": "report", "source": "OCHA", "format": "News"}

    def test_unknown_keys_and_non_string_values_never_reach_sql(self):
        # Column names come only from the whitelist; a hostile key is dropped.
        clauses, params = build_sql_filter({"country; DROP TABLE chunks": "x", "source": ["a"], "theme": ""})
        assert clauses == [] and params == {}


def _doc(doc_id, content="text", url=None):
    meta = {"doc_id": doc_id}
    if url is not None:
        meta["url"] = url
    return Document(page_content=content, metadata=meta)


class TestDedupeByDocument:
    def test_keeps_first_chunk_per_document(self):
        docs = [_doc("a", "chunk1"), _doc("a", "chunk2"), _doc("b", "chunk3")]
        out = dedupe_by_document(docs)
        assert len(out) == 2
        assert out[0].page_content == "chunk1"  # highest-ranked chunk of "a" kept
        assert out[1].metadata["doc_id"] == "b"

    def test_falls_back_to_url_when_no_doc_id(self):
        d1 = Document(page_content="c1", metadata={"url": "u1"})
        d2 = Document(page_content="c2", metadata={"url": "u1"})
        out = dedupe_by_document([d1, d2])
        assert len(out) == 1

    def test_empty_list(self):
        assert dedupe_by_document([]) == []


class TestRerankByRelevance:
    def test_noop_when_disabled(self):
        s = MagicMock(RERANK_ENABLED=False)
        docs = [_doc("a"), _doc("b")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=5)
        assert out == docs

    def test_noop_when_single_doc(self):
        s = MagicMock(RERANK_ENABLED=True)
        docs = [_doc("a")]
        with patch("rag.retriever.get_settings", return_value=s):
            out = rerank_by_relevance("q", docs, top_n=5)
        assert out == docs

    def test_reorders_by_pinecone_result(self):
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        # Pinecone returns indices in relevance order: c, a
        result = MagicMock()
        result.data = [MagicMock(index=2), MagicMock(index=0)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert [d.metadata["doc_id"] for d in out] == ["c", "a"]
        client.inference.rerank.assert_called_once()

    def test_falls_back_to_original_order_on_error(self):
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b"), _doc("c")]
        client = MagicMock()
        client.inference.rerank.side_effect = RuntimeError("network down")
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs[:2]

    def test_passes_truncate_end_to_reranker(self):
        # bge-reranker-v2-m3 rejects query+document pairs over 1024 tokens, and our
        # chunks can exceed that. Pinecone truncates long pairs when asked, so the
        # rerank call must pass parameters={"truncate": "END"} or it 400s and the
        # relevance signal is silently lost to the MMR fallback.
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b")]
        result = MagicMock()
        result.data = [MagicMock(index=0), MagicMock(index=1)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            rerank_by_relevance("q", docs, top_n=2)
        assert client.inference.rerank.call_args.kwargs.get("parameters") == {"truncate": "END"}

    def test_attaches_relevance_score_to_metadata(self):
        # The Pinecone relevance score is attached so rerank_by_recency can blend
        # it with recency instead of using the steep position-based fallback.
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        docs = [_doc("a"), _doc("b")]
        result = MagicMock()
        result.data = [MagicMock(index=1, score=0.91), MagicMock(index=0, score=0.42)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert [d.metadata["doc_id"] for d in out] == ["b", "a"]
        assert out[0].metadata["_relevance_score"] == 0.91
        assert out[1].metadata["_relevance_score"] == 0.42

    def test_scores_the_title_with_the_chunk(self):
        # A chunk alone often lacks the country, agency or report type a query names;
        # its document's title carries them. Untitled chunks are sent as they are.
        s = MagicMock(RERANK_ENABLED=True, RERANK_MODEL="bge-reranker-v2-m3")
        titled = Document(page_content="Cholera cases rose.", metadata={
            "doc_id": "a", "title": "Sudan: Cholera Situation Report No. 12"})
        untitled = Document(page_content="Rains continue.", metadata={"doc_id": "b"})
        result = MagicMock()
        result.data = [MagicMock(index=0, score=0.9), MagicMock(index=1, score=0.1)]
        client = MagicMock()
        client.inference.rerank.return_value = result
        with patch("rag.retriever.get_settings", return_value=s), \
             patch("rag.retriever._get_pinecone_client", return_value=client):
            rerank_by_relevance("q", [titled, untitled], top_n=2)
        assert client.inference.rerank.call_args.kwargs["documents"] == [
            "Sudan: Cholera Situation Report No. 12\n\nCholera cases rose.", "Rains continue."]
        assert rerank_text(untitled) == "Rains continue."


def test_search_skips_mmr_when_every_candidate_is_kept():
    # Report retrieval keeps the whole dense pool (k == fetch_k): MMR would select every
    # row anyway, at O(k^2) vector work; the dense order is returned instead.
    from rag import retriever
    rows = [MagicMock(dist=0.1 * i, emb="[1, 0]", content=f"c{i}", metadata={"doc_id": str(i)})
            for i in range(3)]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    conn.__enter__.return_value = conn
    with patch.object(retriever, "get_embeddings") as emb, \
         patch.object(retriever, "connect", return_value=conn), \
         patch.object(retriever, "maximal_marginal_relevance") as mmr:
        emb.return_value.embed_query.return_value = [1.0, 0.0]
        docs = retriever.search("q", None, 3, 3)
    mmr.assert_not_called()
    assert [d.metadata["doc_id"] for d in docs] == ["0", "1", "2"]


class TestVoyageRerank:
    """RERANK_PROVIDER=voyage: Voyage's hosted reranker over plain HTTPS (no SDK)."""

    @staticmethod
    def _settings(**kw):
        base = dict(RERANK_ENABLED=True, RERANK_PROVIDER="voyage", VOYAGE_API_KEY="k",
                    VOYAGE_RERANK_MODEL="rerank-3-lite", RERANK_TIMEOUT=15)
        base.update(kw)
        return MagicMock(**base)

    def test_scores_with_voyage_and_attaches_its_relevance(self):
        docs = [_doc("a", "alpha"), _doc("b", "beta"), _doc("c", "gamma")]
        resp = MagicMock()
        resp.json.return_value = {"data": [{"index": 2, "relevance_score": 0.8},
                                           {"index": 0, "relevance_score": 0.3}]}
        with patch("rag.retriever.get_settings", return_value=self._settings()), \
             patch("rag.retriever.requests.post", return_value=resp) as post:
            out = rerank_by_relevance("q", docs, top_n=2)
        assert [d.metadata["doc_id"] for d in out] == ["c", "a"]
        assert [d.metadata["_relevance_score"] for d in out] == [0.8, 0.3]
        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        assert url == "https://api.voyageai.com/v1/rerank"
        assert kwargs["headers"]["Authorization"] == "Bearer k"
        assert kwargs["json"] == {"query": "q", "documents": ["alpha", "beta", "gamma"],
                                  "model": "rerank-3-lite", "top_k": 2, "truncation": True}
        assert kwargs["timeout"] == 15

    def test_falls_back_to_the_original_order_on_an_http_error(self):
        docs = [_doc("a"), _doc("b"), _doc("c")]
        resp = MagicMock()
        resp.raise_for_status.side_effect = RuntimeError("429 Too Many Requests")
        with patch("rag.retriever.get_settings", return_value=self._settings()), \
             patch("rag.retriever.requests.post", return_value=resp):
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs[:2]
        assert all("_relevance_score" not in d.metadata for d in out)

    def test_without_a_key_it_keeps_the_original_order_and_calls_nothing(self):
        docs = [_doc("a"), _doc("b")]
        with patch("rag.retriever.get_settings", return_value=self._settings(VOYAGE_API_KEY="")), \
             patch("rag.retriever.requests.post") as post:
            out = rerank_by_relevance("q", docs, top_n=2)
        assert out == docs
        post.assert_not_called()
