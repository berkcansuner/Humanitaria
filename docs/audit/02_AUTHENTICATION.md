# PASS 2 — Authentication & Session Handling

Files: `api/routes/auth.py`, `rag/users.py`, `api/limiter.py`, `api/main.py`
(SessionMiddleware), `api/routes/health.py`.

## Core auth — inspected, STRONG (documented, not findings)

- **Session tokens:** `secrets.token_urlsafe(32)` (256-bit), stored only as SHA-256
  hash (`rag/users.py:155-170`) → a DB leak never exposes live cookies. Expiry checked
  server-side (`get_user_by_session`, line 185-187).
- **Cookie flags** (`_set_session_cookie`, auth.py:97-107): `HttpOnly`, `SameSite=Lax`,
  `Secure` (=`SESSION_COOKIE_SECURE`, true in prod), `Path=/`, bounded `max_age`. Correct.
- **Passwords:** bcrypt w/ per-hash salt; signup bounds 8–72 chars (bcrypt 72-byte cap
  handled). Login runs bcrypt against a real hash OR `DUMMY_PASSWORD_HASH` for
  unknown/password-less emails → **timing side-channel for user enumeration closed**
  (auth.py:159-164). `verify_password` returns False for null hash (Google-only accts).
- **Logout** (auth.py:172-177): deletes the server-side session row AND clears the
  cookie → genuine revocation, not just cookie removal.
- **Session fixation:** every login/signup mints a fresh server-generated token; no
  client-supplied session id is ever adopted. Not vulnerable.
- **Google OAuth** (auth.py:189-268): `authorize_redirect` sets signed state; the
  callback validates `state` via `get_state_data` (**CSRF on the OAuth leg**) and
  clears it (no replay); profile read from the authenticated `userinfo` endpoint
  (JWKS-unreachable workaround — sound, token is Google-issued via the code exchange);
  `email_verified` required before create/link (**blocks unverified-email account
  takeover**); callback is fully `try/except` → fails closed to `/login?error=…`,
  never a 500; account create/link race → `IntegrityError` caught, fail-closed.
- **CSRF (app-wide):** all state-changing endpoints are POST/PATCH/DELETE; there are
  **no state-changing GETs**. With `SameSite=Lax`, the session cookie is not sent on
  cross-site POST/fetch → CSRF is mitigated without separate tokens. Verified by
  enumerating the routers.

## Findings

### [P2-01] Rate limiter likely keys on the proxy IP behind Render → shared bucket

**Status:** UNVERIFIED (NEEDS-CONTEXT: deployed proxy/uvicorn behavior)
**Severity:** MEDIUM
**Confidence:** PLAUSIBLE
**Audit Pass:** 2 (cross-ref 11, 14, 18)

**Location:** `api/limiter.py:13` (`Limiter(key_func=get_remote_address)`) +
`Dockerfile:33` (`uvicorn … --host 0.0.0.0 --port …`, no `--proxy-headers` /
`--forwarded-allow-ips`).

`slowapi.get_remote_address` returns `request.client.host` — the socket peer. Behind
Render's reverse proxy, unless uvicorn is told to trust `X-Forwarded-For` from the
proxy (it is not configured to; uvicorn's `forwarded_allow_ips` defaults to
`127.0.0.1`, and Render's proxy is not that peer), every request appears to come from
**one proxy IP**. Then all per-IP limits (`RATE_LIMIT=20/min` chat,
`AUTH_LOGIN_RATE_LIMIT=5/min`, `AUTH_SIGNUP_RATE_LIMIT=3/min`) become **one shared
global bucket**.

**Impact:** (a) *Availability/DoS* — a single client can exhaust the login bucket
(5/min) and lock **every** user out of login (and the 20/min chat budget) for the
window; (b) legitimate concurrent users trip 429s under modest load; (c) per-attacker
brute-force granularity is lost (though the shared bucket also over-throttles an
attacker, so brute-force is not *weakened*, but distributed brute-force is unaffected).

**Existing controls:** the limiter exists and is wired; the issue is the key source.

**Verification needed:** confirm `request.client.host` on the deployed service (log it
once, or send an `X-Forwarded-For` and observe limit behavior). If it is the proxy IP,
CONFIRMED.

**Remediation (later):** run uvicorn with `--proxy-headers --forwarded-allow-ips=<Render
proxy CIDR>` (NOT `*`, which lets a client spoof the key via XFF), or a custom
`key_func` that reads the left-most XFF entry **only when the peer is the trusted
proxy**. Add a test asserting two different `X-Forwarded-For` values get independent
buckets while an untrusted peer cannot spoof.

### [P2-02] `/health?deep=true` is unauthenticated, unthrottled, and hits paid deps

**Status:** CONFIRMED
**Severity:** LOW
**Audit Pass:** 2 (cross-ref 11)

`api/routes/health.py:31-52` — `/health` has no auth and no rate limit; `?deep=true`
performs a Pinecone `describe_index_stats()` + a SQLite open on every call. An
unauthenticated client can spam `/health?deep=true` to generate Pinecone API traffic
(cost/quota) and DB opens. Liveness (`?deep` absent) is correctly cheap/always-200.
**Remediation:** rate-limit or restrict the deep probe (or cache its result briefly).

### [P2-03] Google auto-link on matching verified email — known product edge case

**Status:** N/A as a new finding (pre-existing documented decision)
**Severity:** LOW / informational

`get_or_create_google_user` links a Google login to a pre-existing password account
when the **Google-verified** email matches. Controlling the verified email is
reasonable proof of ownership, but a reassigned corporate email could let a new
mailbox owner claim the prior account. Already recorded as an open product decision
(MEMORY.md). Not re-reported as new; listed for completeness. Optional hardening: an
explicit link-confirmation step or notification.

## Pass 2 verdict

Auth implementation is notably solid. One MEDIUM (P2-01, deployment/proxy — needs
prod confirmation), one LOW (P2-02), one known informational (P2-03).
