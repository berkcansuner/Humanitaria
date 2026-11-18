/**
 * The note under a next-period report's "What changed" heading.
 *
 * The section streams before it is checked (rag/report_compare.py), and the saved,
 * checked text then replaces the stream, so sentences the reader saw can drop out.
 * The note sits on the section itself: "Checking against the previous report (…)"
 * while the check runs, then how many statements it removed. It belongs to this
 * view of a just-generated report only; a reopened report shows no note.
 *
 * The note is the app's status message to the reader, not part of the report, so
 * it is in the interface language (`t` defaults to the app's i18n) even under a
 * heading in another report language.
 */
import { i18n, t as appT } from '../i18n/index.js'

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

/**
 * { checking, text, lang } for the current state, or null when there is nothing to
 * say. `lang` is the language the text is written in (the interface's), for the
 * note's own lang attribute inside a report body in another language.
 */
export function comparisonNote(state, t = appT, lang = i18n.global.locale.value) {
  if (!state) return null
  if (state.checking) {
    const text = state.period
      ? t('reports.compare.checkingPeriod', { period: state.period })
      : t('reports.compare.checking')
    return { checking: true, text, lang }
  }
  if (typeof state.removed !== 'number') return null
  if (state.removed === 0) return { checking: false, text: t('reports.compare.none'), lang }
  return {
    checking: false,
    text: t('reports.compare.removed', { n: state.removed }, state.removed),
    lang,
  }
}

/** The rendered report html with the note right after the "What changed" <h2>. */
export function injectComparisonNote(html, note) {
  if (!html || !note || !note.text) return html
  const spin = note.checking ? '<span class="compare-note-spin" aria-hidden="true"></span>' : ''
  const lang = note.lang ? ` lang="${escapeHtml(note.lang)}"` : ''
  const tag = `<p class="compare-note"${lang} role="status">${spin}${escapeHtml(note.text)}</p>`
  for (const heading of HEADINGS) {
    const marker = `<h2>${escapeHtml(heading)}</h2>`
    const i = html.indexOf(marker)
    if (i >= 0) return html.slice(0, i + marker.length) + tag + html.slice(i + marker.length)
  }
  return html
}
