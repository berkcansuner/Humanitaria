# PASS 11 — External Calls, Timeouts & Resilience

| Call site | Dependency | Timeout | Retry | Failure behavior | Verdict |
|-----------|-----------|---------|-------|------------------|---------|
| `ingestion/client.fetch` | ReliefWeb | **30s** | 5×, backoff; 4xx no-retry, 5xx/429 retry | raises after retries | OK |
| `store._upsert_batch` | Pinecone upsert | (client default) | 6×, backoff on 429 | raises | OK |
| `chain.build_chain` LLM | Gemini chat | **45s** (`CHAT_LLM_TIMEOUT`), `max_retries=0` | route-level pre-token retry | 503→retry msg | OK |
| `query_processor._get_llm_extractor` | Gemini query | **10s** | none (falls back to rule-based) | graceful fallback | OK |
| `embeddings.GeminiLangChainEmbeddings` | Gemini embed | **none → SDK default ~600s** | 3×, backoff | raises after retries | **P11-01** |
| `retriever` MMR query + `rerank_by_relevance` | Pinecone | (client default) | rerank has try/except fallback | keeps order on error | **P11-02** |
| `file_loader.fetch_pdf_text` | remote PDF | 30s | 3× | returns None | OK (op-gated) |
| `oauth.google.*` | Google | authlib/httpx defaults | none | fail-closed redirect | OK |

## Findings

### [P11-01] Query-embedding client has no timeout → can hang the request ~10 min
**Severity:** MEDIUM · **Confidence:** CONFIRMED (by code) · (cross-ref PASS 7)

`rag/embeddings.py:31` `OpenAI(api_key=..., base_url=...)` sets **no `timeout`** → the
openai-python default (~600s). `embed_query` (the query vectorization that runs at the
**start** of every chat/report retrieval, *before* the LLM) calls `_embed_with_retry`
(3 attempts, exponential backoff) with that untimed client. Under a Gemini slowdown (the
app has a documented history of Gemini 503s) a single query embedding can block for up to
~600s per attempt. This **defeats the deliberate 45s chat fast-fail** (which only covers
the LLM stage) and, on the single free-tier worker, a few such requests exhaust capacity
(DoS-by-slow-dependency). **Remediation:** pass an explicit `timeout` (e.g. 15–20s) to
the embeddings `OpenAI(...)` client (and ideally an overall retrieval timeout). Add a
test that a slow embed raises within the bound.

### [P11-02] Pinecone query + hosted reranker have no explicit timeout
**Severity:** LOW (→MEDIUM under load) · **Confidence:** CONFIRMED (by code)

`_get_vectorstore()` / `_get_pinecone_client()` use Pinecone client defaults with no
per-call timeout; `rerank_by_relevance` has a try/except fallback (keeps order on error)
but no timeout, and the vectorstore query has neither. A slow/hung Pinecone stalls
retrieval and holds the worker (same worker-exhaustion shape as P11-01). Remediation:
set a Pinecone client/request timeout and wrap retrieval with an overall deadline.

## Pass 11 verdict
Ingestion + chat-LLM + query-LLM resilience is well done (timeouts, bounded retry,
correct retryable/non-retryable split). The gap is the **embedding + Pinecone read**
calls lacking timeouts (P11-01 MEDIUM, P11-02 LOW/MED) — which undercuts the otherwise
careful fast-fail design on a single-worker deployment.
