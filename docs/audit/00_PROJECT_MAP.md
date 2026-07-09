# 00 — Project Map (Phase 0 Reconnaissance)

## Purpose

Multilingual (Turkish/English) RAG chat + M&E situation-report generator over
ReliefWeb humanitarian content, for a humanitarian monitoring & evaluation team.
Deployed at https://humanitaria.onrender.com (Render free tier, Docker).

**Sensitive-data classification:** This is a humanitarian-domain application →
the master prompt's "HEALTHCARE / SENSITIVE-DATA CONDITIONAL MODE" applies.
Increased depth for authorization, cross-user isolation, exports, logs, secrets.
Note however: the *corpus* (ReliefWeb reports) is PUBLIC data. The sensitive
assets are **user accounts** (email + bcrypt password), **per-user conversations**,
and **generated M&E reports** — plus the operational secrets (API keys).

## Languages / frameworks

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI 0.115, uvicorn, Starlette |
| RAG | LangChain LCEL (`langchain` 0.3.24), Gemini via OpenAI-compat endpoint (`langchain-openai`) |
| Vector DB | Pinecone serverless (`langchain-pinecone`, `pinecone` 7.3) |
| Auth | Starlette SessionMiddleware (signed cookie for OAuth state), Authlib (Google OAuth), bcrypt, httpOnly app session cookie |
| Persistence | SQLite (`conversations.db`) — users, sessions, conversations, messages, reports |
| Frontend | Vue 3 + Vite SPA, with two React "islands"; `marked` + `dompurify` for markdown; `vue-router` history mode |
| Rate limiting | slowapi (per-IP) |
| Scheduling | APScheduler (in-process) + external Cloudflare Worker cron |
| Observability | stdlib logging (`dictConfig`), opt-in Sentry |
| PDF export | xhtml2pdf + reportlab |
| CI | GitHub Actions (ruff blocking, pytest+cov blocking, mypy + pip-audit advisory) |
| Deploy | Render Docker (multi-stage: Vue build → FastAPI runtime), auto-deploy on master push |

## Application entry points

- **`api/main.py`** — the ONLY network-facing process. FastAPI app: mounts routers,
  CORS, SessionMiddleware, rate limiter, serves the built SPA via a catch-all
  `GET /{full_path:path}` fallback (line 132-137). Startup `lifespan` warms RAG +
  starts APScheduler (disabled in prod, `INGEST_SCHEDULE_HOURS=0`).
- **CLI scripts** (`scripts/`): `ingest.py`, `setup_pinecone.py`,
  `prune_old_vectors.py`, `backfill_source_urls.py`, `build_eval_labels.py`,
  `eval_rag.py` — operator-run, not network-facing.
- **`cloudflare-cron/worker.js`** — external cron that POSTs to
  `/admin/ingest/cron` with a shared `X-Cron-Token` (currently disabled: token empty).

## HTTP surface (routers under `api/routes/`)

| Router | Prefix | Notes |
|--------|--------|-------|
| `health.py` | `/health` | liveness + `?deep=true` readiness (Pinecone/DB) |
| `auth.py` | `/auth` | email/password signup+login, Google OAuth, session cookie, `/auth/me` |
| `chat.py` | `/chat` | `POST /chat/stream` (SSE) + `POST /chat` — **auth-gated**, rate-limited |
| `conversations.py` | `/conversations` | per-user CRUD of named chats — **auth-gated, ownership-checked** |
| `admin.py` | `/admin` | ingestion status/trigger/documents/cron — **ADMIN_EMAILS-gated** (+ token for cron) |
| `reports.py` | `/reports` | M&E report generate (SSE) + CRUD — **auth-gated** |
| SPA fallback | `GET /{full_path}` | serves `frontend/dist` |

## Data stores

- **Pinecone** (`reliefweb-docs` index, serverless) — public ReliefWeb corpus as
  embedded chunks. Metadata schema per chunk: `doc_id, url, title, country, theme,
  date, date_ts, source, format, doctype`. Namespaces observed: `default`, `v2`,
  `pilot` (per MEMORY.md; `v3` cutover planned).
- **SQLite `conversations.db`** — `rag/users.py` (users + sessions),
  `rag/conversations.py` (conversations + messages), `rag/reports.py` (M&E reports).
  ⚠️ On Render free tier this is **ephemeral** (reset on deploy/sleep).
- **In-memory** — session chat history (`rag/history.py`, LRU) unless `REDIS_URL` set.
- **JSON state files** — `.last_ingest.json` (watermark), `.reports_cache.json`
  (admin doc list). Gitignored, guarded by a local hook.

## AuthN / AuthZ model

- **AuthN:** httpOnly session cookie (`rw_session`) → server-side session row in
  SQLite (`rag/users.py`). Email/password (bcrypt) + Google OAuth (Authlib).
  `AUTH_SESSION_SECRET` signs the *Starlette* session (OAuth state), separate from
  the app session cookie. Prod fail-fast if secret is the insecure default.
- **AuthZ:** two tiers —
  1. **Ownership** — conversations/reports are scoped to `user_id`; must verify
     server-side ownership on read/update/delete (IDOR surface — PASS 3 focus).
  2. **Admin** — `config.ADMIN_EMAILS` allowlist via `get_admin_user` dependency
     (anon→401, non-admin→403). `is_admin` computed server-side.
  3. **Cron token** — `/admin/ingest/cron` gated by `INGEST_TRIGGER_TOKEN` header.

## External calls (leave the process) — for PASS 11

- Gemini chat/embeddings (OpenAI-compat; via Cloudflare AI Gateway in prod)
- Pinecone (query/upsert/list/fetch/describe)
- ReliefWeb API (ingestion)
- Google OAuth (token exchange + userinfo endpoint — JWKS deliberately skipped)
- ReliefWeb file attachments (PDF/HTML) when `FETCH_PDF_CONTENT=True` (SSRF surface)
- xhtml2pdf remote resource fetch (report PDF `<img>` etc. — SSRF surface)

## Background / async execution

- APScheduler in-process ingestion (prod: OFF). `ingestion/runner.py` uses a
  `threading.Lock` so scheduled + manual ingest never overlap.
- Fire-and-forget `asyncio` tasks for manual ingest trigger (`admin.py`).
- SSE streaming generators (chat + reports).

## Known deployment facts (context, from MEMORY.md — verify, don't trust)

- Live on Render; Gemini reached via **Cloudflare AI Gateway** (Render Frankfurt IP
  is blocked by Google's Gemini host).
- Google OAuth callback uses the **userinfo endpoint** (JWKS unreachable from Render).
- Two operator secrets (Render API key, Google client secret) were pasted into a
  past chat and **await manual rotation** — relevant to PASS 4 (were NOT committed).
- Pinecone **write** quota was paused until 2026-07-01; retention/cron code is
  present but PASSIVE (disabled by empty/zero config).
