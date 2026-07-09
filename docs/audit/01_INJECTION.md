# PASS 1 — Injection & Untrusted Input

Scope: every external-input → dangerous-sink path. Sinks examined: filesystem
(SPA fallback), SQLite, HTML/markdown render (XSS), remote fetch (SSRF), regex
(ReDoS), HTTP headers, and the LLM (prompt injection extension).

Baseline for this pass: 488 backend / 81 frontend tests green.

---

## [P1-01] Unauthenticated path traversal / arbitrary file read via SPA catch-all

> **✅ REMEDIATION APPLIED & VERIFIED (2026-07-09).** Fixed in `api/main.py`
> `spa_fallback`: resolve the candidate and require `is_relative_to(_dist_root)`
> before serving. TDD regression tests in `tests/test_spa_fallback_security.py`
> (3 tests, incl. encoded `..%2f` and a legit-route control). Full suite **491
> passed**. Live re-repro: `/../../.env`, `/../../conversations.db`,
> `/..%2f..%2fconfig.py` now all return `index.html` (481 B) instead of the file.

**Status:** CONFIRMED (live reproduction) → RESOLVED
**Severity:** CRITICAL
**Confidence:** CONFIRMED
**Audit Pass:** 1

**Location**
- file: `api/main.py`
- symbol: `spa_fallback` (the `@app.get("/{full_path:path}")` catch-all)
- lines: 132–137

```python
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    candidate = frontend_dir / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)        # favicon, robots.txt, etc.
    return FileResponse(frontend_dir / "index.html")  # client routes → SPA
```

**Affected execution path**
Unauthenticated GET `/{anything}` → `spa_fallback` → `frontend_dir / full_path`
→ `.is_file()` (OS stat resolves `..`) → `FileResponse(candidate)` streams the
file. There is NO auth dependency, NO containment check that the resolved path is
inside `frontend_dir`, and the `/assets` StaticFiles mount (which *is* traversal-safe)
does not cover this catch-all. `full_path` may contain `..` (literal or percent-encoded
`%2e%2e` / `..%2f`) because uvicorn percent-decodes but does not remove dot segments,
and Starlette's `:path` converter matches `.*` including slashes.

**Trigger**
Any HTTP client that does not client-side-normalize the path (e.g.
`curl --path-as-is`, or any raw client, or encoded segments that survive an
upstream proxy).

**Concrete attack scenario (reproduced locally against this code)**
Server started on `127.0.0.1:8099` (dummy keys, no live calls). Observed:

| Request | Result |
|---------|--------|
| `GET /nonexistent-xyz` (control) | `<!DOCTYPE html>` (index.html — normal) |
| `GET /../../requirements.txt` | served the real file body |
| `GET /..%2f..%2frequirements.txt` | served the real file body (encoded bypass) |
| `GET /../../config.py` | served application source |
| `GET /../../.env` | HTTP 200, 1360 bytes (**all API keys + AUTH_SESSION_SECRET + Google secret**; body deliberately not captured) |
| `GET /../../conversations.db` | HTTP 200, 184320 bytes (**SQLite: bcrypt password hashes, session token hashes, all user emails, every conversation + saved report**) |

**Production impact.** The Dockerfile does NOT copy `.env` into the image, but the
same primitive reads, from `/app/frontend/dist`:
- `../../config.py`, any `.py` — source disclosure
- `../../conversations.db` — the live user DB (created in `/app` at runtime): PII,
  bcrypt hashes (offline-crackable), cross-user conversations & M&E reports
- `../../../../proc/self/environ` — **every environment variable Render injects**,
  i.e. `GEMINI_API_KEY`, `PINECONE_API_KEY`, `GOOGLE_CLIENT_SECRET`,
  `AUTH_SESSION_SECRET`. Disclosure of `AUTH_SESSION_SECRET` additionally lets an
  attacker forge the Starlette-signed OAuth-state/session cookie.

