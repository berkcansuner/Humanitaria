# 00 — 20-Pass Applicability Matrix

States: **YES** (fully applies) · **PARTIAL** (applies to a subset) · **N/A** (does
not apply, with evidence). No pass is fully N/A for this project.

| Pass | Relevant? | Reason | Main Areas |
|------|-----------|--------|------------|
| 1 — Injection & Untrusted Input | **YES** | Rich untrusted-input surface + LLM. | Chat/report input → LLM (prompt injection); LLM → Pinecone metadata filters; SPA catch-all `GET /{full_path}` → filesystem (path traversal); SQLite queries; markdown→XSS (frontend `marked`+`dompurify`); `file_loader`/`xhtml2pdf` remote fetch (SSRF); ReliefWeb API response as data |
| 2 — Authentication & Session | **YES** | Full custom auth stack. | Email/password (bcrypt), Google OAuth (Authlib, userinfo flow), httpOnly session cookie, server-side session store, `AUTH_SESSION_SECRET`, cookie flags, logout/revocation |
| 3 — Authorization & IDOR | **YES (elevated)** | Sensitive-domain; per-user resources. | Conversation & report ownership (IDOR/BOLA), admin allowlist (`ADMIN_EMAILS`), cron token, mass-assignment on create/update |
| 4 — Secrets & Data Exposure | **YES** | Multiple live API keys + PII. | `.env`, key handling, git history, logs/error messages, SSE error payloads, `/health` internals, frontend bundle, two known-leaked operator secrets |
| 5 — Error Handling & Failure Paths | **YES** | Multi-step ingest + streaming + DB. | Ingestion partial failure, SSE mid-stream errors, DB write failure, broad `except`, swallowed errors, false-success |
| 6 — Concurrency & Races | **PARTIAL** | Mostly single-process, but real shared state. | SQLite concurrent writes, signup check-then-act, OAuth callback DB race, `threading.Lock` ingest guard, in-memory session LRU, fire-and-forget tasks |
| 7 — Resource Lifecycle & Leaks | **YES** | Connections, clients, streams, handles. | SQLite connection handling, `httpx`/requests clients, SSE generator cleanup, PDF file handles, APScheduler shutdown, background task refs |
| 8 — Data Access & N+1 | **PARTIAL** | SQLite small; Pinecone is main. Loops exist. | Report synthesis fetch loop, analytics full-namespace scan, per-conversation message loads, Pinecone fetch batching |
| 9 — Algorithmic Complexity & Hot Paths | **PARTIAL** | A few data-scaling paths. | Citation/dedup, MMR+rerank blend, report synthesis over `REPORT_TOP_K`, analytics scan, langdetect per doc |
| 10 — Memory & Unbounded Growth | **PARTIAL** | Caches claim to be bounded — verify. | Session history LRU (`SESSION_MAX_MEMORY`), query/embedding/filter caches, reports cache, SSE buffers |
| 11 — External Calls, Timeouts & Resilience | **YES** | Many upstreams, mixed timeout/retry. | Gemini, Pinecone, ReliefWeb, Google OAuth, remote file/PDF fetch, xhtml2pdf resource fetch |
| 12 — Idempotency & Retry Safety | **YES** | Ingest retries, cron redelivery, double-submit. | Ingestion (canonical `doc_id` + delete-before-upsert), signup dup email, chat/report double-submit, cron replay |
| 13 — Transactions & Consistency | **YES** | Multi-store writes without DB txn. | Pinecone upsert + orphan delete + watermark + reports cache; chat persist message+session; DB + Pinecone divergence |
| 14 — Configuration & Hardening | **YES** | Docker + Render + Cloudflare + env. | Container runs as root, CORS/credentials, cookie `Secure/HttpOnly/SameSite`, prod fail-fast, startup validation, security headers, `.env` handling |
| 15 — Dependency & Supply Chain | **YES** | Pinned deps + known advisory CVEs. | `requirements.txt`, `package-lock.json`, `pip-audit` (18 CVE noted), `npm audit`, base image currency, CI action pinning |
| 16 — Logging & Observability | **YES** | Central logging + Sentry; audit needs. | Request/correlation IDs, structured logs, PII/secret in logs, admin/auth audit trail, log levels, Sentry scrubbing |
| 17 — API Contract Consistency | **PARTIAL** | Small internal API, single consumer. | Error shape/status-code consistency, pagination, null-vs-absent, frontend/backend drift |
| 18 — Cross-Module Contracts & Emergent Risks | **YES** | Several tight boundaries + cross-cutting. | chat↔retriever↔query_processor, frontend↔backend citation/SSE contract, ingest pipeline↔store; request-size limits, rate-limit coverage, security headers, CSP, clickjacking. (User file-upload lifecycle = **N/A**, no user upload endpoint) |
| 19 — Test Gap & Assertion Quality | **YES** | 488 backend + 81 frontend tests to map vs risk. | Auth/authz matrix tests, ingestion failure/rollback, concurrency, SSE, findings from 1–18 |
| 20 — Verification & False-Positive Filter | **YES (always last)** | Mandatory. | Relocate, falsify, reachability, safe repro, dedup, rescore |

## Proposed audit execution order

Sequential PASS 1 → PASS 20 as mandated, but effort is weighted toward the
highest-value passes for this app:

**Tier A (deepest):** 1 (injection incl. path-traversal + LLM), 3 (IDOR — sensitive
domain), 2 (auth), 4 (secrets), 14 (hardening).
**Tier B:** 5, 11, 12, 13, 6 (failure/resilience/consistency/concurrency of the
ingest + chat + DB paths).
**Tier C:** 7, 8, 9, 10, 15, 16, 17, 18, 19 (breadth + operational).
**Always last:** 20 (verification / false-positive filter).
