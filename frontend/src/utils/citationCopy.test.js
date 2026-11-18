import { describe, it, expect, vi, afterEach } from 'vitest'
import { setLocale } from '../i18n/locale.js'
import {
  referenceEntries,
  referenceLine,
  buildCopyText,
  buildCopyHtml,
  copyWithSources,
} from './citationCopy.js'

const sources = [
  {
    index: 2,
    title: 'Sudan Access Update',
    url: 'https://reliefweb.int/report/b',
    source: 'OCHA',
    date: '2026-10-21T08:00:00Z',
  },
  {
    index: 1,
    title: 'Food Security Snapshot',
    url: 'https://reliefweb.int/report/a',
    source: 'WFP',
    date: '2026-11-03',
  },
  { index: 3, title: 'No link' }, // not a valid (shown) source
]

describe('referenceEntries', () => {
  it('keeps shown sources only, in citation order', () => {
    expect(referenceEntries(sources).map((s) => s.index)).toEqual([1, 2])
    expect(referenceEntries(null)).toEqual([])
  })
})

describe('referenceLine', () => {
  it('formats number, title, publisher, ISO date and URL', () => {
    expect(referenceLine(sources[0])).toBe(
      '[2] Sudan Access Update. OCHA, 2026-10-21. https://reliefweb.int/report/b',
    )
  })

  it('drops missing parts and non-http URLs', () => {
    expect(referenceLine({ index: 4, title: 'Bare', url: 'javascript:alert(1)' })).toBe('[4] Bare.')
  })
})

describe('buildCopyText', () => {
  it('appends a numbered Sources list to the answer', () => {
    const text = buildCopyText('Needs are high [1][2].', sources)
    expect(text).toBe(
      'Needs are high [1][2].\n\nSources\n' +
        '[1] Food Security Snapshot. WFP, 2026-11-03. https://reliefweb.int/report/a\n' +
        '[2] Sudan Access Update. OCHA, 2026-10-21. https://reliefweb.int/report/b',
    )
  })

  it('expands grouped citations so every number matches a reference', () => {
    expect(buildCopyText('Rising [1, 2]', [])).toBe('Rising [1][2]')
  })

  it('returns the answer alone when there are no sources', () => {
    expect(buildCopyText('Hello', null)).toBe('Hello')
  })

  it("labels a copied report in the report's language when one is given", () => {
    // English interface, Turkish report: the list reads as part of the Turkish report.
    expect(buildCopyText('Gereksinim yüksek [1].', sources, 'tr')).toContain('\n\nKaynaklar\n')
    expect(buildCopyText('Gereksinim yüksek [1].', sources, 'tr')).toContain('WFP, 3 Kas 2026.')
    expect(buildCopyHtml('Metin [1].', sources, 'tr')).toContain('<strong>Kaynaklar</strong>')
    expect(buildCopyText('Needs [1].', sources, 'en')).toContain('\n\nSources\n')
  })

  describe('in Turkish', () => {
    afterEach(() => {
      setLocale('en')
      localStorage.clear()
    })

    it('labels the list in the interface language and keeps source titles as they are', () => {
      setLocale('tr')
      expect(buildCopyText('Needs are high [1].', sources)).toBe(
        'Needs are high [1].\n\nKaynaklar\n' +
          '[1] Food Security Snapshot. WFP, 3 Kas 2026. https://reliefweb.int/report/a\n' +
          '[2] Sudan Access Update. OCHA, 21 Eki 2026. https://reliefweb.int/report/b',
      )
      expect(referenceLine({ index: 4, url: 'https://x.test/4' })).toBe(
        '[4] Başlıksız. https://x.test/4',
      )
      const html = buildCopyHtml('Text [1].', sources)
      expect(html).toContain('<p><strong>Kaynaklar</strong></p>')
      expect(html).toContain('WFP, 3 Kas 2026.')
    })
  })
})

