// Pure helpers for the landing page: number formatting, map projection,
// sparkline paths and the two motion primitives (count-up, visibility).
import { gsap } from 'gsap'

const LAT_LIMIT = 70

const round = (n) => Math.round(n * 100) / 100

export function formatCompact(n) {
  const units = [
    [1e9, 'B', 2],
    [1e6, 'M', 1],
    [1e3, 'K', 0],
  ]
  for (const [size, suffix, decimals] of units) {
    if (Math.abs(n) >= size) return `${Number((n / size).toFixed(decimals))}${suffix}`
  }
  return String(Math.round(n))
}

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
  return points.filter(
    (p) => Number.isFinite(p.lat) && Number.isFinite(p.lon) && p.reports > 0,
  )
}

// SVG path `d` for [x, y] points; x spans the points' own range over `w`.
export function linePath(points, w, h, yMin, yMax) {
  if (!points.length) return ''
  const xs = points.map((p) => p[0])
  const xMin = Math.min(...xs)
  const xSpan = Math.max(...xs) - xMin || 1
  const ySpan = yMax - yMin || 1
  return points
    .map(([x, y], i) => {
      const px = round(((x - xMin) / xSpan) * w)
      const py = round(h - ((y - yMin) / ySpan) * h)
      return `${i === 0 ? 'M' : 'L'}${px},${py}`
    })
    .join(' ')
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

// Latest [date, value] against the series peak, as a whole-number percent change.
export function peakChange(series) {
  const peak = series.reduce((a, b) => (b[1] > a[1] ? b : a))
  const latest = series[series.length - 1]
  return { peak, latest, pct: Math.round((latest[1] / peak[1] - 1) * 100) }
}

const MONTH = new Intl.DateTimeFormat('en-US', { month: 'short', timeZone: 'UTC' })

// 'Sep 2026' for an ISO date, read in UTC.
export function monthLabel(iso) {
  const d = new Date(iso)
  return `${MONTH.format(d)} ${d.getUTCFullYear()}`
}

// '27 Jan 2026' for an ISO date, read in UTC.
export function dayLabel(iso) {
  return `${new Date(iso).getUTCDate()} ${monthLabel(iso)}`
}

// The latest value worded against the series peak: '26% below the Jan 2025 peak'.
export function peakPhrase(series) {
  const { peak, latest, pct } = peakChange(series)
  if (latest[1] >= peak[1]) return 'at its peak'
  return `${Math.abs(pct)}% below the ${monthLabel(peak[0])} peak`
}

// Last [year, value] against the year before, as a whole-number percent change.
export function yearChange(series) {
  const [year, value] = series[series.length - 1]
  const prev = series[series.length - 2]
  if (!prev) return { year, value, prevYear: null, pct: null }
  return { year, value, prevYear: prev[0], pct: Math.round((value / prev[1] - 1) * 100) }
}

// '−13%' / '+5%' / '0%', with a true minus sign.
export function signedPct(pct) {
  if (pct < 0) return `−${Math.abs(pct)}%`
  return pct > 0 ? `+${pct}%` : '0%'
}

// Axis ticks every `step`, from the step at or below `lo` to the one at or above `hi`.
export function axisTicks(lo, hi, step) {
  const ticks = []
  for (let t = Math.floor(lo / step) * step; t <= Math.ceil(hi / step) * step; t += step) {
    ticks.push(t)
  }
  return ticks
}

// Index of the value in `xs` closest to `x`.
export function nearestIndex(xs, x) {
  let best = 0
  xs.forEach((v, i) => {
    if (Math.abs(v - x) < Math.abs(xs[best] - x)) best = i
  })
  return best
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
  out[0] = { ...out[0], text: out[0].text.trimStart() }
  return out
}

// Publishers (from `meta`, 'OCHA · Haiti') of the sources a passage cites, each
// once in citation order, and the newest cited date.
export function passageSources(parts, sources) {
  const cited = sources.filter((s) => parts.some((p) => p.cite === s.n))
  const order = parts.filter((p) => p.cite !== undefined).map((p) => p.cite)
  cited.sort((a, b) => order.indexOf(a.n) - order.indexOf(b.n))
  return {
    publishers: [...new Set(cited.map((s) => s.meta.split(' · ')[0]))],
    newest: cited.map((s) => s.date).sort().at(-1),
  }
}
