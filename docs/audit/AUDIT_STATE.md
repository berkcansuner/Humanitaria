# AUDIT_STATE — Resumable Checkpoint

> Source of truth for audit progress across sessions. Update after every pass.
> Do NOT rely on chat context — read this file first on resume.

## Continuation command (for the next session)

> Read, in order: `docs/audit/AUDIT_STATE.md`, `00_PROJECT_MAP.md`,
> `00_APPLICABILITY_MATRIX.md`, then the last completed pass file. Resume at the
> "Next action" below. Baseline is green (488 backend / 81 frontend); re-run only
> if source changed.

## Current position

- **Phase 0:** ✅ COMPLETE
- **PASS 1 (Injection):** ✅ — 1 CRITICAL (P1-01) **FIXED & verified**; P1-02 xhtml2pdf SSRF to verify (PASS 20).
- **PASS 2 (Auth):** ✅ — core strong; P2-01 rate-limiter proxy-IP (MEDIUM, verify), P2-02 health deep (LOW).
- **PASS 3 (AuthZ/IDOR):** ✅ — CLEAN, no IDOR (full matrix in `03`).
- **PASS 4 (Secrets):** ✅ — strong hygiene; P4-01 op rotation (known).
- **PASSES 5–19:** ✅ — see `05`–`19`. +3 MED (P11-01 embed timeout, P14-01 root, P14-02 headers) + ~18 LOW/NIT; PASS 3/8/9/10 clean.
- **PASS 20 (Verification):** ✅ — P1-02 SSRF sink reproduced; P2-01 + backend CVEs = NEEDS-CONTEXT; merges/rejects applied (`20`).
- **FINAL REPORT:** ✅ `FINAL_AUDIT_REPORT.md` — verdict: ACCEPTABLE / PRODUCTION-READY-AFTER-P0.
- **✅ AUDIT COMPLETE (20/20).** Only P1-01 remediated (user-directed fix-now). All other findings = separate remediation phase (P0/P1/P2/P3 plan in final report).
- **Passes complete:** 20 / 20

## Confirmed findings so far

- **[P1-01] CRITICAL — Unauthenticated path traversal / arbitrary file read**
  (`api/main.py` `spa_fallback`). Live-reproduced: read `.env` (1360B),
  `conversations.db` (184KB), `config.py` via `/../../` and encoded `..%2f`. Prod
  vector `/proc/self/environ` → all injected secrets + `AUTH_SESSION_SECRET`.
  **✅ FIXED & VERIFIED 2026-07-09** — `resolve()` + `is_relative_to(_dist_root)`
  containment; 3 TDD regression tests (`tests/test_spa_fallback_security.py`); full
  suite 491 passed; live re-repro now returns index.html. (User chose fix-now.)

## Baseline (captured 2026-07-09, all green)

- `pytest tests/ -q` → 488 passed
- `ruff check api rag ingestion config.py` → clean
- `mypy` → clean (config.py only)
- `vitest run` → 81 passed
- `vite build` → ok
- `pip-audit` / `npm audit` → DEFERRED to PASS 15 (NEEDS-CONTEXT: live advisory data)

## Remediation applied (2026-07-09, branch `fix/security-audit-p0-p1`)

All TDD (red→green). Full suite **494 passed**, ruff clean.
- **P1-01** CRIT path traversal — FIXED (resolve + `is_relative_to` containment) + 3 tests
  + live re-verify. [d466f02]
- **P11-01** MED embedding timeout — FIXED (`EMBED_TIMEOUT=20` passed to the embedding
  `OpenAI(...)` client) + `tests/test_embeddings.py`.
- **P1-02** MED xhtml2pdf SSRF — FIXED (`link_callback` replaces any remote/file URI with an
  inline blank `data:` image) + `tests/test_report_pdf_security.py` (socket probe → 0 fetch).
- **P14-02** MED security headers — FIXED (pure-ASGI middleware: CSP/X-Frame-Options/nosniff/
  Referrer-Policy/HSTS-in-prod) + `tests/test_security_headers.py` + **browser CSP smoke**
  (landing + /login render fully, no CSP violations).
- **P14-01** MED container root — FIXED (`adduser` + `chown` + `USER app`); **needs a
  Docker build/deploy check** (not built locally).

- **P2-01** MED rate-limiter proxy-IP — FIXED (`RATE_LIMIT_TRUSTED_HOPS`: read the real
  client IP as the Nth-from-right `X-Forwarded-For` entry, spoofing-safe; `render.yaml=1`
  for Render's single proxy) + 4 unit tests + **live-verified** (distinct XFF → distinct
  rate buckets; forged prefix ignored, real rightmost IP used).

