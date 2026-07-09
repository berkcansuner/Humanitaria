# PASS 10 — Memory & Unbounded Growth

## Inspected — all growth is bounded (STRONG)

| State | Bound |
|-------|-------|
| `rag/history._session_histories` | LRU, `SESSION_MAX_MEMORY=1000` sessions; each window capped at `HISTORY_WINDOW_K*2` messages |
| `rag/embeddings._query_embed_cache` | LRU `OrderedDict`, `_QUERY_CACHE_MAX=512` |
| `rag/query_processor._llm_cache` | LRU `OrderedDict`, `_MAX_LLM_CACHE=512` |
| `ingestion/analytics._state.documents` | one list, bounded by corpus size (~25–30K lean rows), replaced wholesale each rebuild |
| `admin._bg_tasks` | set, entries removed via `add_done_callback` |
| Pinecone upsert / embed batches | fixed batch sizes (100 / `EMBED_BATCH_SIZE`) |

Every cache has an explicit eviction policy and cap; no module-level collection grows
per-request without a bound. Session windows also self-trim per message.

## Note
- With `REDIS_URL` unset (default), session history lives in-process and resets on
  restart — a known/accepted limitation (documented), not a growth risk.

## Pass 10 verdict
Memory posture is a strength — all identified caches/collections are explicitly bounded.
No findings.
