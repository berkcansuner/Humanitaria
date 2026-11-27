// Pure helpers for the landing page: number and date formatting, map projection,
// sample-answer parsing and the two motion primitives (count-up, visibility).
import { gsap } from 'gsap'
import { orderCitationRuns } from '../utils/citationRuns.js'

const LAT_LIMIT = 70

const INTL_LOCALE = { en: 'en-US', tr: 'tr-TR' }
const intlLocale = (locale) => INTL_LOCALE[locale] ?? INTL_LOCALE.en

// Equirectangular projection; latitude is clamped to the drawn ±70° band.
export function project(lat, lon, w, h) {
  const clamped = Math.max(-LAT_LIMIT, Math.min(LAT_LIMIT, lat))
  return {
    x: ((lon + 180) / 360) * w,
    y: ((LAT_LIMIT - clamped) / (2 * LAT_LIMIT)) * h,
  }
}

// Square-root scale so area, not radius, tracks report volume: 1.5-7 px.
export function pulseRadius(reports, max) {
  const t = max > 0 ? Math.sqrt(Math.max(0, Math.min(reports, max)) / max) : 0
  return 1.5 + t * 5.5
}

// Points the coverage map can draw: finite coordinates and at least one report.
export function drawablePoints(points) {
  return points.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon) && p.reports > 0)
}

// The points the coverage map draws and names: countries only, so the occupied
// Palestinian territory (ReliefWeb's "oPt") is left off the map. The corpus counts
// beside the map still include its reports.
export function mapCountries(points) {
  return points.filter((p) => p.iso3 !== 'PSE')
}

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  )
}

// Calls cb(entry) once the element first intersects; returns a disconnect function.
export function onVisible(el, cb) {
  const observer = new IntersectionObserver(
    (entries) => {
      const entry = entries.find((e) => e.isIntersecting)
      if (!entry) return
      observer.disconnect()
      cb(entry)
    },
    { threshold: 0.2 },
  )
  observer.observe(el)
  return () => observer.disconnect()
}

// Counts the element's text up to `to`. Reduced motion: final text, no tween.
export function countUp(el, to, { duration = 1.2, format = (v) => String(Math.round(v)) } = {}) {
  if (prefersReducedMotion()) {
    el.textContent = format(to)
    return
  }
  const state = { v: 0 }
  gsap.to(state, {
    v: to,
    duration,
    ease: 'power3.out',
    onUpdate: () => {
      el.textContent = format(state.v)
    },
    onComplete: () => {
      el.textContent = format(to)
    },
  })
}

// Characters a streamed answer types out; citation chips cost nothing.
export function answerLength(parts) {
  return parts.reduce((n, p) => n + (p.text?.length ?? 0), 0)
}

// The parts visible after `count` characters: the part being typed is cut,
// chips appear once the text before them is complete.
export function revealedParts(parts, count) {
  const shown = []
  let left = count
  for (const part of parts) {
    if (part.text === undefined) {
      shown.push(part)
      continue
    }
    if (left <= 0) break
    if (part.text.length > left) {
      shown.push({ ...part, text: part.text.slice(0, left) })
      break
    }
    shown.push(part)
    left -= part.text.length
  }
  return shown
}

// Markdown emphasis in generated text ('*(Based on …)*') as em parts, so the answer
// renders italics instead of stray asterisks. List markers and bold parts are kept;
// an asterisk without a closing pair stays as written.
export function emphasisParts(parts) {
  return parts.flatMap((part) => {
    if (part.text === undefined || part.list_item || part.strong) return [part]
    const out = []
    let last = 0
    for (const m of part.text.matchAll(/\*(?!\s)([^*\n]+?)\*/g)) {
      if (m.index > last) out.push({ ...part, text: part.text.slice(last, m.index) })
      out.push({ ...part, text: m[1], em: true })
      last = m.index + m[0].length
    }
    if (!out.length) return [part]
    if (last < part.text.length) out.push({ ...part, text: part.text.slice(last) })
    return out
  })
}

// Answer parts laid out as blocks: paragraphs ({ parts }) and bullet lists
// ({ items: [parts] }). A line break ends the paragraph or item it is in; a
// list_item part starts an item (its marker text is not shown).
export function answerBlocks(parts) {
  const blocks = []
  let open = null // the parts array being filled, or null at a line start
  const push = (part) => {
    if (!open) {
      open = []
      blocks.push({ parts: open })
    }
    open.push(part)
  }
  for (const part of parts) {
    if (part.list_item) {
      let list = blocks[blocks.length - 1]
      if (!list?.items) blocks.push((list = { items: [] }))
      open = []
      list.items.push(open)
      continue
    }
    if (part.text === undefined) {
      push(part)
      continue
    }
    part.text.split('\n').forEach((line, i) => {
      if (i > 0) open = null
      // Spaces left at a line start (after a break) are layout, not text.
      const text = open ? line : line.trimStart()
      if (text) push({ ...part, text })
    })
  }
  return blocks
}

