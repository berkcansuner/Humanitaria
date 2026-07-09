# PASS 15 — Dependency & Supply Chain

## Posture — good hygiene
- `requirements.txt` is **fully pinned** (exact `==`); `frontend/package-lock.json`
  present and the image builds with `npm ci` (reproducible). Base images `python:3.12-slim`,
  `node:20-slim` (current majors, tag-pinned not digest-pinned). No install-time scripts,
  no git-URL/unknown-registry deps, no obviously typosquatted names.

## Backend CVEs — NEEDS-CONTEXT
`pip-audit` is pinned in `requirements.txt` but **not installed in the local venv**
(`No module named pip_audit`), so no fresh local result was captured. CI runs `pip-audit`
as an advisory (`continue-on-error`) step; MEMORY.md notes a prior "18 CVE / 9 packages"
advisory result (transitive, non-blocking) — **unverified here**. To confirm, run in CI or
`pip install pip-audit && pip-audit`. Exact versions to check (critical-path libs):
`langchain 0.3.24`, `langchain-community 0.3.22`, `langchain-openai 0.3.14`,
`langchain-pinecone 0.2.13`, `pinecone 7.3.0`, `fastapi 0.115.9`, `authlib 1.7.2`,
`bcrypt 5.0.0`, `httpx 0.28.1`, `requests 2.32.3`, `pypdf 6.14.2`, `xhtml2pdf 0.2.17`,
`reportlab 4.5.1`, `sentry-sdk 2.20.0`.

## Frontend CVEs — captured (`npm audit`, 7 vulns: 1 critical / 2 high / 4 moderate)

| Package | Advisory | In-context impact |
|---------|----------|-------------------|
| **dompurify** | GHSA-cmwh-pvxp-8882 — `ALLOWED_ATTR` pollution via `setConfig()` | **Not in the used path** — app calls `DOMPurify.sanitize(html)` with **default config**, no `setConfig`/hooks. Update anyway (it's our XSS defense). Non-breaking `npm audit fix`. |
| **esbuild** ≤0.24.2 (→ vite/vitest/vite-node) | GHSA-67mh-4wv8-2f99 — dev server accepts any-origin requests | **Dev-only** (devDependencies; not in the prod bundle — prod is a static `vite build`). Fix requires vite major bump (breaking); low priority. |
| **form-data** 4.0.0–4.0.5 | GHSA-hmw2-7cc7-3qxx — CRLF injection in multipart field names | **Transitive, not used** — the frontend sends JSON `fetch`, no multipart. Non-breaking `npm audit fix`. |

## Findings
### [P15-01] Run the recommended dependency fixes / capture a fresh backend audit
**Severity:** LOW · Frontend: apply non-breaking `npm audit fix` (dompurify, form-data);
schedule the vite/vitest major bump separately (dev-only). Backend: capture a real
`pip-audit` run (NEEDS-CONTEXT) and triage any actionable transitive CVE. Consider
SHA-pinning CI actions and base-image digests (NIT, supply-chain).

## Pass 15 verdict
Pinned + lockfile'd + reproducible — good baseline. Frontend advisories are dev-only or
not-in-the-used-path (LOW). Backend CVE status is NEEDS-CONTEXT (tool not installed locally).
