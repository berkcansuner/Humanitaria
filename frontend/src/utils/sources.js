import { i18n, t } from '../i18n/index.js'

/**
 * Whether a retrieved source should be shown to the user as a citable source.
 *
 * Shared by SourceList (what renders in the panel) and renderMarkdown (which
 * citation [n] markers become clickable chips) so the two never disagree — a
 * chip is only clickable when its source is actually displayed.
 *
 * Drops sources with no url (nothing to link to) and country-metadata entries
 * whose title is just the country name (index artefacts, not real reports).
 */
export function isValidSource(src) {
  if (!src || !src.url) return false
  if (src.doctype === 'country' && src.title === src.country) return false
  return true
}

/**
 * Distinct publishers for the collapsed sources line ("WFP, OCHA, UNICEF +2"),
 * in first-seen order. Sources without a publisher are skipped.
 */
export function summarizePublishers(sources, max = 3) {
  const seen = []
  for (const src of sources || []) {
    const name = src && src.source
    if (name && !seen.includes(name)) seen.push(name)
  }
  const shown = seen.slice(0, max).join(', ')
  return seen.length > max ? `${shown} +${seen.length - max}` : shown
}

/** The YYYY-MM-DD part of an ISO date for the ledger's Date column (a Turkish day-month-year for tr); '' otherwise. */
export function ledgerDate(iso, locale = 'en') {
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(iso || '')
  if (!m) return ''
  const date = new Date(m[1])
  // A calendar overflow (2026-02-30) would roll into the next month: keep it as written.
  if (locale !== 'tr' || isNaN(date) || date.toISOString().slice(0, 10) !== m[1]) return m[1]
  return new Intl.DateTimeFormat('tr-TR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

/** A technical monitoring report's data source (an HDX HAPI dataset), not a document. */
export function isDataSource(src) {
  return !!src && src.doctype === 'dataset'
}

const ISO_DAY = /^\d{4}-\d{2}-\d{2}(?:T[\d:.]+Z?)?$/

/**
 * A dataset's reference period in the ledger's date format for `locale`, both ends
 * joined with an en dash. The backend sends "2024-01-01 – 2026-01-01" or a single
 * date; the older "2024-01-01 to 2026-01-01" and a spaced hyphen read the same. The
 * separator needs spaces round it, so a date's own hyphens never split it. Anything
 * that is not one or two ISO dates is shown exactly as received.
 */
export function dataPeriod(period, locale = 'en') {
  if (!period) return ''
  const text = String(period).trim()
  const ends = text.split(/\s+(?:to|–|—|-)\s+/)
  if (ends.length > 2 || !ends.every((day) => ISO_DAY.test(day))) return text
  return ends.map((day) => ledgerDate(day, locale)).join(' – ')
}

/**
 * What names a data source after its title: the publisher exactly as given (for
 * IOM DTM, its required credit line), the HDX dataset, the period used and the day
 * the figures were retrieved. `retrieved(date)` words the last part in the wanted
 * language; empty parts are left out.
 */
export function dataSourceParts(src, locale, retrieved) {
  return [
    src.source,
    src.dataset,
    dataPeriod(src.period, locale),
    src.retrieved ? retrieved(ledgerDate(src.retrieved, locale) || src.retrieved) : '',
  ].filter(Boolean)
}

// The chip that last opened a source, per container, so "Back to text" can
// return the reader to the exact place they left.
const lastCite = new WeakMap()

/**
 * Reveal the source a citation chip points to, inside `container` (one chat
 * message or the report viewer): open the collapsed sources ledger, mark that
 * row as the single active one, scroll it into view and pulse it briefly.
 * Focus moves to the row's link so keyboard users land on the source; `cite`
 * (the activated chip) is remembered for returnToCite().
 * `block` is the scroll alignment; 'nearest' leaves an already-visible row in place.
 * Returns false (and changes nothing) when that source is not shown.
 */
export function revealSource(container, id, cite = null, { block = 'center' } = {}) {
  const item = container?.querySelector(`.source-item[data-srcid="${id}"]`)
  if (!item) return false
  const ledger = item.closest('details')
  if (ledger) ledger.open = true
  container.querySelectorAll('.source-item.active').forEach((el) => el.classList.remove('active'))
  item.classList.add('active')
  if (cite) lastCite.set(container, cite)
  item.scrollIntoView({ behavior: 'smooth', block })
  item.querySelector('.source-link')?.focus({ preventScroll: true })
  item.classList.add('flash')
  setTimeout(() => item.classList.remove('flash'), 1500)
  return true
}

/** Scroll back to (and focus) the chip that last revealed a source in `container`. */
export function returnToCite(container) {
  const cite = container ? lastCite.get(container) : null
  if (!cite || !cite.isConnected) return false
  cite.scrollIntoView({ behavior: 'smooth', block: 'center' })
  cite.focus({ preventScroll: true })
  return true
}

/**
 * Accessible name for a citation chip in the interface language: "Source 2:
 * Title, Publisher, 2026-10-21" ("Kaynak 2: …, 21 Eki 2026"). Title and publisher
 * are never translated. Read at render, so the label follows a language switch.
 */
export function citeLabel(id, src) {
  const locale = i18n.global.locale.value
  const parts = src ? [src.title, src.source, ledgerDate(src.date, locale)].filter(Boolean) : []
  return parts.length
    ? t('chat.cite.details', { n: id, details: parts.join(', ') })
    : t('chat.cite.number', { n: id })
}