// Whole months from one ISO date to a later one, read in UTC.
export function monthsSpan(from, to) {
  const a = new Date(from)
  const b = new Date(to)
  const months = (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + b.getUTCMonth() - a.getUTCMonth()
  return b.getUTCDate() < a.getUTCDate() ? months - 1 : months
}

const MONTHS = {}
const monthFormat = (locale) =>
  (MONTHS[locale] ??= new Intl.DateTimeFormat(intlLocale(locale), {
    month: 'short',
    timeZone: 'UTC',
  }))

// 'Sep 2026' for an ISO date, read in UTC.
export function monthLabel(iso, locale = 'en') {
  const d = new Date(iso)
  return `${monthFormat(locale).format(d)} ${d.getUTCFullYear()}`
}

const MONTH_NUMBERS = {
  january: 1,
  february: 2,
  march: 3,
  april: 4,
  may: 5,
  june: 6,
  july: 7,
  august: 8,
  september: 9,
  october: 10,
  november: 11,
  december: 12,
  ocak: 1,
  şubat: 2,
  mart: 3,
  nisan: 4,
  mayıs: 5,
  haziran: 6,
  temmuz: 7,
  ağustos: 8,
  eylül: 9,
  ekim: 10,
  kasım: 11,
  aralık: 12,
}

// A report's 'As of' cell with each full date ('12 October 2026', '12 Ekim 2026')
// written as '12.10.2026'. Months and years alone ('October 2026') stay as they are.
export function asOfLabel(text) {
  return text.replace(/\b(\d{1,2}) ([A-Za-zÇĞİÖŞÜçğıöşü]+) (\d{4})\b/g, (all, d, m, y) => {
    const month = MONTH_NUMBERS[m.toLocaleLowerCase('tr')]
    return month ? `${d.padStart(2, '0')}.${String(month).padStart(2, '0')}.${y}` : all
  })
}

// A number with the language's digit grouping and decimal mark ('19,147' / '19.147').
export function formatNumber(n, locale = 'en', options = {}) {
  return new Intl.NumberFormat(intlLocale(locale), options).format(n)
}

// The answer parts from the text part containing `from` through the one
// containing `to`, plus the citation chips that close it. Throws if the answer
// no longer contains the passage, so a quoted excerpt cannot drift silently.
export function passage(parts, from, to) {
  const start = parts.findIndex((p) => p.text?.includes(from))
  const last = parts.findIndex((p, i) => i >= start && p.text?.includes(to))
  if (start < 0 || last < 0) throw new Error(`passage not found: ${from} … ${to}`)
  let end = last + 1
  while (parts[end]?.cite !== undefined) end++
  const out = parts.slice(start, end)
  // The quote opens at `from`, not at the tail of the sentence before it.
  out[0] = { ...out[0], text: out[0].text.slice(out[0].text.indexOf(from)) }
  return out
}

// The sources a passage cites, each once, in citation order.
export function passageSources(parts, sources) {
  const cited = sources.filter((s) => parts.some((p) => p.cite === s.n))
  const order = parts.filter((p) => p.cite !== undefined).map((p) => p.cite)
  return cited.sort((a, b) => order.indexOf(a.n) - order.indexOf(b.n))
}

// A generated sentence's [n] markers as chip parts, in the hero answer's shape:
// 'Out of service [3].' -> [{ text: 'Out of service' }, { cite: 3 }, { text: '.' }].
// Adjacent markers read in ascending order, as in the app ('[5][2]' -> 2, 5).
export function citedParts(sentence) {
  const text = orderCitationRuns(sentence)
  const parts = []
  let last = 0
  for (const m of text.matchAll(/\s*\[(\d+)\]/g)) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) })
    parts.push({ cite: Number(m[1]) })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ text: text.slice(last) })
  return parts
}

// The `count` highest-volume drawable points to name on the map, skipping a point
// whose label would crowd a stronger one (within `minLat` and `minLon` degrees).
export function mapLabels(points, { count, minLat = 8, minLon = 30 }) {
  const picked = []
  for (const p of [...drawablePoints(points)].sort((a, b) => b.reports - a.reports)) {
    if (picked.length === count) break
    const crowded = picked.some(
      (q) => Math.abs(q.lat - p.lat) < minLat && Math.abs(q.lon - p.lon) < minLon,
    )
    if (!crowded) picked.push(p)
  }
  return picked
}
