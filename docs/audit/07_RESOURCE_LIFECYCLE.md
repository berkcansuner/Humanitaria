# PASS 7 — Resource Lifecycle & Leaks

## Inspected — sound

- **SQLite connections** (`rag/users.py`, `conversations.py`, `reports.py`): every
  access uses the `_connect()` `@contextmanager` → `commit()` on success, `close()` in
  `finally`. One connection per call, WAL mode. No leaked handles.
- **ThreadPoolExecutor** (`analytics._collect_metadata`): `with ThreadPoolExecutor(...)`
  → shut down on block exit. Bounded to `_FETCH_WORKERS=32`.
- **APScheduler**: started in lifespan, `scheduler.shutdown(wait=False)` on lifespan exit.
- **Background tasks** (`admin._bg_tasks`): strong-referenced in a set, discarded via
  `add_done_callback` → not GC'd mid-run, and released after.
- **SSE generators**: hold no external resource across yields; sse-starlette handles
  client-disconnect cancellation.

## Findings

### [P7-01] Write-side Pinecone client re-created per call
**Severity:** LOW · **Confidence:** CONFIRMED

`ingestion.store.get_store()` builds a fresh `PineconeStore()` (new `Pinecone()` client)
on every call — including per-request in `/health?deep`, `/admin/ingest/status`, and the
reports scan. The read-side is cached (`retriever._get_vectorstore` / `_get_pinecone_client`,
`lru_cache`), but the write-side is not. Not a handle leak (the client uses a pooled
urllib3 session and is GC'd), but it is avoidable churn on hot admin/health paths. Cache
it like the read side.

### [P7-02] (cross-ref P11-01) Unbounded upstream calls can hold the single worker
**Severity:** see P11-01

On the free tier (1 worker), a request blocked in an untimed embedding/Pinecone call
(P11-01/P11-02) holds a worker slot for up to the client default (~600s for the OpenAI
embedding client). A handful of such requests exhausts capacity. Tracked under PASS 11.

## Pass 7 verdict
Local resources (DB, threads, scheduler, tasks) are correctly scoped and released. The
only real risk is worker-holding from untimed *external* calls (PASS 11).
