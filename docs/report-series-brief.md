# Report series: design brief and plan

Status: brief confirmed 2026-11-15 (`/impeccable shape`); not yet implemented.

## Brief

**Job and audience.** An M&E officer who writes the same monitoring report for the
same country and sector every month or quarter, at a desk. Reports is an Operate
surface: speed and trust before expression.

**Outcome.** On a saved report, "Run next period" creates the same report for the
following period. The new report opens with **"What changed since the last report"**
right after its summary: what rose or fell, which risks are new, which are no longer
reported, each claim cited like the rest of the report. Success: no re-entering the
form each month, and no hand-compiled "what changed since last time".

**Direction (inside the Quiet Archive; no new visual language).**
- A series is implicit: reports with the same type + country + sector + language.
  No "create series" step. The saved list folds a series into one row
  ("Afghanistan · Health · 4 reports") that expands to its periods, newest first,
  with mono dates.
- A new report links to the one it continues via `previous_report_id`; the
  comparison uses that link.
- The next period is suggested from the previous report's length (e.g. 3 months)
  and stays editable.
- The comparison reads the previous report's **stored text**, so it works even when
  that period's source documents have aged out of the 12-month index.

**Scope.** In: "Run next period" in the report header, series grouping in the saved
list, the "What changed" section, an editable suggested period. Out: team sharing
(series stay personal), a side-by-side compare view, structured indicator data,
scheduled automatic runs. Untouched: existing report types, PDF, copy with sources,
one-off report generation.

**States and ranges.** 2–6 reports per series typically, about 12 at most (the data
window). First report in a series: no "What changed". Suggested period running past
today: end is clamped to today with a "period not finished yet" note. Start before
the 12-month window: said plainly. Previous report deleted: the link breaks, no
"What changed", and the reason is shown.

**Interaction and layout.** "Run next period" sits beside Copy and PDF in the report
header and opens the form pre-filled with the suggested dates; the user confirms and
generation starts. "What changed" comes right after the summary. Phones keep the
one-pane layout.

**Constraints and open decisions.** New nullable `previous_report_id` column on
`reports` (added at startup like the existing `ADD COLUMN IF NOT EXISTS` columns).
The previous report's text goes to the model as extra context, so comparative runs
cost a little more Gemini time and tokens. To settle while building: the exact
section heading and its Turkish form (reports can be written in Turkish).

## Plan

Each step is its own branch and commit, with tests first for logic and before/after
screenshots for UI (CLAUDE.md rule 6).

1. **Data (backend).** `previous_report_id` column + startup migration (SQLite and
   Postgres); `create_report` stores it; the list and detail APIs return the series
   fields (type, country, theme, language, date_from, date_to, previous_report_id).
   pytest.
2. **Comparative generation (backend).** `ReportRequest.previous_report_id`
   (optional). The route checks the previous report belongs to the user and has the
   same type, country, sector and language. The prompt gets the previous report's
   text, truncated and labelled as *not a source* (no `[n]` citations to it; old
   values are named by period, new values cite current sources), plus a directive to
   write "What changed since the last report" right after the summary. Works for the
   document-based types and the technical (HDX HAPI) type. pytest with a stubbed LLM.
3. **Series in the list (frontend).** `groupSeries()` util (tests): fold same-key
   reports into one expandable row, newest first; single reports stay as today.
4. **Run next period (frontend).** `nextPeriod()` util (tests: length carry-over,
   clamp to today, 12-month window note). Header button fills the form with the
   report's settings and the suggested dates; generation sends `previous_report_id`;
   the viewer names the previous period it compared against.
5. **Check on the live site** (with the owner's go-ahead: it spends Gemini quota):
   generate one next-period report and read the "What changed" section against the
   previous report.
6. DESIGN.md, `/impeccable polish`, then `/impeccable critique` round 3.
