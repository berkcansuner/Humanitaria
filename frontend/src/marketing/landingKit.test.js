import { describe, it, expect, afterEach, vi } from 'vitest'
import {
  project,
  pulseRadius,
  countUp,
  onVisible,
  drawablePoints,
  answerLength,
  revealedParts,
  monthsSpan,
  monthLabel,
  passage,
  passageSources,
  citedParts,
  mapLabels,
  formatNumber,
  emphasisParts,
  answerBlocks,
  asOfLabel,
} from './landingKit.js'
import { sampleAnswer, sampleIndicators, sampleReport, samplePassage } from './samples.js'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('project', () => {
  it('maps (0,0) to the centre', () => {
    expect(project(0, 0, 200, 100)).toEqual({ x: 100, y: 50 })
  })
  it('clamps latitude to the drawn band', () => {
    expect(project(90, 0, 200, 100).y).toBe(project(70, 0, 200, 100).y)
    expect(project(-90, 0, 200, 100).y).toBe(project(-70, 0, 200, 100).y)
    expect(project(90, 0, 200, 100).y).toBe(0)
  })
})

describe('pulseRadius', () => {
  it('spans 1.5 to 7 px', () => {
    expect(pulseRadius(0, 100)).toBe(1.5)
    expect(pulseRadius(100, 100)).toBe(7)
  })
  it('is monotonic', () => {
    expect(pulseRadius(25, 100)).toBeLessThan(pulseRadius(50, 100))
    expect(pulseRadius(50, 100)).toBeLessThan(pulseRadius(90, 100))
  })
})

describe('countUp', () => {
  it('finalStateWhenReduced: sets the formatted final text synchronously', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const el = document.createElement('span')
    el.textContent = '0'
    countUp(el, 19_147, { format: (v) => formatNumber(Math.round(v), 'en') })
    expect(el.textContent).toBe('19,147')
  })
})

describe('onVisible', () => {
  it('observes the element and returns a disconnect function', () => {
    const observe = vi.fn()
    const disconnect = vi.fn()
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        observe = observe
        disconnect = disconnect
      },
    )
    const el = document.createElement('div')
    const stop = onVisible(el, () => {})
    expect(observe).toHaveBeenCalledWith(el)
    stop()
    expect(disconnect).toHaveBeenCalled()
  })
})

describe('drawablePoints', () => {
  it('keeps only points with finite lat/lon and reports above zero', () => {
    const ok = { iso3: 'SDN', lat: 15, lon: 30, reports: 10 }
    const noLat = { iso3: 'XXX', lon: 30, reports: 10 }
    const noReports = { iso3: 'YYY', lat: 1, lon: 2, reports: 0 }
    expect(drawablePoints([noLat, noReports, ok])).toEqual([ok])
  })
})

describe('revealedParts', () => {
  const parts = [
    { text: 'Abc ' },
    { text: 'bold', strong: true },
    { cite: 1 },
    { cite: 2 },
    { text: '.' },
  ]

  it('counts only text towards the answer length', () => {
    expect(answerLength(parts)).toBe(9)
  })
  it('cuts the part being typed and hides everything after it', () => {
    expect(revealedParts(parts, 6)).toEqual([{ text: 'Abc ' }, { text: 'bo', strong: true }])
  })
  it('shows citations as soon as the text before them is complete', () => {
    expect(revealedParts(parts, 8)).toEqual(parts.slice(0, 4))
  })
  it('shows nothing at zero and everything at the full length', () => {
    expect(revealedParts(parts, 0)).toEqual([])
    expect(revealedParts(parts, 9)).toEqual(parts)
    expect(revealedParts(parts, 99)).toEqual(parts)
  })
})

describe('formatNumber', () => {
  it('groups digits the way each language writes them', () => {
    expect(formatNumber(19_147)).toBe('19,147')
    expect(formatNumber(19_147, 'tr')).toBe('19.147')
    expect(formatNumber(679, 'tr')).toBe('679')
  })
  it('passes Intl options through', () => {
    expect(formatNumber(0.0275, 'en', { maximumSignificantDigits: 3 })).toBe('0.0275')
    expect(formatNumber(0.0275, 'tr', { maximumSignificantDigits: 3 })).toBe('0,0275')
  })
})

describe('emphasisParts', () => {
  it('turns single-asterisk emphasis into em parts and drops the asterisks', () => {
    expect(emphasisParts([{ text: '. \n\n*(Based on documents.)*' }, { cite: 1 }])).toEqual([
      { text: '. \n\n' },
      { text: '(Based on documents.)', em: true },
      { cite: 1 },
    ])
  })
  it('leaves list markers, bold parts and unpaired asterisks alone', () => {
    const parts = [
      { text: '* ', list_item: true },
      { text: 'Refugees:', strong: true },
      { text: ' 1,803,441* returned' },
    ]
    expect(emphasisParts(parts)).toEqual(parts)
  })
})

