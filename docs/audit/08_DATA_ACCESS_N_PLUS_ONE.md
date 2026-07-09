# PASS 8 — Data Access Patterns & N+1

## Inspected — no N+1 in request paths

- **Retrieval** (`chat._retrieve_docs`): one Pinecone MMR query + one hosted-reranker
  call per request, then in-memory dedupe/recency over a small pool (~k×multiplier ≈
  20–40 docs). No per-doc round trips.
- **SQLite**: `get_messages` (1 query), `list_conversations` (1), `list_reports` (1),
  ownership checks (1). No query-in-loop. Indexes exist on `conversations(user_id)`,
  `messages(conversation_id, id)`, `reports(user_id, created_at)`, `sessions(user_id)`.
- **Analytics scan** (`_collect_metadata`): `index.list` then metadata `fetch` **batched
  by 50** across a 32-worker pool — the batching/parallelism is deliberate and correct
  for a latency-bound scan; it is admin/post-ingest, not a per-user path.

## Minor notes (not findings)

- `analytics.slice_documents` substring-filters the full cached list (~25K rows) in
  Python per admin request — O(n) over an in-memory list; negligible at this scale and
  admin-only.
- `distinct_countries()` scans the cached list per `/reports/options` call — same,
  negligible.

## Pass 8 verdict
Clean. The vector store is queried once per request; SQLite access is single-query and
indexed; the one full scan is batched, parallel, and off the request path. No findings.