describe('copied text orders adjacent citations', () => {
  const sources = [2, 5].map((n) => ({ index: n, url: `https://r.int/${n}`, title: `S${n}` }))

  it('writes [5][2] as [2][5] in the plain text and the rich copy', () => {
    expect(buildCopyText('Lean season [5][2].', sources)).toMatch(/^Lean season \[2\]\[5\]\./)
    expect(buildCopyHtml('Lean season [5][2][5].', sources)).toContain('Lean season [2][5].')
  })
})

describe('buildCopyHtml', () => {
  it('renders the answer and a linked, numbered list', () => {
    const html = buildCopyHtml('**High** needs [1].', sources)
    expect(html).toContain('<strong>High</strong>')
    expect(html).toContain('<ol>')
    expect(html).toContain('<li value="1"><a href="https://reliefweb.int/report/a">')
    expect(html).toContain('WFP, 2026-11-03.')
  })

  it('escapes titles and strips unsafe markup', () => {
    const html = buildCopyHtml('<img src=x onerror=alert(1)> ok', [
      { index: 1, title: 'A <b>bold</b> title', url: 'https://x.test/1' },
    ])
    expect(html).not.toContain('onerror')
    expect(html).toContain('A &lt;b&gt;bold&lt;/b&gt; title')
  })
})

describe('copyWithSources', () => {
  const original = navigator.clipboard
  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', { value: original, configurable: true })
  })

  it('falls back to plain text when rich clipboard writes are unavailable', async () => {
    const writeText = vi.fn().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await expect(copyWithSources('Text [1]', sources)).resolves.toBe(true)
    expect(writeText.mock.calls[0][0]).toContain('Sources\n[1] Food Security Snapshot.')
  })

  it('reports failure when there is no clipboard', async () => {
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true })
    await expect(copyWithSources('Text', sources)).resolves.toBe(false)
  })
})

describe('copied tables keep their citations', () => {
  const sources = [3, 4].map((n) => ({ index: n, url: `https://r.int/${n}`, title: `S${n}` }))

  it('copies an Indicator Table row with its markers, a run in order', () => {
    const table = '| Indicator | Latest value |\n| --- | --- |\n| IDPs | 3.1 million [4] [3] |'
    const text = buildCopyText(table, sources)
    expect(text).toContain('| IDPs | 3.1 million [3][4] |')
    expect(text).toContain('[3] S3.')
    expect(buildCopyHtml(table, sources)).toMatch(/<td>3\.1 million \[3\]\[4\]<\/td>/)
  })
})

describe('data sources in the copied list', () => {
  const dataset = {
    index: 1,
    title: 'Food security: people in need',
    url: 'https://data.humdata.org/dataset/global-hpc-hno',
    source: 'OCHA HNO',
    date: '2026-01-01',
    doctype: 'dataset',
    dataset: 'Global Humanitarian Programme Cycle, Humanitarian Needs',
    period: '2024-01-01 to 2026-01-01',
    retrieved: '2026-11-18',
  }

  it('names publisher, dataset, period and retrieval date, in the copy language', () => {
    expect(referenceLine(dataset, 'en')).toBe(
      '[1] Food security: people in need. OCHA HNO, Global Humanitarian Programme Cycle, Humanitarian Needs, 2024-01-01 – 2026-01-01, retrieved 2026-11-18. https://data.humdata.org/dataset/global-hpc-hno',
    )
    expect(referenceLine(dataset, 'tr')).toBe(
      '[1] Food security: people in need. OCHA HNO, Global Humanitarian Programme Cycle, Humanitarian Needs, 1 Oca 2024 – 1 Oca 2026, erişim tarihi 18 Kas 2026. https://data.humdata.org/dataset/global-hpc-hno',
    )
  })

  it('lists them under Sources in the rich copy too', () => {
    const html = buildCopyHtml('Narrative without markers.', [dataset], 'en')
    expect(html).toContain('<li value="1">')
    expect(html).toContain('retrieved 2026-11-18')
    expect(buildCopyText('Narrative without markers.', [dataset], 'en')).toContain(
      '\n\nSources\n[1] ',
    )
  })
})
