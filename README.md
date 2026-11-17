# Humanitaria

Humanitaria answers questions about humanitarian crises from ReliefWeb reports, with a
numbered citation on every claim. It is built for monitoring and evaluation (M&E) teams and
humanitarian analysts who have to cite what they write.

**Live demo:** https://humanitaria.onrender.com (free hosting: the first request after a
quiet period can take up to a minute while the server wakes up)

![Humanitaria answering a question with numbered citations and its source list](docs/images/humanitaria-chat.png)

## What it does

- **Cited answers in English or Turkish.** Answers are written only from the reports the
  system retrieves, and each `[n]` opens the original report with its publisher and date. If
  nothing relevant is found, it says so instead of answering from the model's memory. The
  country, sector and dates are picked out of the question and used as search filters.
- **M&E reports.** Pick a country, sector, period and language, then choose one of four
  report types: situation, indicator monitoring, needs assessment or technical monitoring.
  Reports use the same citations, are saved to your account and export to PDF.
- **Statistics computed in code, not by the model.** The technical monitoring report pulls
  indicator series from HDX HAPI and runs the trend and comparison tests in Python (Sen's
  slope, Holm correction). The model only writes them up, and a check removes any sentence
  whose numbers it cannot match to the computed results.
- **A rolling 12-month index.** A scheduled GitHub Actions workflow triggers an incremental
  ingest of new ReliefWeb reports, and reports older than a year are pruned.
- **Accounts.** Email and password or Google sign-in. Deleting an account removes its
  conversations and reports.

## Architecture

```
ReliefWeb API → ingestion pipeline → Postgres + pgvector (Supabase: chunks + documents)
                                            ↓
User → Vue 3 frontend → FastAPI → retrieval (pgvector + MMR + rerank) → Gemini (answer)
                            ↑                 ↑
            query processor (filters)   Gemini embeddings (768-dim)
```

| Layer | Technology |
|---|---|
| Chat and query processing | Google Gemini `gemini-3.5-flash-lite` (OpenAI-compatible endpoint) |
| Reports | Google Gemini `gemini-3.8-flash` |
| Embeddings | Google Gemini `gemini-embedding-001`, truncated to 768 dimensions |
| Vector search | Postgres + pgvector on Supabase (`halfvec(768)`, HNSW index) |
| Reranking | Pinecone Inference `bge-reranker-v2-m3` (rerank API only, no data stored) |
| Indicator data | HDX HAPI |
| Backend | Python 3.12, FastAPI, LangChain (LCEL), server-sent events for streaming |
| Frontend | Vue 3, Vite |
| Hosting and CI | Render (Docker), GitHub Actions |

## Running it locally

Requirements: Python 3.12, Node.js, and a Postgres database with the `vector` extension
(vector search only works on Postgres).

1. Create a virtual environment and install the dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in at least:
   - `GEMINI_API_KEY` for chat, reports and embeddings
   - `DATABASE_URL` for Postgres with pgvector
   - `RELIEFWEB_APPNAME` for the ReliefWeb API

   `PINECONE_API_KEY` is optional. Without it, results keep their retrieval order.
   `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are only needed for Google sign-in. For
   production, set a long random `AUTH_SESSION_SECRET` and `SESSION_COOKIE_SECURE=True`.
3. Enable the `vector` extension in the database (Supabase: Database → Extensions →
   vector). The app creates its tables on first start.
4. Build the frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
5. Start the server, which also serves the built frontend, then open
   http://localhost:8000:
   ```bash
   python -m uvicorn api.main:app
   ```
6. Load some reports:
   ```bash
   python scripts/ingest.py --limit 1000
   ```
   `--date-from YYYY-MM-DD` limits it to newer reports. Ingestion is idempotent, so
   running it twice does not duplicate anything. `--force` clears the index first.

Tests: `python -m pytest tests/ -q` for the backend and `npm test` in `frontend/`.
Deployment notes are in `DEPLOY.md`.

## How it was built

I built Humanitaria with [Claude Code](https://claude.com/claude-code), Anthropic's coding
agent, which wrote most of the code. My part was deciding what to build and checking that
it worked:

- **Product decisions.** I chose who it is for (M&E staff first, then analysts,
  researchers and journalists), what to build and in what order.
- **Architecture and technology choices.** I picked Supabase with pgvector, Gemini, Render
  and GitHub Actions, and kept hosting and the database on free tiers.
- **Quality evaluation.** I decided what counted as good enough and whether a change
  stayed. For retrieval there is a 30-query evaluation set with LLM-judged relevance
  labels: one round of changes raised nDCG@5 from 0.658 to 0.761. For reports, the bar was
  that every cited figure must appear in the report it cites. In one Yemen test, all 62
  did.
- **Live testing.** I used the deployed app myself, found problems and asked for fixes.

A 20-pass security review was part of the work. The summary is in
[docs/security-audit.md](docs/security-audit.md).

## Known limitations

- **Reranker quota.** Pinecone's free plan allows 500 rerank requests a month, shared by
  the live app and evaluation runs. When the quota is used up, results fall back to
  retrieval order. The app keeps working, but ranking quality drops until the monthly
  reset.
- **Free-tier hosting.** The Render instance sleeps when idle, so the first request can be
  slow. The Supabase database is capped at 500 MB, which is why the index keeps only 12
  months of reports and caps how many it keeps per country.
- **ReliefWeb only, text only.** Report bodies are indexed. PDF attachments are skipped by
  default. Images and infographics are searchable only by their title and description.
- **Embedding task type.** Embeddings go through Gemini's OpenAI-compatible endpoint, which
  has no separate query and document modes. This is a small quality trade-off.
- **Silver labels.** The retrieval evaluation set is labelled by an LLM, not by people, so
  the scores are useful for comparing changes, not as absolute numbers.

## Repository layout

```
api/          FastAPI app and routes (auth, chat, conversations, reports, admin)
rag/          embeddings, retrieval, chains, query processing, report generation
ingestion/    ReliefWeb client, parsing, chunking, storage, scheduling, retention
analytics/    HDX HAPI client and statistics for the technical monitoring report
frontend/     Vue 3 app (src/), built into dist/
scripts/      CLI tools: ingest.py, eval_rag.py, build_eval_labels.py
tests/        pytest suite
docs/         security audit summary and design notes
```
