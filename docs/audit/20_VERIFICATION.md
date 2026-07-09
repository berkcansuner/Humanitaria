# PASS 20 — Verification & False-Positive Filter

Every PASS 1–19 finding was relocated in current code, tested for existing
protection (falsification), checked for reachability, and reproduced where safe.
No new findings created here. Merges applied. Severity re-scored conservatively.

## CONFIRMED (sorted by severity)

| ID | Sev | What | Verification |
|----|-----|------|--------------|
| **P1-01** | CRITICAL → **RESOLVED** | Unauth path traversal / arbitrary file read (SPA fallback) | Live-reproduced (`.env` 1360B, `conversations.db` 184KB, `config.py` via `../` + `..%2f`); **fixed** (`is_relative_to` containment) + 3 regression tests + full suite 491; live re-repro now returns index.html. |
| **P1-02** | MEDIUM | SSRF via xhtml2pdf rendering report `<img>` | **Sink reproduced** (3 connection hits to a local listener during `render_report_pdf`). Full chain needs LLM to emit `<img>` (PLAUSIBLE, not run). |
| **P11-01** | MEDIUM | Query-embedding client has no timeout (~600s default) → hangs retrieval / holds worker | Confirmed by code: `OpenAI(...)` sets no `timeout`; `embed_query` runs pre-LLM with 3 untimed retries. |
| **P14-01** | MEDIUM | Container runs as root | Confirmed: `Dockerfile` has no `USER`. |
| **P14-02** | MEDIUM | No security headers (CSP / X-Frame-Options / nosniff / HSTS) | Confirmed: no header middleware; Starlette/Render add none by default. |
| **P2-02** | LOW | `/health?deep` unauth + unthrottled hits Pinecone+DB | Confirmed by code. |
| **P4-01** | LOW (op) | Two operator secrets await rotation (not in repo) | Confirmed operational (MEMORY); redacted. |
| **P5-01 / P13-01** | LOW | Watermark advances past failed docs (merged) | Confirmed by code (`run_pipeline` doesn't raise on partial fail; runner advances watermark). |
| **P5-02** | LOW | Silent `except: pass` on post-ingest rebuild | Confirmed (`runner.py:73-77`). |
| **P6-01** | LOW | In-process lock/state, no cross-instance coordination | Confirmed (scaling caveat; single-instance today). |
| **P6-02** | LOW | Shared dicts mutated from loop+worker (GIL-safe) | Confirmed; benign under CPython. |
| **P7-01** | LOW | Write-side Pinecone client re-created per call | Confirmed (`get_store()` uncached). |
| **P11-02** | LOW→MED | Pinecone query + rerank have no explicit timeout | Confirmed by code. |
| **P12-01** | LOW | No idempotency key → chat/report double-submit duplicates | Confirmed by code. |
| **P13-02** | LOW | Non-atomic state-file writes | Confirmed (`write_text`, no tmp+rename); self-healing readers. |
| **P13-03** | LOW | Chat persistence = multiple independent txns | Confirmed by code. |
| **P14-03** | LOW | No request-body size limit | Confirmed (no middleware/limit). |
| **P16-01** | LOW | No request/correlation ID | Confirmed. |
| **P16-03** | LOW | No security-event audit trail | Confirmed. |
| **P17-01** | LOW | Unpaginated per-user list endpoints | Confirmed by code. |
| **P18-01** | LOW | PDF export not rate-limited (CPU) | Confirmed by code. |
| **P1-03** | LOW | `fetch_pdf_text` no host allowlist (SSRF) | Confirmed but op-gated (`FETCH_PDF_CONTENT=False`), trusted source. |
| **P1-04** | LOW | Report `date_*`/`theme` unvalidated | Confirmed by code. |
| **P14-04** | NIT | No `.dockerignore` | Confirmed. |
| **P16-02** | LOW (cond.) | Sentry PII posture relies on defaults | Confirmed conditional (only if DSN set). |

## UNVERIFIED / NEEDS-CONTEXT (exact evidence required)

| ID | Sev | Missing evidence |
|----|-----|------------------|
| **P2-01** | MEDIUM | Whether the deployed uvicorn/Render stack makes `request.client.host` a shared proxy IP. Verify by logging `request.client.host` in prod or observing whether two `X-Forwarded-For` values get independent rate buckets. If shared → CONFIRMED (global rate-limit / auth-DoS). |
| **P15 backend CVEs** | ? | `pip-audit` is not installed in the local venv. Run it (CI or `pip install pip-audit && pip-audit`) against the pinned versions listed in `15`. MEMORY's "18 CVE" is stale/unverified. |

## REJECTED (inspected, not a vulnerability)

| Claim | Why rejected |
|-------|--------------|
| SQL injection | All queries parameterized (`?` binds); static DDL. Proven across users/conversations/reports stores. |
| Stored/reflected/DOM XSS | `renderMarkdown` = `marked`→**DOMPurify.sanitize**; chips are digits-only; `SourceList` uses `safeUrl` + text interpolation. |
| IDOR / BOLA (cross-user conversations/reports) | Every per-user route ownership-checked → 404; full matrix in `03`. No reachable cross-user access. |
| LLM prompt-injection → privilege/SQL/command | LLM has no agency; outputs are text or a read-only Pinecone filter over a **public** corpus. (The one real onward risk is P1-02.) |
| ReDoS | Static regex patterns, no catastrophic backtracking; user text is the target not the pattern. |
| Content-Disposition header injection | `_pdf_filename` sanitizes to `[A-Za-z0-9_.-]`. |
| XXE | No XML parser on untrusted input (`strip_html` = stdlib `HTMLParser`). |
| Session fixation | Always server-generated fresh token; no client id adoption. |
| Secrets committed to git | `.env` never committed; only `.env.example` placeholders. |

## Merges applied
- **P4-02 → P1-01** (secrets exposure was via the file-read primitive).
- **P13-01 → P5-01** (watermark-advances-on-partial-failure is one root issue).
- **P7-02 → P11-01** (worker-hold is a consequence of the untimed embed).

## Re-scoring notes
- P1-01 was the only CRITICAL; it is now RESOLVED. Nothing else reaches CRITICAL/HIGH:
  the remaining MEDIUMs are either injection-dependent (P1-02), deployment-dependent
  (P2-01), resilience (P11-01), or defense-in-depth (P14-01/02). No severity was inflated.