### P2/P3 backlog batch (quick + valuable LOW/NIT)
- **P18-01** PDF export rate-limit — FIXED (per-IP limiter on the pdf route) + test.
- **P15** dependency CVEs — `npm audit fix` bumped dompurify + form-data (non-breaking);
  dev-only vite/esbuild chain deferred (breaking major bump).
- **P13-02** atomic state writes — FIXED (temp + `os.replace` for watermark + reports
  cache) + tests.
- **P16-01 / P16-03** observability — FIXED (request correlation id + `X-Request-ID` +
  security audit logs) + tests.
- **P14-04** `.dockerignore` — REJECTED (false positive; the file existed) + a minor
  `.reports_cache.json` addition.
- **P17-01** unpaginated lists — DEFERRED (needs a coordinated frontend change; a silent
  server-side cap would drop a heavy user's rows).

Still open: **P4-01** (user rotates the leaked operator secrets) + the nuanced / WONTFIX
LOW items by choice (P2-02 health-deep throttle, P6-01/02 multi-instance, P7-01 write
client, P12-01 idempotency key, P16-02 Sentry PII). See `FINAL_AUDIT_REPORT.md`.

Tests after the full remediation: **505 backend + 81 frontend green; ruff/mypy clean.**

## Pass status

| Pass | Status | Confirmed | Unverified | Notes |
|------|--------|-----------|------------|-------|
| 0 Recon | ✅ done | — | — | map + matrix + baseline |
| 1 Injection | ✅ done | **1 CRIT** | 1 MED, 2 LOW | P1-01 path traversal CONFIRMED; SQLi/XSS/ReDoS SAFE; P1-02 xhtml2pdf SSRF to verify |
| 2 Auth | ✅ done | — | 1 MED,1 LOW | core strong; P2-01 rate-limiter proxy-IP (verify), P2-02 health deep |
| 3 AuthZ/IDOR | ✅ done | — | — | CLEAN — no IDOR; full matrix |
| 4 Secrets | ✅ done | — | 1 LOW | strong hygiene; P4-01 op rotation; P1-01 was the exposure vector (fixed) |
| 5 Errors | ⬜ next | | | ingestion multi-step, SSE mid-stream, broad except |
| 6 Concurrency | ⬜ | | | |
| 7 Resources | ⬜ | | | |
| 8 Data/N+1 | ⬜ | | | |
| 9 Complexity | ⬜ | | | |
| 10 Memory | ⬜ | | | |
| 11 External calls | ⬜ | | | |
| 12 Idempotency | ⬜ | | | |
| 13 Transactions | ⬜ | | | |
| 14 Config hardening | ⬜ | | | Docker root, CORS, cookie flags, headers |
| 15 Dependencies | ⬜ | | | pip-audit 18 CVE (NEEDS-CONTEXT), npm audit |
| 16 Logging | ⬜ | | | |
| 17 API contracts | ⬜ | | | |
| 18 Cross-module | ⬜ | | | |
| 19 Test gaps | ⬜ | | | |
| 20 Verification | ⬜ | | | MUST run last |

## Leads captured during Phase 0 recon (hypotheses — NOT yet findings)

1. `api/main.py:132-137` `spa_fallback` — `frontend_dir / full_path` + `is_file()`
   → potential path traversal / arbitrary file read. Verify ASGI `..` normalization. **PASS 1, high priority.**
2. `Dockerfile` — no `USER`; container runs as **root**. **PASS 14.**
3. Two operator secrets pasted in past chat await rotation (NOT committed). **PASS 4** (verify git history clean).
4. LLM-generated Pinecone metadata filters (`query_processor` → `retriever`). Prompt-injection → filter manipulation. **PASS 1 (LLM ext).**
5. `xhtml2pdf` report PDF + `file_loader` PDF fetch → SSRF / remote resource fetch. **PASS 1 / 11.**
6. SQLite stores (`rag/users.py`, `rag/conversations.py`, `rag/reports.py`) — confirm parameterized queries. **PASS 1.**
7. Frontend markdown render (`marked` + `dompurify`) — confirm sanitization actually wraps LLM output. **PASS 1 (XSS).**
8. `test_conversation_access_control.py` exists → IDOR appears tested; verify coverage completeness. **PASS 3.**
9. `/health?deep=true` may expose internal readiness detail. **PASS 4.**
10. Prior audits (TIER 1–3) already fixed: ingest data-loss window, prod `/docs` hidden, session-secret fail-fast, OAuth `email_verified`, auth rate-limit, MMR fetch_k. **Verify still present; do not re-report as new.**

## Safety notes

- Tests run offline with dummy env. Do NOT run live upstream calls against prod.
- Local `.env` holds real keys — never print its values into any report (redact).
- A local hook denies writes to `.env` / `.db` / state files.