describe('answerBlocks', () => {
  it('splits paragraphs on line breaks and gathers list items into one list', () => {
    const parts = [
      { text: 'Intro' },
      { cite: 4 },
      { text: '. \n\nNumbers:\n' },
      { text: '* ', list_item: true },
      { text: 'Refugees:', strong: true },
      { text: ' many' },
      { cite: 1 },
      { text: '. \n' },
      { text: '* ', list_item: true },
      { text: 'IDPs', strong: true },
      { text: '. \n\nWhere' },
      { cite: 2 },
      { text: '.' },
    ]
    expect(answerBlocks(parts)).toEqual([
      { parts: [{ text: 'Intro' }, { cite: 4 }, { text: '. ' }] },
      { parts: [{ text: 'Numbers:' }] },
      {
        items: [
          [{ text: 'Refugees:', strong: true }, { text: ' many' }, { cite: 1 }, { text: '. ' }],
          [{ text: 'IDPs', strong: true }, { text: '. ' }],
        ],
      },
      { parts: [{ text: 'Where' }, { cite: 2 }, { text: '.' }] },
    ])
  })
  it('keeps a partly typed answer in shape', () => {
    expect(answerBlocks([{ text: 'Numbers:\n' }, { text: '* ', list_item: true }])).toEqual([
      { parts: [{ text: 'Numbers:' }] },
      { items: [[]] },
    ])
  })
})

describe('the Syria samples', () => {
  it('pick the answer and the report in the active language, English otherwise', () => {
    expect(sampleAnswer('en').question).toMatch(/^How many Syrian refugees/)
    expect(sampleAnswer('tr').question).toMatch(/^Aralık 2024/)
    expect(sampleAnswer('xx')).toBe(sampleAnswer('en'))
    expect(sampleReport('en').language).toBe('en')
    expect(sampleReport('tr').language).toBe('tr')
    expect(sampleReport('xx')).toBe(sampleReport('en'))
  })
  it('quote a passage of each answer with two of its sources', () => {
    for (const locale of ['en', 'tr']) {
      const { parts, sources } = sampleAnswer(locale)
      const sample = samplePassage(locale)
      expect(sample.filter((p) => p.cite).map((p) => p.cite)).toEqual([1, 2])
      expect(passageSources(sample, sources).map((s) => s.n)).toEqual([1, 2])
      // Verbatim: every quoted text is a stretch of the generated answer.
      const answerText = parts.map((p) => p.text ?? '').join('')
      for (const p of sample) if (p.text) expect(answerText).toContain(p.text)
    }
  })
})

describe('monthLabel', () => {
  it('formats ISO dates in UTC, whatever the local zone', () => {
    expect(monthLabel('2026-09-30')).toBe('Sep 2026')
    expect(monthLabel('2026-02-01')).toBe('Feb 2026')
  })
  it('formats Turkish month names for tr', () => {
    expect(monthLabel('2025-01-28', 'tr')).toBe('Oca 2025')
  })
})

describe('passage', () => {
  const answer = [
    { text: 'Intro ' },
    { cite: 1 },
    { text: '. ' },
    { text: 'Head:', strong: true },
    { text: ' First claim' },
    { cite: 1 },
    { cite: 3 },
    { text: '. Second claim' },
    { cite: 4 },
    { text: '. Later' },
    { cite: 5 },
  ]
  it('takes the text parts from the first match to the last, with the chips after it', () => {
    expect(passage(answer, 'First claim', 'Second claim')).toEqual([
      { text: 'First claim' },
      { cite: 1 },
      { cite: 3 },
      { text: '. Second claim' },
      { cite: 4 },
    ])
  })
  it('throws when the answer no longer contains the passage', () => {
    expect(() => passage(answer, 'Missing', 'Second claim')).toThrow()
  })
})

describe('passageSources', () => {
  const sources = [
    { n: 1, meta: 'OCHA · Haiti', date: '2026-11-06' },
    { n: 3, meta: 'IOM · Haiti', date: '2026-09-25' },
    { n: 4, meta: 'IOM · Haiti', date: '2026-09-21' },
    { n: 5, meta: 'UN Security Council · Haiti', date: '2026-10-20' },
  ]
  it('lists each cited source once, in citation order', () => {
    const parts = [{ text: 'a' }, { cite: 3 }, { cite: 1 }, { text: 'b' }, { cite: 4 }, { cite: 3 }]
    expect(passageSources(parts, sources).map((s) => s.n)).toEqual([3, 1, 4])
  })
})

describe('the workflow chat sample', () => {
  it('opens the quote at its first words, not at the end of the sentence before', () => {
    const parts = [
      { text: 'Earlier sentence' },
      { cite: 3 },
      { text: '. \n\nThe figure is 12' },
      { cite: 1 },
    ]
    expect(passage(parts.slice(2), 'The figure', 'is 12')).toEqual([
      { text: 'The figure is 12' },
      { cite: 1 },
    ])
  })
  it('quotes the Syria answer from its first figure, in each language', () => {
    expect(samplePassage('en')[0].text.startsWith('An estimated 1,803,441')).toBe(true)
    expect(samplePassage('tr')[0].text.startsWith('Güncel verilere göre')).toBe(true)
  })
})

