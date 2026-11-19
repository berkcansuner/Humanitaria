import { describe, it, expect } from 'vitest'
import { renderMarkdown, expandCitationGroups } from './renderMarkdown.js'
import { orderCitationRuns } from './citationRuns.js'
import { numberByFirstAppearance, renumberCitations } from './renumberCitations.js'

describe('expandCitationGroups', () => {
  it('expands a comma-separated citation group into adjacent single citations', () => {
    expect(expandCitationGroups('foo [1, 3, 4] bar')).toBe('foo [1][3][4] bar')
  })

  it('handles groups without spaces and multi-digit numbers', () => {
    expect(expandCitationGroups('a [12,3] b')).toBe('a [12][3] b')
  })

  it('leaves single citations and non-citation brackets unchanged', () => {
    expect(expandCitationGroups('one [1] two [note] three')).toBe('one [1] two [note] three')
  })
})

describe('renderMarkdown citations', () => {
  it('renders a multi-citation group as individual clickable chips, not raw text', () => {
    const html = renderMarkdown('Conflict worsened [1, 3, 4].')
    expect(html).toContain('data-cite="1"')
    expect(html).toContain('data-cite="3"')
    expect(html).toContain('data-cite="4"')
    expect(html).not.toContain('[1, 3, 4]')
  })

  it('renders a single citation as a chip (unchanged behavior)', () => {
    expect(renderMarkdown('See [2].')).toContain('data-cite="2"')
  })

  it('strips a citation with no matching source (dangling) instead of leaving dead text', () => {
    // sources only carries index 1; [4] is dangling -> dropped entirely, no chip, no [4]
    const html = renderMarkdown('Valid [1] and dangling [4].', [{ index: 1, url: 'https://x/1' }])
    expect(html).toContain('data-cite="1"')
    expect(html).not.toContain('data-cite="4"')
    expect(html).not.toContain('[4]')
  })

  it('chips the in-source members of a group and strips dangling ones', () => {
    const html = renderMarkdown('Multi [1, 4].', [{ index: 1, url: 'https://x/1' }])
    expect(html).toContain('data-cite="1"')
    expect(html).not.toContain('data-cite="4"')
    expect(html).not.toContain('[4]')
  })
})

describe('renderMarkdown citation names', () => {
  it('names each chip after its source for screen readers', () => {
    const html = renderMarkdown('Needs [1].', [
      { index: 1, url: 'https://x/1', title: 'Access Update', source: 'OCHA', date: '2026-10-21' },
    ])
    expect(html).toContain('aria-label="Source 1: Access Update, OCHA, 21.10.2026"')
  })

  it('falls back to the number while sources are still streaming', () => {
    expect(renderMarkdown('See [2].')).toContain('aria-label="Source 2"')
  })
})

describe('renderMarkdown citation chips stay out of attributes (security audit run-1)', () => {
  it('does not rewrite [n] inside a sanitized attribute value', () => {
    const md = '<span title="[1] <img src=x onerror=alert(1)>">t</span> and [1]'
    const host = document.createElement('div')
    host.innerHTML = renderMarkdown(md)
    expect(host.querySelector('img')).toBeNull()
    expect(host.querySelector('span').getAttribute('title')).toBe(
      '[1] <img src=x onerror=alert(1)>',
    )
    expect(host.querySelectorAll('a.cite').length).toBe(1) // only the text-node citation
  })

  it('does not create elements from a meta-refresh tail in a link title', () => {
    const md =
      '[x](https://example.org "[2] <meta http-equiv=refresh content=0;url=https://evil.test>")'
    const host = document.createElement('div')
    host.innerHTML = renderMarkdown(md)
    expect(host.querySelector('meta')).toBeNull()
  })
})

