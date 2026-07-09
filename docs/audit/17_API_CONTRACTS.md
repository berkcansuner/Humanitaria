# PASS 17 — API Contract Consistency

Single consumer (the app's own Vue SPA), so cross-client drift risk is low; still checked
for internal consistency + frontend/backend alignment.

## Inspected — consistent
- **Status codes** used coherently: 401 (unauth), 403 (admin/token), 404 (not-found /
  ownership, no existence leak), 409 (duplicate/conflict), 422 (validation), 429 (rate),
  503 (upstream busy / readiness).
- **SSE event vocabulary** is consistent across chat + reports (`token`, `session`,
  `sources`, `persisted`/`saved`, `clarification`, `error`, `done`) and matches
  `frontend/src/utils/parseSSE.js`.
- **Errors** are `HTTPException(detail=…)` (string, or a structured dict for `/health`
  deep) — uniform enough for one consumer.

## Findings

### [P17-01] Unpaginated per-user list endpoints
**Severity:** LOW · `GET /conversations` and `GET /reports/list` return **all** of a user's
rows with no pagination/limit. Fine at current scale, but a heavy user grows an unbounded
response over time. The admin documents endpoint is correctly paginated (offset/limit);
apply the same to these two.

## Pass 17 verdict
Internally consistent; single-consumer API. One LOW (unpaginated user lists). Largely N/A
for multi-client contract drift.
