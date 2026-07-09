# PASS 6 — Concurrency & Race Conditions

Concurrency model: single uvicorn process (Render free tier = 1 instance),
async event loop + `anyio.to_thread` workers for sync SQLite/Pinecone, one
APScheduler background thread (disabled in prod).

## Inspected — sound

- **Ingest overlap guard** (`ingestion/runner.py`): non-blocking `threading.Lock`
  shared by the scheduled job (APScheduler thread) and the manual trigger
  (`anyio.to_thread` worker) → a scheduled and a manual run can never overlap. The
  admin pre-check `is_running()` is advisory; the lock is the real guarantee.
- **Reports scan** (`ingestion/analytics.py`): same non-blocking-lock pattern.
- **Signup / user creation:** relies on the SQLite `UNIQUE(email)` / `UNIQUE(google_sub)`
  constraints → a concurrent duplicate signup raises `IntegrityError` → 409 (auth.py) /
  fail-closed (OAuth callback). **Check-then-act is delegated to the DB constraint** —
  race-safe.
- **Chat `session_id`:** `_verify_session_owner` gates a client id; ids are uuid4
  (unguessable) and bound to owner on create — no create/claim race across users.

## Findings

### [P6-01] In-process lock + in-memory run-state do not coordinate across instances
**Severity:** LOW · **Confidence:** CONFIRMED (scaling caveat)

The ingest/scan locks and `RunState`/`ReportsCache` are per-process. Correct for the
current single-instance deploy (and prod has the scheduler OFF; cron is one external
caller). If the service is ever scaled to >1 instance/worker, two ingests could run
concurrently (no distributed lock) — mostly self-correcting because ingestion is
idempotent (PASS 12), but retention deletes could interleave. Document the single-instance
assumption; use a DB/Redis lock if scaled.

### [P6-02] Shared in-memory dicts mutated from event loop AND worker threads
**Severity:** LOW · **Confidence:** CONFIRMED (benign under CPython)

`rag/history._session_histories` is populated by `populate_history_from_messages`
running inside `anyio.to_thread` (`_ensure_conversation_and_seed`) while other coroutines
call `get_session_history`/eviction on the event-loop thread; `analytics._state` is
similarly read on the loop and written in a worker. Individual dict ops are atomic under
the GIL, and the sequences here don't hold invariants across an `await`, so no corruption
is realistically reachable — but the access is unsynchronized. If history ops ever move
fully off-thread or the GIL assumption changes, add a lock. Noted for completeness.

## Pass 6 verdict
The genuinely dangerous races (duplicate ingest, duplicate account) are correctly
prevented by a lock and by DB constraints. Remaining items are scaling/theoretical (LOW).