So this is unauthenticated **full secret + full user-data compromise**, plus a
building block for auth bypass. Meets the CRITICAL bar ("broad sensitive-data
compromise", "unauthenticated critical system takeover").

**Observed evidence:** the reproduction table above (curl `--path-as-is`).

**Existing controls checked**
- Auth: none on the catch-all (it is intentionally public to serve the SPA).
- `/assets` uses `StaticFiles` (traversal-safe) — but the catch-all `FileResponse`
  does not, and it is what serves everything else.
- `frontend_dir.exists()` guard only decides whether the route is registered; it
  does not constrain the resolved path.

**Why existing controls are insufficient:** there is simply no containment check;
`FileResponse` serves whatever path it is handed.

**Reachability caveat (production only):** Render's front proxy *might* normalize a
literal `..`. The **percent-encoded** variant (`..%2f`, `%2e%2e`) reproduced above
typically survives proxy normalization (the proxy forwards the encoded form; uvicorn
decodes it), so production exploitation is highly likely but the exact Render proxy
behavior is `NEEDS-CONTEXT`. Any direct-to-uvicorn / self-hosted / local deployment
is unconditionally exploitable. The application-level vulnerability is CONFIRMED
regardless of proxy.

**Reproduction method:** start `uvicorn api.main:app` with a built `frontend/dist`
present; `curl -s --path-as-is 'http://127.0.0.1:PORT/..%2f..%2fconfig.py'`.

**Recommended remediation (remediation phase — not applied during audit)**
Serve the SPA via traversal-safe primitives. Either:
1. Replace the hand-rolled catch-all with `StaticFiles(directory=frontend_dir, html=True)`
   mounted at `/` (its `lookup_path` rejects escapes), or
2. In `spa_fallback`, resolve and contain before serving:
   ```python
   candidate = (frontend_dir / full_path).resolve()
   if full_path and candidate.is_file() and candidate.is_relative_to(frontend_dir.resolve()):
       return FileResponse(candidate)
   return FileResponse(frontend_dir / "index.html")
   ```
   (plus reject `..` segments defensively).

**Regression test that should be added**
An integration test that asserts `GET /../../config.py`, the encoded `..%2f`
variant, and `/../../conversations.db` return the SPA `index.html` (or 404) and
never the traversed file. Must send the raw path (bypass httpx normalization, e.g.
by driving the ASGI app with a hand-built scope whose `path`/`raw_path` contain `..`).

---

## [P1-02] Potential SSRF / local-resource access via xhtml2pdf report rendering

**Status:** PARTIALLY CONFIRMED — **sink reproduced (PASS 20)**; end-to-end LLM-emission trigger PLAUSIBLE
**Severity:** MEDIUM
**Confidence:** CONFIRMED (sink) / PLAUSIBLE (full chain)
**Audit Pass:** 1 (verified PASS 20)

**Location**
- file: `rag/report_pdf.py`
- symbol: `_body_html` (line 120–123) → `render_report_pdf` → `pisa.CreatePDF` (line 164)

**Path.** A saved report's `content` (LLM-generated markdown) is converted with
`markdown.markdown(..., extensions=["extra","sane_lists"])` — Python-Markdown passes
**raw HTML through unsanitized** — then embedded in the PDF HTML and rendered by
`xhtml2pdf` (`pisa.CreatePDF`). xhtml2pdf's default resource loader fetches external
resources (`<img src>`, CSS) via urllib. So report content containing
`<img src="http://169.254.169.254/…">` or a `file://`/local path could cause a
**blind server-side fetch / local-file access** during `GET /reports/{id}/pdf`.

**Reachability.** Auth-gated (own report only), and it requires the LLM to emit an
`<img>`/external-resource tag into the report body — reachable via prompt injection
through the report inputs (`theme`/`date_from`/`date_to` are free-form and unvalidated)
or via indirect injection from retrieved ReliefWeb content. Blind (the fetch result
is not returned), but usable to hit internal metadata endpoints / internal services.

**Existing controls checked.** Sources' `title`/`url`/`meta` ARE `html.escape`d
(lines 107–110), so the Sources table is not an injection vector. The `content` body
is NOT escaped (by design — it is markdown→HTML). No allowlist/`link_callback`
restricting xhtml2pdf resource loading is configured.

**Why controls may be insufficient.** Nothing prevents raw `<img>`/external URLs in
the body from reaching xhtml2pdf's fetcher.

**Verified (PASS 20) — sink CONFIRMED.** A safe local reproducer
(`scratchpad/ssrf_pdf_probe.py`: a 127.0.0.1 listener + `render_report_pdf` with body
`<img src="http://127.0.0.1:8123/ssrf-probe">`) showed: (1) `raw <img> survives markdown:
True` (Python-Markdown passes it through), and (2) **3 inbound connection hits** on the
listener during `render_report_pdf` ("Could not get image data from src attribute:
http://127.0.0.1:8123/ssrf-probe"). So xhtml2pdf **does** fetch remote URLs embedded in
report content. The remaining unproven half is the LLM emitting such an `<img>` (needs a
live prompt-injection attempt — not performed). Severity holds MEDIUM (blind, auth-gated,
LLM-emission-dependent; on Render there is no obvious cloud-metadata endpoint, limiting
blast radius). **Remediation:** pass a restrictive `link_callback` to `pisa.CreatePDF`
that blocks remote/local-file URIs (allow only embedded/`data:`), and/or strip
`<img>`/external refs from the markdown-rendered body before PDF render.

---

## [P1-03] No host allowlist on attachment fetch (SSRF) — low reachability

**Status:** UNVERIFIED (low reachability)
**Severity:** LOW
**Audit Pass:** 1

`ingestion/file_loader.fetch_pdf_text(url)` (line 61–89) does `requests.get(url)`
with no scheme/host allowlist and follows redirects (requests default). The `url`
originates from the ReliefWeb API `file` field (trusted upstream), and the call is
gated by `FETCH_PDF_CONTENT` (default **False**, and off in prod) and runs only in
operator-run ingestion — not a network-facing path. Real-world SSRF would require a
malicious/compromised ReliefWeb response. Documented; not a priority. Hardening:
restrict to `https://…reliefweb.int/…` hosts and disable redirects.

---

## [P1-04] Report inputs partially unvalidated — robustness, minimal injection impact

**Status:** CONFIRMED (validation gap), low injection relevance
**Severity:** LOW
**Audit Pass:** 1 (cross-ref PASS 5 / 17)

`api/routes/reports.py:103` `ReportRequest`: `theme` has no length bound;
`date_from`/`date_to` are free-form `Optional[str]` with no date-format validation.
They flow into the retrieval filter + report directive + stored report (PDF-escaped
on render). No high-impact sink (Pinecone filter is structured; PDF escapes), but
malformed dates degrade retrieval silently and an unbounded `theme` inflates the
LLM prompt. Recommend `date_from/date_to` = validated ISO `date` and a `max_length`
on `theme`.

---

## Inspected and found SAFE (documented, not reported as findings)

- **SQL injection — SAFE.** `rag/users.py`, `rag/conversations.py`, `rag/reports.py`:
  every query uses `?` bind parameters; schema DDL is static `executescript`. No
  string interpolation into SQL anywhere. (Verified by reading all three stores.)
- **XSS — SAFE.** The only two `v-html` sinks (`Chat.vue:54`, `ReportsView.vue:107`)
  route through `renderMarkdown` = `marked.parse` → **`DOMPurify.sanitize`**; the
  post-sanitize citation-chip injection emits digits-only `\d+` anchors. `SourceList.vue`
  renders `src.title` via text interpolation and `src.url` via `safeUrl(...)` with
  `rel="noopener noreferrer"`. Source data is trusted ReliefWeb metadata regardless.
- **Prompt injection / LLM filter manipulation — LOW / no boundary crossed.** The
  chat + query-extraction LLMs have **no agency**: outputs are text (chat answer) or a
  structured **read-only Pinecone metadata filter** over a **public** ReliefWeb corpus.
  No tool calls, no code/SQL execution, no authz decisions. A prompt-injection at worst
  changes which public docs surface / the wording of the attacker's own answer. Indirect
  injection via retrieved content is possible but confined to answer quality. (One
  concrete onward risk — injecting an `<img>` that later reaches the PDF renderer — is
  tracked as P1-02.)
- **ReDoS — SAFE.** Regexes in `query_processor.py` and `_GREETING_PATTERN` use static
  patterns with no nested quantifiers; user input is the search target, not the pattern.
- **HTTP header injection — SAFE.** `reports._pdf_filename` sanitizes to
  `[A-Za-z0-9_.-]` before the `Content-Disposition` header (no CR/LF/quote).
- **XXE — N/A.** `file_loader.strip_html` uses stdlib `HTMLParser` (not an XML parser);
  no user-facing XML parsing in the codebase.

## LLM / AI extension summary

No model-generated command execution, SQL, or filesystem path is executed. The only
model→sink chains are (a) model text → DOMPurify-sanitized HTML (safe) and (b) model
report HTML → xhtml2pdf (tracked as P1-02). Retrieved corpus is public, so no secret
is placed in model context beyond the user's own query + public docs.

## Pass 1 verdict

One **CRITICAL, CONFIRMED** finding (P1-01) — unauthenticated arbitrary file read.
One MEDIUM plausible (P1-02, verify in PASS 20). Two LOW. Core injection classes
(SQLi, XSS, ReDoS, header injection) are genuinely well-defended.
