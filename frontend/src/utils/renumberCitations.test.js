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

  it('leaves a dangling marker with no matching source untouched', () => {
    // LLM cited [7] but doc 7 had no url/title, so it never became a source.
    const content = 'Var olan [3]. Eksik [7].'
    const sources = [{ index: 3, title: 'C', url: 'https://x/3' }]
    const result = renumberCitations(content, sources)
    expect(result.content).toBe('Var olan [1]. Eksik [7].')
    expect(result.sources.map(s => s.index)).toEqual([1])
  })

  it('returns input unchanged for empty sources', () => {
    expect(renumberCitations('No sources [1].', [])).toEqual({
      content: 'No sources [1].',
      sources: [],
    })
  })
})
