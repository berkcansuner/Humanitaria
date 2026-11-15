# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary:** monitoring and evaluation (M&E) staff in the humanitarian sector. They track the situation in a country or sector, gather sourced evidence, and write reports and briefs. Design decisions favor this group's work first.

**Secondary:** humanitarian analysts, researchers, and journalists who need fast, sourced answers about a crisis.

Typical situations:
- At a desk while writing a report: wide screen, long sessions, several tabs open, frequent copying of quotes and sources.
- Shortly before a meeting or briefing: a few minutes to check the latest state of a country or crisis.

## Product Purpose

Humanitaria answers questions over the ReliefWeb record (reports, disasters, countries) with source-grounded responses, and generates structured M&E situation reports from many reports at once. It exists so that M&E staff spend their time judging evidence, not hunting for it. Success means a user can trust an answer enough to cite it, because they can open the report it came from.

## Positioning

What a general chat assistant or ReliefWeb's own search cannot truthfully claim together:
- **Every claim is sourced.** Answers cite ReliefWeb reports with `[n]` references; seeing, opening, and verifying the source is the core of the product.
- **M&E situation reports.** Country, sector, period, and language selection produces a structured brief that synthesizes many reports, with saved reports and PDF export.
- **Currency.** The index holds the last year of ReliefWeb content, updated automatically every day; answers are date-aware.

## Operating Context

- Routes: `/` landing page, `/login` and `/signup`, `/app` chat (login required), `/reports` M&E report generator, `/settings`, `/admin/ingestion` (owner only).
- Sign-in by email/password or Google; conversations belong to the user and are saved.
- Chat streams token by token (SSE) and shows a source list for each answer.
- Live at https://humanitaria.onrender.com (Render free tier; cold starts are possible).

## Capabilities and Constraints

- UI language is English (global audience); chat is multilingual. Users can ask in Turkish, English, or other languages, and answers follow the user's language. Template system messages (greeting, "no documents found") stay in English on purpose.
- Data: about 9,000 ReliefWeb documents (about 25,000 chunks) across 248 countries, covering the last year (as of 2026-11-15). Older major events can fall outside this window.
- Images and infographics cannot be queried directly; only their title and description are indexed.
- When retrieval finds nothing, the product says so plainly instead of letting the model answer without sources.
- Stack is an existing Vue 3 + Vite SPA served by FastAPI; dark and light themes exist.

## Brand Commitments

- Name: **Humanitaria**. Logo assets: `frontend/src/components/HelpingHandLogo.vue`, `frontend/src/marketing/HandMark.vue`.
- Tagline in use: "Ask the humanitarian record. Get answers you can cite."

## Evidence on Hand

- Real corpus: the live ReliefWeb index described above.
- Real generated output: users' saved M&E reports (private to each user; not for marketing use without permission).
- **None on hand:** testimonials, named customer organizations, usage numbers, press, or benchmarks. Future work must not invent them.

## Product Principles

1. **The source is part of the answer.** Never show a claim in a way that hides where it came from, or makes the reference harder to open than the answer is to read.
2. **Honest about gaps.** Saying "no documents found" or "outside the data window" beats a fluent guess.
3. **Built for the report being written.** Copying, quoting, comparing, and exporting are core jobs, not extras.
4. **Fast to the latest state.** A pre-briefing check should reach the current situation in a few minutes.
5. **M&E work first.** When the needs of M&E staff and those of a broader audience conflict, M&E wins.
