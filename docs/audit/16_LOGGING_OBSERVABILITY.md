# PASS 16 — Logging, Observability & Auditability

## Inspected — good baseline
- Central `dictConfig` (`api/observability.py`) with a consistent format + `LOG_LEVEL`;
  uvicorn routed through the same handler. Opt-in Sentry (import-guarded).
- Per-module `logging.getLogger(__name__)` throughout. Chat logs a useful latency
  breakdown (`filter/retrieval/ttft/total/ns`). Ingestion logs progress + failures.
- **No secrets or emails in logs** (OAuth logs the opaque `sub`, not the email; errors
  log `%r` of exceptions, not credentials).

## Findings

### [P16-01] No request/correlation ID
**Severity:** LOW · A single request's log lines can't be correlated (no request id / trace
id). For incident reconstruction on a busy log, add a correlation-id middleware and include
it in log records (and Sentry scope).

### [P16-02] Sentry PII scrubbing not explicitly asserted
**Severity:** LOW (only if `SENTRY_DSN` enabled) · `init_sentry` sets no `send_default_pii`
(defaults to False, and Sentry scrubs `cookie`/`authorization` by default), so the session
cookie is unlikely to be captured — but this relies on defaults. If Sentry is enabled,
explicitly set `send_default_pii=False` and confirm cookie/body scrubbing.

### [P16-03] No security-event audit trail
**Severity:** LOW (elevated for sensitive-domain) · There is no explicit audit logging of
security-relevant events: login failures, admin ingest triggers, permission denials
(403/404-on-ownership), report/PDF exports. For a humanitarian app handling user accounts,
a minimal structured audit log (who/what/when, no PII beyond user id) aids incident
response. Currently only incidental `logger.warning`s exist (e.g. rejected unverified OAuth).

## Pass 16 verdict
Solid logging foundation; gaps are correlation IDs (P16-01), explicit Sentry PII posture
(P16-02), and a security audit trail (P16-03) — all LOW.
