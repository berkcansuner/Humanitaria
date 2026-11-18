import { describe, it, expect, afterEach, vi } from 'vitest'
import {
  formatCompact,
  project,
  pulseRadius,
  linePath,
  countUp,
  onVisible,
  drawablePoints,
  answerLength,
  revealedParts,
  peakChange,
  monthsSpan,
  peakPhrase,
  monthLabel,
  dayLabel,
  yearChange,
  signedPct,
  axisTicks,
  nearestIndex,
  passage,
  passageSources,
  citedParts,
  mapLabels,
  periodLabel,
  formatNumber,
  emphasisParts,
  answerBlocks,
} from './landingKit.js'
import { sampleAnswer, sampleReport, samplePassage } from './samples.js'
import { i18n } from '../i18n/index.js'

const tIn = (locale) => (key, params) => i18n.global.t(key, params ?? {}, { locale })

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('formatCompact', () => {
  it('compacts millions, thousands and billions', () => {
    expect(formatCompact(8_580_000)).toBe('8.6M')
    expect(formatCompact(929_250)).toBe('929K')
    expect(formatCompact(1_780_000_000)).toBe('1.78B')
  })
  it('leaves small numbers alone', () => {
    expect(formatCompact(780)).toBe('780')
  })
  it('uses Turkish suffixes and a decimal comma for tr', () => {
    expect(formatCompact(8_585_611, 'tr')).toBe('8,6 Mn')
    expect(formatCompact(1_782_902_647, 'tr')).toBe('1,78 Mr')
    expect(formatCompact(929_250, 'tr')).toBe('929 B')
    expect(formatCompact(780, 'tr')).toBe('780')
  })
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

describe('linePath', () => {
  it('draws a two-point line from bottom-left to top-right', () => {
    expect(
      linePath(
        [
          [0, 0],
          [1, 1],
        ],
        100,
        50,
        0,
        1,
      ),
    ).toBe('M0,50 L100,0')
  })
})

describe('countUp', () => {
  it('finalStateWhenReduced: sets the formatted final text synchronously', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const el = document.createElement('span')
    el.textContent = '0'
    countUp(el, 8_580_000, { format: formatCompact })
    expect(el.textContent).toBe('8.6M')
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

describe('peakChange', () => {
  it('compares the latest value with the series peak', () => {
    const series = [
      ['2023-08-31', 7_000_000],
      ['2025-01-28', 11_600_000],
      ['2026-09-30', 8_700_000],
    ]
    expect(peakChange(series)).toEqual({
      peak: ['2025-01-28', 11_600_000],
      latest: ['2026-09-30', 8_700_000],
      pct: -25,
    })
  })
})

describe('peakPhrase', () => {
  it('words the latest value against the peak month', () => {
    const series = [
      ['2023-08-31', 7_000_000],
      ['2025-01-28', 11_600_000],
      ['2026-09-30', 8_700_000],
    ]
    expect(peakPhrase(series, tIn('en'))).toBe('25% below the Jan 2025 peak')
  })
  it('says "at its peak" when the series ends on its peak', () => {
    expect(
      peakPhrase(
        [
          ['2025-01-31', 5],
          ['2025-02-28', 9],
        ],
        tIn('en'),
      ),
    ).toBe('at its peak')
  })
  it('words the Turkish phrase from the tr messages', () => {
    const series = [
      ['2025-01-28', 11_600_000],
      ['2026-09-30', 8_700_000],
    ]
    expect(peakPhrase(series, tIn('tr'), 'tr')).toBe('Oca 2025 zirvesinin %25 altında')
    expect(peakPhrase(series, tIn('en'))).toBe('25% below the Jan 2025 peak')
    expect(
      peakPhrase(
        [
          ['2025-01-31', 5],
          ['2025-02-28', 9],
        ],
        tIn('tr'),
        'tr',
      ),
    ).toBe('zirvede')
  })
  it('names the peak year, not a month, for an annual series', () => {
    const series = [
      ['2021-01-01', 6_848_865],
      ['2025-01-01', 4_865_764],
    ]
    expect(peakPhrase(series, tIn('en'), 'en', { annual: true })).toBe('29% below the 2021 peak')
    expect(peakPhrase(series, tIn('tr'), 'tr', { annual: true })).toBe(
      '2021 zirvesinin %29 altında',
    )
  })
})

describe('periodLabel', () => {
  it('is the month for a monthly series and the year for an annual one', () => {
    expect(periodLabel('2025-02-28', 'en')).toBe('Feb 2025')
    expect(periodLabel('2025-02-28', 'tr')).toBe('Şub 2025')
    expect(periodLabel('2021-01-01', 'tr', { annual: true })).toBe('2021')
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

describe('monthLabel and dayLabel', () => {
  it('formats ISO dates in UTC, whatever the local zone', () => {
    expect(monthLabel('2026-09-30')).toBe('Sep 2026')
    expect(monthLabel('2026-02-01')).toBe('Feb 2026')
    expect(dayLabel('2026-01-27')).toBe('27 Jan 2026')
    expect(dayLabel('2026-09-01')).toBe('1 Sep 2026')
  })
  it('formats Turkish month names for tr', () => {
    expect(monthLabel('2025-01-28', 'tr')).toBe('Oca 2025')
    expect(dayLabel('2026-11-18', 'tr')).toBe('18 Kas 2026')
  })
})

describe('yearChange', () => {
  it('compares the last year with the one before it', () => {
    const funding = [
      [2023, 1_500_000_000],
      [2024, 2_038_731_400],
      [2025, 1_782_902_647],
    ]
    expect(yearChange(funding)).toEqual({
      year: 2025,
      value: 1_782_902_647,
      prevYear: 2024,
      pct: -13,
    })
  })
  it('has no change for a single year', () => {
    expect(yearChange([[2025, 10]])).toEqual({ year: 2025, value: 10, prevYear: null, pct: null })
  })
})

describe('signedPct', () => {
  it('signs a whole-number percent with a true minus', () => {
    expect(signedPct(-13)).toBe('−13%')
    expect(signedPct(5)).toBe('+5%')
    expect(signedPct(0)).toBe('0%')
  })
  it('puts the percent sign first for tr', () => {
    expect(signedPct(-13, 'tr')).toBe('−%13')
    expect(signedPct(5, 'tr')).toBe('+%5')
    expect(signedPct(0, 'tr')).toBe('%0')
  })
})

describe('axisTicks', () => {
  it('spans the data with whole steps', () => {
    expect(axisTicks(7_071_674, 11_585_384, 2_000_000)).toEqual([
      6_000_000, 8_000_000, 10_000_000, 12_000_000,
    ])
  })
  it('keeps a tick that lands exactly on the data', () => {
    expect(axisTicks(6_000_000, 8_000_000, 2_000_000)).toEqual([6_000_000, 8_000_000])
  })
})

describe('nearestIndex', () => {
  it('finds the closest x', () => {
    expect(nearestIndex([0, 10, 30], 18)).toBe(1)
    expect(nearestIndex([0, 10, 30], 25)).toBe(2)
    expect(nearestIndex([0, 10, 30], -5)).toBe(0)
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
