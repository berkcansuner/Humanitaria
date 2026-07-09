# PASS 4 — Secrets & Sensitive Data Exposure

## Repository hygiene — STRONG (inspected)

- `.env` is **never committed**: `git log --all -- .env` is empty; `git ls-files
  --error-unmatch .env` → not tracked. Only `.env.example` (placeholders) is tracked.
- `.gitignore` covers `.env`, `conversations.db` (+`-wal`/`-shm`), `.last_ingest.json`,
  `.reports_cache.json`, `*.log`, `.claude/`, `.codegraph/`, `venv/`, `node_modules/`.
- `config.py` ships only placeholders (`DEFAULT_SESSION_SECRET="dev-insecure-change-me"`),
  and prod fail-fast rejects the default (`_verify_production_config`). No real secret
  in source.
- `render.yaml` marks all real secrets `sync:false` (dashboard-set, never committed)
  and generates `AUTH_SESSION_SECRET`.
- **Frontend has no client-side secrets** — grep of `frontend/src` shows only password
  form fields, SSE `token` event names, and the httpOnly cookie (browser-managed). No
  API keys, no `VITE_*` secrets, no bearer tokens baked into the bundle.
- **Docker image** copies only `config.py`, `api/`, `rag/`, `ingestion/`, `frontend/dist`
  — not `.env`. Secrets reach the container via Render env vars only.

## Client-facing exposure — inspected, clean

- Chat/report errors return generic messages (`_GENERIC_ERROR_MESSAGE`,
  `_BUSY_MESSAGE`); no stack traces reach the client. `/docs`/`/openapi` hidden in prod.
- `/health?deep` returns only `ok`/`error` per dependency (no secret; but see P2-02 for
  its unauthenticated cost amplification).

## Findings

### [P4-01] Two operator secrets await rotation (operational, not in repo)

**Status:** CONFIRMED (operational) · **Severity:** LOW (repo) / act-now (ops)

Per MEMORY.md, a **Render API key** and a **Google client secret** were pasted into a
past chat session (values NOT written to memory or the repo). They are not in git and
not a code finding, but should be rotated by the user (Render Dashboard → API Keys
revoke+recreate; Google Cloud Console → new client secret → update Render
`GOOGLE_CLIENT_SECRET`). Values redacted here.

### [P4-02] (MERGED into P1-01) Arbitrary file read exposed ALL secrets + PII

The single most severe data-exposure path — unauthenticated read of `.env` /
`/proc/self/environ` / `conversations.db` — was P1-01 (PASS 1), now **fixed & verified**.
Cross-referenced here because its blast radius was primarily secret/PII disclosure:
API keys, `AUTH_SESSION_SECRET`, bcrypt password hashes, user emails, all conversations
and reports. Resolved.

## Privacy (sensitive-domain extension) — inspected

- The RAG **corpus is public** ReliefWeb data; no personal/sensitive data is embedded
  into Pinecone.
- Personal data at rest = user email + name + bcrypt hash + their conversations/reports
  in SQLite (ephemeral on Render free tier). Access is ownership-gated (PASS 3).
- No production data in test fixtures (conftest uses `tmp_path` DBs + a synthetic test
  user). No PII in committed files.
- Logs: no secrets logged; emails not logged (OAuth logs the opaque `sub`, not email);
  see PASS 16 for the Sentry-PII consideration if `SENTRY_DSN` is enabled.

## Pass 4 verdict

Secret hygiene is a clear strength. One operational rotation item (P4-01, already
known); the critical exposure vector was P1-01 (fixed).
