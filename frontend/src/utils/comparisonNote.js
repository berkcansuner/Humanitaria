/**
 * The note under a next-period report's "What changed" heading.
 *
 * The section streams before it is checked (rag/report_compare.py), and the saved,
 * checked text then replaces the stream, so sentences the reader saw can drop out.
 * The note sits on the section itself: "Checking against the previous report (…)"
 * while the check runs, then how many statements it removed. It belongs to this
 * view of a just-generated report only; a reopened report shows no note.
 */

// The section heading as the report prompt writes it (rag/report_service.py
// COMPARISON_HEADINGS), in each report language.
const HEADINGS = ['What changed since the last report', 'Son rapordan bu yana neler değişti']

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** { checking, text } for the current state, or null when there is nothing to say. */
export function comparisonNote(state) {
  if (!state) return null
  if (state.checking) {
    const period = state.period ? ` (${state.period})` : ''
    return { checking: true, text: `Checking against the previous report${period}…` }
  }
  if (typeof state.removed !== 'number') return null
  if (state.removed === 0) {
    return { checking: false, text: 'Checked against the previous report: nothing removed.' }
  }
  const what =
    state.removed === 1
      ? '1 statement removed because it'
      : `${state.removed} statements removed because they`
  return {
    checking: false,
    text: `Checked against the previous report: ${what} presented older or undated information as new.`,
  }
}

/** The rendered report html with the note right after the "What changed" <h2>. */
export function injectComparisonNote(html, note) {
  if (!html || !note || !note.text) return html
  const spin = note.checking ? '<span class="compare-note-spin" aria-hidden="true"></span>' : ''
  const tag = `<p class="compare-note" role="status">${spin}${escapeHtml(note.text)}</p>`
  for (const heading of HEADINGS) {
    const marker = `<h2>${escapeHtml(heading)}</h2>`
    const i = html.indexOf(marker)
    if (i >= 0) return html.slice(0, i + marker.length) + tag + html.slice(i + marker.length)
  }
  return html
}
