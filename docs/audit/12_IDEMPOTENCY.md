# PASS 12 — Idempotency & Retry Safety

## Inspected — sound

- **Ingestion is idempotent by construction:** `doc_id = sha256(canonical
  reliefweb.int/report/{id})` is stable across re-runs; chunk ids are deterministic
  `{doc_id}_{i}`; upsert overwrites in place and orphan-delete prunes only surplus. Re-
  running the pipeline (queue redelivery, retry, cron double-fire) converges to the same
  index state. **PROTECTED BY CONSTRUCTION.**
- **Cron trigger** (`/admin/ingest/cron`): `runner.is_running()` + the non-blocking lock
  prevent a concurrent double-run; a sequential re-fire just re-ingests idempotently.
- **Signup:** `UNIQUE(email)` → duplicate is a 409, not a second account. **PROTECTED BY
  CONSTRAINT.**
- **Chat/report persist only after a full stream** → an aborted/retried stream does not
  write a partial exchange.

## Findings

### [P12-01] No idempotency key on chat/report submit → double-submit duplicates
**Severity:** LOW · **Confidence:** CONFIRMED

Two rapid `POST /chat/stream` (or `/reports/stream`) for the same `session_id`
(double-click, client retry) each run to completion and each `append_message` /
`create_report`, producing **duplicate user+assistant messages** (or two saved reports
with different uuids). Self-inflicted, same-user, low impact — but there is no
idempotency key or in-flight de-dup per session. Remediation (optional): a client-supplied
idempotency key, or reject a new submit while one is streaming for the same session.

## Pass 12 verdict
The high-stakes path (ingestion) is fully idempotent; account creation is constraint-
protected. Only a minor same-user double-submit duplication (LOW).