// Adjacent markers read as one citation run: "[5][2]" shows as chips 2, 5.
describe('orderCitationRuns', () => {
  it('sorts a run of adjacent markers in ascending order', () => {
    expect(orderCitationRuns('lean season [5][2].')).toBe('lean season [2][5].')
    expect(orderCitationRuns('a [3][1] b [10][9][2]')).toBe('a [1][3] b [2][9][10]')
  })

  it('drops a number repeated within the run', () => {
    expect(orderCitationRuns('x [4][2][4]')).toBe('x [2][4]')
    expect(orderCitationRuns('x [2][2]')).toBe('x [2]')
  })

  it('reads markers one space apart as one run, since their chips sit side by side', () => {
    expect(orderCitationRuns('lean season [5] [2].')).toBe('lean season [2][5].')
    expect(orderCitationRuns('x [4] [2][4] y')).toBe('x [2][4] y')
    // Two spaces, a line break or any other character still separates citations.
    const apart = 'a [5]  [2] b [5]\n[2] c [5] and [2]'
    expect(orderCitationRuns(apart)).toBe(apart)
  })

  it('leaves single markers, ordered runs and markers split by other text as they are', () => {
    const text = 'one [3] two [1][2] three [1] [2] four [4], [1] five [5]; [2]'
    expect(orderCitationRuns(text)).toBe(text)
    expect(orderCitationRuns('')).toBe('')
    expect(orderCitationRuns(null)).toBe(null)
  })

  it('orders a comma group once it is expanded', () => {
    expect(orderCitationRuns(expandCitationGroups('rising [5, 2, 5]'))).toBe('rising [2][5]')
  })
})

describe('renderMarkdown orders adjacent citation chips', () => {
  const sources = [1, 2, 3, 4, 5].map((n) => ({
    index: n,
    url: `https://r.int/${n}`,
    title: `S${n}`,
  }))
  const chips = (html) => {
    const div = document.createElement('div')
    div.innerHTML = html
    return [...div.querySelectorAll('.cite')].map((a) => [a.textContent, a.getAttribute('href')])
  }

  it('shows [5][2] as chips 2, 5, each still pointing at its own source', () => {
    expect(chips(renderMarkdown('Needs rose [5][2].', sources))).toEqual([
      ['2', '#src-2'],
      ['5', '#src-5'],
    ])
  })

  it('orders chips written one space apart too ("[5] [2]" read as "5 2")', () => {
    expect(chips(renderMarkdown('Needs rose [5] [2].', sources))).toEqual([
      ['2', '#src-2'],
      ['5', '#src-5'],
    ])
  })

  it('removes a duplicate inside a run', () => {
    expect(chips(renderMarkdown('Vaccination [4][2][4].', sources)).map((c) => c[0])).toEqual([
      '2',
      '4',
    ])
  })

  it('sorts by the displayed number while streaming (after first-appearance numbering)', () => {
    // Raw retrieval numbers: 11 is seen first (-> 1), then the run [13][11] -> [2][1].
    const streamed = numberByFirstAppearance('Access [11]. Food [13][11].')
    expect(streamed).toBe('Access [1]. Food [2][1].')
    expect(chips(renderMarkdown(streamed)).map((c) => c[0])).toEqual(['1', '1', '2'])
  })

  it('sorts by the displayed number once sources renumber the text', () => {
    const raw = [12, 15].map((n) => ({ index: n, url: `https://r.int/${n}`, title: `S${n}` }))
    // 15 appears first (-> 1), so the run [12][15] reads [2][1] before ordering.
    const { content, sources: shown } = renumberCitations('A [15]. B [12][15].', raw)
    expect(content).toBe('A [1]. B [2][1].')
    const out = chips(renderMarkdown(content, shown))
    expect(out.map((c) => c[0])).toEqual(['1', '1', '2'])
    // Chip 2 still opens the source numbered 2 (originally [12]).
    expect(shown.find((s) => s.index === 2).url).toBe('https://r.int/12')
  })

  it('appends a new number at the end of a run that is still streaming', () => {
    // First-appearance numbering makes every new number the largest so far, so a
    // run growing token by token only ever adds a chip at its end.
    const first = numberByFirstAppearance('Food [13]')
    const next = numberByFirstAppearance('Food [13][16]')
    expect(chips(renderMarkdown(first)).map((c) => c[0])).toEqual(['1'])
    expect(chips(renderMarkdown(next)).map((c) => c[0])).toEqual(['1', '2'])
  })
})

