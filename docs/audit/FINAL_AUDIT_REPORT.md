# FINAL AUDIT REPORT — Humanitaria (ReliefWeb RAG)

Date: 2026-07-09 · Scope: full repository (backend `api`/`rag`/`ingestion`, Vue+React
frontend, Docker/Render/Cloudflare config). Method: 20-pass evidence-based audit
(`docs/audit/00_*`–`20_*`). One CRITICAL was found and fixed under the user's direction;
all other findings are documented for a separate remediation phase.

# 1. Executive Summary

- **Overall posture: strong, with one now-fixed critical flaw.** The application is
  well-engineered defensively: parameterized SQL, DOMPurify-sanitized markdown, a clean
  server-side authorization model with no reachable IDOR, solid auth (hashed high-entropy
  sessions, bcrypt, timing-safe login, OAuth state + `email_verified`), bounded caches,
  and thoughtful ingestion error handling + idempotency.
- **Strongest areas:** authorization/IDOR (PASS 3 — clean), secret hygiene (PASS 4),
  memory bounding (PASS 10), injection defenses other than the file-serving path.
- **Weakest areas:** the SPA file-serving path (P1-01, now fixed), deployment hardening
  (container root, missing security headers), and upstream-call timeouts (embedding/Pinecone).
- **Most urgent risk (RESOLVED):** **P1-01** — unauthenticated arbitrary file read via the
  SPA catch-all, which leaked `.env` / `/proc/self/environ` (all secrets incl.
  `AUTH_SESSION_SECRET`) and `conversations.db` (bcrypt hashes + PII). Live-reproduced, then
  fixed with a containment check + 3 regression tests + live re-verification.

# 2. Project Architecture Summary

Single FastAPI process serving a Vue SPA + JSON/SSE API. RAG over a **public** ReliefWeb
corpus in Pinecone; Gemini (OpenAI-compat, via Cloudflare AI Gateway) for chat/embeddings.
Auth = httpOnly session cookie (SQLite-backed) + Google OAuth. Per-user conversations and
M&E reports in SQLite (ephemeral on Render free tier). Ingestion pipeline (APScheduler +
external Cloudflare cron). Sensitive assets = user accounts/PII, per-user chats/reports,
and operational secrets (the corpus itself is public). Full map: `00_PROJECT_MAP.md`.

# 3. Audit Coverage

