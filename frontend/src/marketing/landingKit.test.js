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
  peakPhrase,
  monthLabel,
  dayLabel,
  yearChange,
  signedPct,
  axisTicks,
  nearestIndex,
  passage,
  passageSources,
} from './landingKit.js'

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
    expect(peakPhrase(series)).toBe('25% below the Jan 2025 peak')
  })
  it('says "at its peak" when the series ends on its peak', () => {
    expect(
      peakPhrase([
        ['2025-01-31', 5],
        ['2025-02-28', 9],
      ]),
    ).toBe('at its peak')
  })
})

describe('monthLabel and dayLabel', () => {
  it('formats ISO dates in UTC, whatever the local zone', () => {
    expect(monthLabel('2026-09-30')).toBe('Sep 2026')
    expect(monthLabel('2026-02-01')).toBe('Feb 2026')
    expect(dayLabel('2026-01-27')).toBe('27 Jan 2026')
    expect(dayLabel('2026-09-01')).toBe('1 Sep 2026')
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
  it('names each cited publisher once and the newest cited date', () => {
    const parts = [{ text: 'a' }, { cite: 3 }, { cite: 1 }, { text: 'b' }, { cite: 4 }]
    expect(passageSources(parts, sources)).toEqual({
      publishers: ['IOM', 'OCHA'],
      newest: '2026-11-06',
    })
  })
})

describe('the workflow chat sample', () => {
  it('quotes the Haiti answer with its citations 1, 3 and 4', async () => {
    const { parts, sources } = await import('./haitiAnswer.js')
    const sample = passage(parts, 'Nearly 80 percent', 'Grand Sud (39%)')
    expect(sample.filter((p) => p.cite).map((p) => p.cite)).toEqual([1, 3, 4])
    expect(sample[0].text.startsWith('Nearly 80 percent')).toBe(true)
    expect(passageSources(sample, sources)).toEqual({
      publishers: ['OCHA', 'IOM'],
      newest: '2026-11-06',
    })
  })
})
