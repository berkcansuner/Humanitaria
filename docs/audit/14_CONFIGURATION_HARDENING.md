# PASS 14 — Configuration & Environment Hardening

## Inspected — good

- **Prod fail-fast:** `_verify_production_config` aborts startup if `AUTH_SESSION_SECRET`
  is the insecure default in production; `/docs`,`/redoc`,`/openapi` hidden in prod.
- **CORS:** explicit origin list, never `*` with credentials; prod = single origin.
- **Cookies:** `HttpOnly`, `SameSite=Lax`, `Secure` in prod.
- **Secrets:** `render.yaml` `sync:false` for all real secrets; `AUTH_SESSION_SECRET`
  generated; `.env` never in image (selective `COPY`, not `COPY .`).
- **`is_production`** also treats a Secure cookie as prod (conservative).

## Findings

### [P14-01] Container runs as root
**Severity:** MEDIUM (defense-in-depth) · **Confidence:** CONFIRMED

`Dockerfile` has no `USER` directive → the app runs as **root** inside the container. Any
code-execution or file-write bug then operates with root in the container (larger blast
radius; can write anywhere, bind low ports, etc.). Remediation: add a non-root user
(`RUN adduser --system app && USER app`) and ensure the app dir is readable by it.

### [P14-02] No security response headers (CSP, X-Frame-Options, nosniff, HSTS)
**Severity:** MEDIUM · **Confidence:** CONFIRMED

The app sets **no** security headers. Missing:
- **CSP** — defense-in-depth for XSS (DOMPurify mitigates injection, but a CSP is the
  second layer, esp. given LLM-generated HTML rendered via `v-html`).
- **X-Frame-Options / frame-ancestors** — no clickjacking protection on the authed SPA.
- **X-Content-Type-Options: nosniff**, **Referrer-Policy**, **HSTS** (prod is HTTPS).

Remediation: a small middleware adding these (CSP tuned to the SPA's self-hosted assets;
`frame-ancestors 'none'`; `nosniff`; `Strict-Transport-Security` in prod).

### [P14-03] No explicit request-body size limit
**Severity:** LOW · **Confidence:** CONFIRMED

Uvicorn/Starlette impose no default max body size; oversized POST bodies are buffered
before Pydantic rejects them (the 4000-char `message` cap is post-parse). A large body
DoS is possible. Remediation: enforce a max content-length (middleware or reverse-proxy).

### [P14-04] `.dockerignore` — REJECTED (false positive; audit miss)
**Severity:** NIT · **Status:** REJECTED (corrected during remediation)

The original "no `.dockerignore`" claim was **wrong** — the file exists and was not
checked during PASS 14. It already excludes the important items (`.env`,
`conversations.db*`, `.last_ingest.json`, `venv/`, `**/__pycache__/`,
`frontend/node_modules/`, `frontend/dist/`, `tests/`, `docs/`, `*.md`). Minor follow-up
applied: added `.reports_cache.json` for parity with `.last_ingest.json`.

## Pass 14 verdict
Core deploy config (CORS/cookies/fail-fast/secret handling) is solid. Hardening gaps:
container root (P14-01, MEDIUM), missing security headers (P14-02, MEDIUM), no body-size
limit (P14-03), no `.dockerignore` (NIT).
