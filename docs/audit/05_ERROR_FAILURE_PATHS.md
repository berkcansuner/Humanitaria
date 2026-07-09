# PASS 5 — Error Handling & Failure Paths

Focus: multi-step ingestion, SSE streaming, DB writes.

## Inspected — sound

- **Ingestion** (`ingestion/pipeline.py`) is the main multi-step path. Failures are
  isolated and counted, never silently swallowed: per-item parse/chunk in `try/except`
  → `stats.failed` + logged (line 88-92); per-batch embed/upsert in `try/except`
  → counted + logged (line 116-123). **Orphan delete is deferred until AFTER a
  successful upsert** (line 107-114) so a failed embed never leaves a document with
  zero vectors (the TIER-1 data-loss fix — confirmed present).
- **SSE streaming** (`chat.py` `event_generator`, `reports.py`): mid-stream errors are
  caught → an `error` event + `done` are emitted (never a broken stream); persistence
  happens **only after a full stream** (`_persist_exchange`, `create_report`), so an
  aborted turn is never written. Retry rides only pre-first-token 503s (`_astream_with_retry`).
- **Chat non-stream** distinguishes transient 503 (→ 503 retryable message) from a
  genuine bug (→ logged 500 + generic message). `_is_high_demand` is deliberately narrow
  so a real bug is not masked as transient.

## Findings

### [P5-01] Partial batch failure advances the watermark → failed docs not retried
**Severity:** LOW · **Confidence:** CONFIRMED · (merged with P13-01)

`run_pipeline` catches per-batch embed/upsert failures internally and returns stats
**without raising**. `runner.run_ingest_once` then advances the watermark to *today*
on that (non-raising) return. Documents that failed to embed/upsert have a
`date.created` older than the new watermark, so the next incremental run
(`date_from = watermark`) never re-fetches them → they are **silently absent** from the
index until a manual `--force` / full re-ingest. Impact: best-effort corpus
completeness gaps; retrieval still functions. Remediation: track failed doc dates and
either don't advance the watermark past unresolved failures, or re-enqueue them.

### [P5-02] Silent swallow of the post-ingest cache/retention rebuild
**Severity:** LOW · **Confidence:** CONFIRMED

`runner.py:73-77` wraps `analytics.rebuild_documents(apply_retention=True)` in a bare
`except Exception: pass`. A retention/rebuild failure (incl. a botched deletion) is
neither logged nor surfaced. Best-effort by design, but at minimum it should `logger.warning`.

## Pass 5 verdict
Failure handling is a relative strength (isolated, counted, logged, no partial persist).
Two LOW notes around ingest completeness/observability.
