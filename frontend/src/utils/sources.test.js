import { describe, it, expect, vi } from 'vitest'
import {
  isValidSource,
  summarizePublishers,
  ledgerDate,
  revealSource,
  returnToCite,
  citeLabel,
} from './sources.js'

describe('isValidSource', () => {
  it('rejects a source with no url', () => {
    expect(isValidSource({ title: 'X' })).toBe(false)
  })

  it('rejects a country-metadata source whose title equals the country', () => {
    expect(
      isValidSource({ url: 'https://x', doctype: 'country', title: 'Sudan', country: 'Sudan' }),
    ).toBe(false)
  })

  it('accepts a normal source with a url', () => {
    expect(isValidSource({ url: 'https://x/1', title: 'Report' })).toBe(true)
  })
})

describe('summarizePublishers', () => {
  it('lists distinct publishers in first-seen order', () => {
    const sources = [{ source: 'WFP' }, { source: 'OCHA' }, { source: 'WFP' }]
    expect(summarizePublishers(sources)).toBe('WFP, OCHA')
  })

  it('skips sources without a publisher', () => {
    expect(summarizePublishers([{ source: '' }, { source: null }, { source: 'IOM' }])).toBe('IOM')
  })

  it('collapses publishers beyond the limit into a +N count', () => {
    const sources = ['WFP', 'OCHA', 'UNICEF', 'IOM', 'WHO'].map((source) => ({ source }))
    expect(summarizePublishers(sources)).toBe('WFP, OCHA, UNICEF +2')
  })

  it('returns an empty string when no source has a publisher', () => {
    expect(summarizePublishers([{ title: 'A' }])).toBe('')
  })
})

describe('ledgerDate', () => {
  it('keeps the YYYY-MM-DD part of an ISO date', () => {
    expect(ledgerDate('2026-11-03')).toBe('2026-11-03')
    expect(ledgerDate('2026-11-03T08:15:00+00:00')).toBe('2026-11-03')
  })

  it('returns an empty string for a missing or malformed date', () => {
    expect(ledgerDate(null)).toBe('')
    expect(ledgerDate('Nov 2026')).toBe('')
  })
})

describe('revealSource', () => {
  function mount() {
    document.body.innerHTML = `
      <div class="message">
        <details class="sources">
          <summary>2 sources</summary>
          <table><tbody>
            <tr class="source-item active" data-srcid="1"></tr>
            <tr class="source-item" data-srcid="2"></tr>
          </tbody></table>
        </details>
      </div>`
    const container = document.querySelector('.message')
    container.querySelectorAll('.source-item').forEach((el) => {
      el.scrollIntoView = vi.fn()
    })
    return container
  }

  it('opens the collapsed ledger and marks only the cited row active', () => {
    const container = mount()
    expect(revealSource(container, '2')).toBe(true)
    expect(container.querySelector('details.sources').open).toBe(true)
    const rows = container.querySelectorAll('.source-item')
    expect(rows[0].classList.contains('active')).toBe(false)
    expect(rows[1].classList.contains('active')).toBe(true)
    expect(rows[1].classList.contains('flash')).toBe(true)
    expect(rows[1].scrollIntoView).toHaveBeenCalled()
  })

  it('clears the flash after the pulse', () => {
    vi.useFakeTimers()
    const container = mount()
    revealSource(container, '2')
    vi.advanceTimersByTime(1500)
    expect(container.querySelector('[data-srcid="2"]').classList.contains('flash')).toBe(false)
    vi.useRealTimers()
  })

  it('returns false and changes nothing when the source is not shown', () => {
    const container = mount()
    expect(revealSource(container, '9')).toBe(false)
    expect(container.querySelector('details.sources').open).toBe(false)
    expect(container.querySelector('[data-srcid="1"]').classList.contains('active')).toBe(true)
  })

  it('returns false for a missing container', () => {
    expect(revealSource(null, '1')).toBe(false)
  })

  it('centres the row by default and accepts a gentler alignment', () => {
    const container = mount()
    const row = container.querySelector('[data-srcid="2"]')
    revealSource(container, '2')
    expect(row.scrollIntoView).toHaveBeenLastCalledWith({ behavior: 'smooth', block: 'center' })
    revealSource(container, '2', null, { block: 'nearest' })
    expect(row.scrollIntoView).toHaveBeenLastCalledWith({ behavior: 'smooth', block: 'nearest' })
  })
})

describe('returnToCite', () => {
  function setup() {
    document.body.innerHTML = `
      <div class="message">
        <p>Text <a class="cite" data-cite="2" href="#src-2">2</a></p>
        <details class="sources"><summary>1 source</summary><table><tbody>
          <tr class="source-item" data-srcid="2"><td><a class="source-link" href="https://x">T</a></td></tr>
        </tbody></table></details>
      </div>`
    const container = document.querySelector('.message')
    const cite = container.querySelector('.cite')
    const row = container.querySelector('.source-item')
    row.scrollIntoView = vi.fn()
    cite.scrollIntoView = vi.fn()
    return { container, cite, row }
  }

  it('moves focus to the revealed source link, then back to the chip', () => {
    const { container, cite } = setup()
    expect(revealSource(container, '2', cite)).toBe(true)
    expect(document.activeElement).toBe(container.querySelector('.source-link'))
    expect(returnToCite(container)).toBe(true)
    expect(cite.scrollIntoView).toHaveBeenCalled()
    expect(document.activeElement).toBe(cite)
  })

  it('returns false when no chip opened a source here', () => {
    const { container } = setup()
    expect(returnToCite(container)).toBe(false)
    expect(returnToCite(null)).toBe(false)
  })
})

describe('citeLabel', () => {
  it('names the source with title, publisher and ISO date', () => {
    expect(citeLabel('3', { title: 'Bulletin', source: 'WHO', date: '2026-10-09T00:00:00Z' })).toBe(
      'Source 3: Bulletin, WHO, 2026-10-09',
    )
  })

  it('falls back to the number', () => {
    expect(citeLabel('4', null)).toBe('Source 4')
    expect(citeLabel('5', {})).toBe('Source 5')
  })
})