// Indicator monitoring reports cite each Indicator Table row in its value cell.
describe('citation chips in table cells', () => {
  const sources = [1, 2, 3, 4].map((n) => ({ index: n, url: `https://r.int/${n}`, title: `S${n}` }))
  const TABLE = [
    'Needs rose sharply [2].',
    '',
    '| Indicator | Latest value | As of |',
    '| --- | --- | --- |',
    '| People in need | 21.9 million [1] | 1 January 2026 |',
    '| Internally displaced people | 3.1 million [4] [3] | 31 January 2026 |',
  ].join('\n')
  const cellChips = (html) => {
    const div = document.createElement('div')
    div.innerHTML = html
    return [...div.querySelectorAll('td')].map((td) =>
      [...td.querySelectorAll('a.cite')].map((a) => [a.textContent, a.getAttribute('href')]),
    )
  }

  it('renders markers in a cell as the same chips as in prose, ordered within a run', () => {
    const html = renderMarkdown(TABLE, sources)
    expect(cellChips(html)).toEqual([
      [],
      [['1', '#src-1']],
      [],
      [],
      [
        ['3', '#src-3'],
        ['4', '#src-4'],
      ],
      [],
    ])
    // Named like any chip, so a keyboard or screen-reader user gets the source.
    const div = document.createElement('div')
    div.innerHTML = html
    expect(div.querySelector('td a.cite').getAttribute('aria-label')).toBe('Source 1: S1')
  })

  it('numbers table citations by first appearance with the prose, while streaming', () => {
    const raw = TABLE.replace('[2]', '[12]').replace('[1]', '[15]').replace('[4] [3]', '[12] [17]')
    expect(numberByFirstAppearance(raw)).toContain('| 21.9 million [2] |')
    expect(numberByFirstAppearance(raw)).toContain('| 3.1 million [1] [3] |')
    expect(cellChips(renderMarkdown(numberByFirstAppearance(raw)))[4].map((c) => c[0])).toEqual([
      '1',
      '3',
    ])
  })
})

describe('a run of chips stays together', () => {
  const sources = [1, 2, 3, 4].map((n) => ({ index: n, url: `https://r.int/${n}`, title: `S${n}` }))
  const parse = (html) => {
    const div = document.createElement('div')
    div.innerHTML = html
    return div
  }

  it('holds the chips of one run in a single unbreakable group', () => {
    const div = parse(
      renderMarkdown('| A | B |\n| --- | --- |\n| x | 3.1 million [4] [3] |', sources),
    )
    const runs = [...div.querySelectorAll('.cite-run')]
    expect(runs).toHaveLength(1)
    expect([...runs[0].querySelectorAll('a.cite')].map((a) => a.textContent)).toEqual(['3', '4'])
  })

  it('leaves a single chip, and chips with words between them, ungrouped', () => {
    const div = parse(renderMarkdown('One [1], two [2] and [3].', sources))
    expect(div.querySelectorAll('.cite-run')).toHaveLength(0)
    expect(div.querySelectorAll('a.cite')).toHaveLength(3)
  })

  it('groups across a dropped marker and keeps one-space runs as written', () => {
    const div = parse(renderMarkdown('Text [1] [2][9].', sources))
    expect([...div.querySelectorAll('.cite-run a.cite')].map((a) => a.textContent)).toEqual([
      '1',
      '2',
    ])
    expect(div.querySelector('.cite-run').textContent).toBe('1 2')
  })
})
