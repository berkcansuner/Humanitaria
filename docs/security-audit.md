# Security audit summary

In July 2026 I ran a 20-pass security and resilience review of the whole repository with
Claude Code: backend, frontend, Docker and deployment config. Each pass covered one area:
injection, authentication, authorization, secrets, error paths, concurrency, external
calls, configuration hardening, dependencies, logging and others. Each finding needed
evidence: a reproduction, a failing test or a code path. I reviewed the findings and
decided what to fix.

## What was found and fixed

**Critical: arbitrary file read through the SPA fallback.** The catch-all route that serves
the Vue app joined the request path onto the build directory without checking where it
ended up, so a request such as `GET /../../.env` (sent with a client that keeps the dot
segments) could return any file the process could read, including secrets and the user
database. I reproduced it against a running server and fixed it the same day. The route
now resolves the path and serves it only if it stays inside the build directory.
Regression tests are in `tests/test_spa_fallback_security.py`, including encoded
`..%2f` paths, and the same requests were re-run after the fix.

**Medium (all fixed):**

- **SSRF in PDF export.** The PDF renderer fetched any URL that appeared in model-written
  report HTML. A link callback now replaces every non-`data:` URI. A test opens a socket
  probe and asserts zero outbound requests (`tests/test_report_pdf_security.py`).
- **No timeout on the embedding client.** A slow embedding call could hold the single
  worker for about 10 minutes. It now times out after 20 seconds.
- **Missing security headers.** A pure-ASGI middleware sets CSP, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy` and HSTS. It is pure ASGI so that streamed
  (SSE) answers are not buffered. The CSP was checked in the browser
  (`tests/test_security_headers.py`).
- **Container ran as root.** The image now runs as an unprivileged user.
- **Rate limiter keyed on the proxy's IP.** Behind Render's proxies every user shared one
  bucket. The limiter now takes the client IP from `X-Forwarded-For` at a configured
  trusted-hop depth, so a client cannot spoof it. Verified live: different clients get
  different buckets.

**Low (fixed):** rate limit on PDF export, a request correlation ID with security event
logging, and `npm audit` dependency updates.

**Accepted:** a few low-severity items were left by choice because they don't apply to a
single-instance deployment of this size. Examples: no cross-instance lock, and unpaginated
conversation lists.

## Since then

The data layer has changed since the audit. Vectors moved from Pinecone to Postgres +
pgvector on Supabase, app data moved from SQLite to the same Postgres, and the nightly
trigger moved from a Cloudflare Worker to GitHub Actions. All the fixes above are still in
the code. The full 20-pass audit has not been re-run against the new data layer.

CI runs `pip-audit`, `ruff`, `mypy`, the backend and frontend test suites, lint and a
production build on every push.
