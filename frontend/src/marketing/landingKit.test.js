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