| Pass | Status | Findings | N/A reason |
|------|--------|----------|-----------|
| 1 Injection | ✅ | 1 CRIT (fixed), 1 MED, 2 LOW | — |
| 2 Authentication | ✅ | 1 MED, 2 LOW | — |
| 3 Authorization/IDOR | ✅ | 0 (clean) | — |
| 4 Secrets | ✅ | 1 LOW (op) | — |
| 5 Error/Failure | ✅ | 2 LOW | — |
| 6 Concurrency | ✅ (PARTIAL) | 2 LOW | mostly single-process |
| 7 Resources | ✅ | 1 LOW | — |
| 8 Data/N+1 | ✅ (PARTIAL) | 0 | small SQLite; batched scans |
| 9 Complexity | ✅ (PARTIAL) | 0 | low-concurrency load model |
| 10 Memory | ✅ (PARTIAL) | 0 (strong) | — |
| 11 External calls | ✅ | 1 MED, 1 LOW | — |
| 12 Idempotency | ✅ | 1 LOW | — |
| 13 Transactions | ✅ | 3 LOW | — |
| 14 Config hardening | ✅ | 2 MED, 1 LOW, 1 NIT | — |
| 15 Dependencies | ✅ (PARTIAL) | 1 LOW + NEEDS-CONTEXT (backend) | pip-audit not installed locally |
| 16 Logging | ✅ | 3 LOW | — |
| 17 API contracts | ✅ (PARTIAL) | 1 LOW | single consumer |
| 18 Cross-module | ✅ | 1 LOW | user file-upload = N/A |
| 19 Test gaps | ✅ | top-10 list (#1 fixed) | — |
| 20 Verification | ✅ | filter/merge/re-score | — |

# 4. Baseline Validation Results

All green (captured pre-audit, re-run post-fix): `pytest` **491 passed** (488 + 3 new
security tests), `ruff` clean, `mypy` clean (config.py), `vitest` **81 passed**,
`vite build` ok. `pip-audit` (backend) NEEDS-CONTEXT (not installed locally); `npm audit`
captured (7 vulns, all dev-only or not-in-used-path — see PASS 15). Details:
`00_BASELINE_RESULTS.md`.

# 5. Confirmed Findings (by severity)

**CRITICAL**
- **P1-01 — Unauthenticated path traversal / arbitrary file read (SPA fallback).**
  **RESOLVED** this session (containment fix + tests + live re-verify).

**MEDIUM**
- **P1-02 — SSRF via xhtml2pdf** rendering LLM report `<img>` (sink reproduced; full chain
  LLM-emission-dependent).
- **P11-01 — Query-embedding client has no timeout** (~600s default) → hangs retrieval /
  exhausts the single worker; undercuts the 45s chat fast-fail.
- **P14-01 — Container runs as root.**
- **P14-02 — No security headers** (CSP / X-Frame-Options / nosniff / HSTS).

**LOW** (see `20_VERIFICATION.md` for the full table)
- P2-02 health-deep amplification · P4-01 operator-secret rotation · P5-01/P13-01 watermark
  advances past failures · P5-02 silent rebuild swallow · P6-01 no cross-instance lock ·
  P6-02 unsynchronized shared dicts · P7-01 uncached write client · P11-02 Pinecone no
  timeout · P12-01 double-submit duplicates · P13-02 non-atomic file writes · P13-03
  multi-txn chat persist · P14-03 no body-size limit · P16-01 no correlation id · P16-02
  Sentry PII posture · P16-03 no audit trail · P17-01 unpaginated lists · P18-01 PDF export
  not rate-limited · P1-03 attachment SSRF (op-gated) · P1-04 report input validation.

**NIT:** P14-04 no `.dockerignore`; CI actions / base images not digest-pinned.

# 6. Unverified Findings
- **P2-01 (MEDIUM)** — rate limiter likely keys on the proxy IP behind Render → shared
  global bucket (auth/chat DoS). Needs prod confirmation of `request.client.host`.
- **Backend CVEs (PASS 15)** — run `pip-audit` against the pinned versions.

# 7. Rejected False Positives
SQLi, XSS, IDOR, prompt-injection-as-privilege-escalation, ReDoS, header injection, XXE,
session fixation, committed secrets — all inspected and disproven (evidence in
`20_VERIFICATION.md`).

# 8. Top 10 Highest-Value Missing Tests
See `19_TEST_GAPS.md`. #1 (path-traversal) **added**; prioritize #2 rate-limiter-IP,
#3 embedding-timeout, #4 xhtml2pdf-SSRF, #5 ingest partial-failure watermark.

# 9. Immediate Remediation Plan (by blast radius / exploitability / impact)
1. **P1-01 — DONE** (unauth secret+PII disclosure).
2. **P2-01** — confirm + fix the rate-limiter client-IP (auth-DoS). Verify prod first.
3. **P11-01 / P11-02** — add explicit timeouts to the embedding + Pinecone clients (worker
   exhaustion on a single-worker deploy).
4. **P14-02** — add security-header middleware (CSP/XFO/nosniff/HSTS).
5. **P1-02** — restrict xhtml2pdf resource loading (`link_callback`) / strip `<img>`.
6. **P14-01** — run the container as non-root.
7. **P4-01** — rotate the two leaked operator secrets (user action).

# 10. Recommended Remediation Phases
- **P0 (immediate):** P1-01 ✅ done · P4-01 rotate secrets · P2-01 confirm+fix rate-limit.
- **P1 (before next release):** P11-01/02 timeouts · P14-02 security headers · P1-02 SSRF ·
  P14-01 non-root · P14-03 body-size limit.
- **P2 (planned hardening):** P16-01/03 correlation-id + audit log · P18-01 PDF rate-limit ·
  P17-01 pagination · P15 dependency fixes (`npm audit fix`, backend pip-audit) · P5-01
  watermark completeness · P2-02 health-deep throttle.
- **P3 (tech debt):** P13-02 atomic writes · P13-03 txn-wrap chat persist · P6-01 distributed
  lock (only if scaled) · P7-01 cache write client · P14-04 `.dockerignore` · P12-01
  idempotency key · P16-02 Sentry PII config.

# 11. Final Verdict

**ACCEPTABLE WITH IDENTIFIED RISKS — PRODUCTION READY AFTER P0.**

The one production-blocking issue (P1-01, unauthenticated full secret + PII disclosure) has
been **fixed and verified** in this session. With P4-01 (secret rotation) and P2-01
(rate-limiter confirmation) closed out, the deployment is in good shape. The remaining
MEDIUMs are meaningful hardening (timeouts, security headers, SSRF, non-root) but none is
an unauthenticated critical-takeover path. The codebase shows consistently strong security
fundamentals — the authorization model and secret hygiene in particular are exemplary for a
project of this size. Recommend completing P0/P1 before broadening the user base.