describe('citedParts', () => {
  it('splits [n] markers into chips, dropping the space before each marker', () => {
    expect(citedParts('Out of service [3], while up to 40 per cent [6][7].')).toEqual([
      { text: 'Out of service' },
      { cite: 3 },
      { text: ', while up to 40 per cent' },
      { cite: 6 },
      { cite: 7 },
      { text: '.' },
    ])
  })

  it('keeps text without markers whole', () => {
    expect(citedParts('No citation here.')).toEqual([{ text: 'No citation here.' }])
  })

  it('orders adjacent markers and drops a repeat, like the app', () => {
    expect(citedParts('Lean season [5][2][5].')).toEqual([
      { text: 'Lean season' },
      { cite: 2 },
      { cite: 5 },
      { text: '.' },
    ])
  })
})

// The hero answers are stored as parts, not text: their adjacent chips must already
// read in ascending order, without repeats (a regenerated sample fails here first).
describe('sample answers cite in ascending runs', () => {
  for (const locale of ['en', 'tr']) {
    it(`has no out-of-order or repeated chip run (${locale})`, () => {
      const runs = []
      let run = []
      for (const part of [...sampleAnswer(locale).parts, { text: '' }]) {
        if (part.cite !== undefined) run.push(part.cite)
        else {
          if (run.length > 1) runs.push(run)
          run = []
        }
      }
      for (const r of runs) expect(r).toEqual([...new Set(r)].sort((a, b) => a - b))
    })
  }
})

describe('mapLabels', () => {
  const pt = (iso3, reports, lat, lon) => ({ iso3, name: iso3, reports, lat, lon })

  it('labels the highest-volume points, skipping any that would crowd a stronger label', () => {
    const points = [
      pt('LBN', 750, 33.9, 35.9),
      pt('PSE', 842, 31.9, 35.2),
      pt('SDN', 780, 15, 30),
      pt('YEM', 619, 15.9, 47.6),
      pt('COD', 695, -4, 21.8),
    ]
    expect(mapLabels(points, { count: 3 }).map((p) => p.iso3)).toEqual(['PSE', 'SDN', 'COD'])
  })

  it('never labels a point the map cannot draw', () => {
    const points = [pt('AAA', 900, null, 10), pt('BBB', 0, 5, 5), pt('CCC', 10, 5, 5)]
    expect(mapLabels(points, { count: 3 }).map((p) => p.iso3)).toEqual(['CCC'])
  })
})

describe('monthsSpan', () => {
  it('counts whole months between two ISO dates', () => {
    expect(monthsSpan('2025-11-17', '2026-11-17')).toBe(12)
    expect(monthsSpan('2025-11-18', '2026-11-17')).toBe(11)
    expect(monthsSpan('2026-11-01', '2026-11-17')).toBe(0)
  })
})

describe('asOfLabel', () => {
  it('writes full dates as day.month.year in both languages', () => {
    expect(asOfLabel('12 October 2026')).toBe('12.10.2026')
    expect(asOfLabel('2 Kasım 2026 (yayımlandı)')).toBe('02.11.2026 (yayımlandı)')
    expect(asOfLabel("Aralık 2024'ten itibaren (30 Temmuz 2026 itibarıyla)")).toBe(
      "Aralık 2024'ten itibaren (30.07.2026 itibarıyla)",
    )
  })
  it('leaves months, years and ranges without a day as they are', () => {
    for (const text of ['October 2026', 'end-September 2026', 'Ocak – Eylül 2026', '2026'])
      expect(asOfLabel(text)).toBe(text)
  })
})

describe('the indicator samples', () => {
  it('names the Turkish refugee returns as displaced people from outside the country', () => {
    const names = sampleIndicators('tr', 'hero').rows.map((r) => r.indicator)
    expect(names).toContain('Ülke dışından geri dönen yerinden edilmiş kişi sayısı')
    expect(names.join(' ')).not.toMatch(/sığınmacı/)
  })
  for (const locale of ['en', 'tr']) {
    it(`finds every quoted row in the ${locale} report, cited, and no row twice`, () => {
      const hero = sampleIndicators(locale, 'hero')
      const flow = sampleIndicators(locale, 'flow')
      expect(hero.rows).toHaveLength(3)
      expect(flow.rows).toHaveLength(4)
      const names = [...hero.rows, ...flow.rows].map((r) => r.indicator)
      expect(new Set(names).size).toBe(7)
      for (const { rows, sources } of [hero, flow]) {
        const cited = rows.flatMap((r) => citedParts(r.value).filter((p) => p.cite))
        expect(cited.length).toBeGreaterThanOrEqual(rows.length)
        for (const { cite } of cited) expect(sources.some((s) => s.n === cite)).toBe(true)
        expect(sources.every((s) => cited.some((c) => c.cite === s.n))).toBe(true)
      }
    })
  }
})
