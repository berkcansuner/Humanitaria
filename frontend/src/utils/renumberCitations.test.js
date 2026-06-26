import { describe, it, expect } from 'vitest'
import { renumberCitations } from './renumberCitations.js'

describe('renumberCitations', () => {
  it('renumbers a lone non-first citation to [1]', () => {
    // Server filtered 5 retrieved docs down to the single cited one (index 3).
    const content = 'En güncel rapor şudur [3].'
    const sources = [{ index: 3, title: 'Rapor 3', url: 'https://reliefweb.int/report/3' }]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('En güncel rapor şudur [1].')
    expect(result.sources).toEqual([
      { index: 1, title: 'Rapor 3', url: 'https://reliefweb.int/report/3' },
    ])
  })

  it('renumbers by order of first appearance in the text', () => {
    const content = 'Önce şu [5], sonra şu [2].'
    const sources = [
      { index: 2, title: 'B', url: 'https://x/2' },
      { index: 5, title: 'A', url: 'https://x/5' },
    ]
    const result = renumberCitations(content, sources)
    // [5] appears first -> becomes [1]; [2] appears second -> becomes [2]
    expect(result.content).toBe('Önce şu [1], sonra şu [2].')
    expect(result.sources).toEqual([
      { index: 1, title: 'A', url: 'https://x/5' },
      { index: 2, title: 'B', url: 'https://x/2' },
    ])
  })

  it('handles a repeated citation marker', () => {
    const content = 'Bir [4]. İki [4]. Üç [2].'
    const sources = [
      { index: 4, title: 'D', url: 'https://x/4' },
      { index: 2, title: 'B', url: 'https://x/2' },
    ]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Bir [1]. İki [1]. Üç [2].')
    expect(result.sources.map(s => s.index)).toEqual([1, 2])
  })

  it('leaves already-contiguous citations unchanged', () => {
    const content = 'A [1]. B [2].'
    const sources = [
      { index: 1, title: 'A', url: 'https://x/1' },
      { index: 2, title: 'B', url: 'https://x/2' },
    ]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('A [1]. B [2].')
    expect(result.sources.map(s => s.index)).toEqual([1, 2])
  })

  it('renumbers sources sequentially when the answer has no citation markers (fallback)', () => {
    const content = 'Genel bir özet, atıf yok.'
    const sources = [
      { index: 2, title: 'B', url: 'https://x/2' },
      { index: 4, title: 'D', url: 'https://x/4' },
    ]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Genel bir özet, atıf yok.')
    expect(result.sources.map(s => s.index)).toEqual([1, 2])
  })

  it('strips a dangling marker that has no matching source', () => {
    // LLM cited [7] but doc 7 never became a source, so the dead bracket is dropped.
    const content = 'Var olan [3]. Eksik [7].'
    const sources = [{ index: 3, title: 'C', url: 'https://x/3' }]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Var olan [1]. Eksik.')
    expect(result.sources.map(s => s.index)).toEqual([1])
  })

  it('strips multiple dangling markers, keeping the one valid source', () => {
    // Model over-cited: only [1] maps to a source; [2][3][4][5] are dropped.
    const content = 'Durum kötü [1] ve [2][3] ayrıca [4][5].'
    const sources = [{ index: 1, title: 'A', url: 'https://x/1' }]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Durum kötü [1] ve ayrıca.')
    expect(result.sources.map(s => s.index)).toEqual([1])
  })

  it('returns input unchanged for empty sources', () => {
    expect(renumberCitations('No sources [1].', [])).toEqual({
      content: 'No sources [1].',
      sources: [],
    })
  })

  it('remaps citation numbers inside a comma-separated group', () => {
    // The model grouped two citations: "[5, 2]". After expansion + remap, [5]
    // appears first -> [1], [2] -> [2], and the group becomes adjacent chips.
    const content = 'Both sources [5, 2] agree.'
    const sources = [
      { index: 2, title: 'B', url: 'https://x/2' },
      { index: 5, title: 'A', url: 'https://x/5' },
    ]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Both sources [1][2] agree.')
    expect(result.sources.map(s => s.index)).toEqual([1, 2])
  })
})
