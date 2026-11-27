/**
 * What the waiting state of a report being generated can say truthfully.
 *
 * The server sends nothing between the request and the first word (it searches the
 * index and the report model reads before it
 * writes), so the wait is described by what the pipeline does, the time it usually
 * takes and the sections the report type always has, never by invented progress.
 * Everything here returns keys or numbers; the view translates at render.
 */

// The sections each type's prompt asks for, in order (rag/chain.py report prompts).
const OUTLINES = {
  situation: ['executiveSummary', 'keyFindings', 'outlook'],
  indicator_monitoring: ['overview', 'indicatorTable', 'dataGaps', 'recentDevelopments'],
  needs_assessment: [
    'context',
    'priorityNeeds',
    'affectedGroups',
    'gapsConstraints',
    'recommendations',
  ],
}

/** Section keys (`reports.outline.*`) of a report type. */
export function reportOutline(type) {
  return [...(OUTLINES[type] || OUTLINES.situation)]
}

// "The first words usually appear within two minutes": past that, say it is slow.
export const SLOW_AFTER_S = 120

/** The stage to name (`reports.progress.*`, or `reading`, the viewer's own note).
 * `reading` ({ count, sources }) is what the server's `status` event says before the
 * first word, when it has. */
export function progressStage({ started = false, elapsed = 0, reading = null }) {
  if (started) return 'writing'
  if (elapsed >= SLOW_AFTER_S) return 'slow'
  if (reading) return 'readingCount'
  return 'reading'
}

/** Seconds as a clock: 0:07, 1:32, 10:00. */
export function elapsedClock(seconds) {
  const s = Math.max(0, Math.floor(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
