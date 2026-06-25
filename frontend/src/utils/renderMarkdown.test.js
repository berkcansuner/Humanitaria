import { describe, it, expect } from 'vitest'
import { renderMarkdown, expandCitationGroups } from './renderMarkdown.js'

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

  it('does not create a clickable chip for a citation with no matching source (dangling)', () => {
    // sources only carries index 1; [4] is dangling -> stays plain text, no chip
    const html = renderMarkdown('Valid [1] and dangling [4].', [{ index: 1, url: 'https://x/1' }])
    expect(html).toContain('data-cite="1"')
    expect(html).not.toContain('data-cite="4"')
    expect(html).toContain('[4]')
  })

  it('chips only the in-source members of a group, leaving dangling ones plain', () => {
    const html = renderMarkdown('Multi [1, 4].', [{ index: 1, url: 'https://x/1' }])
    expect(html).toContain('data-cite="1"')
    expect(html).not.toContain('data-cite="4"')
  })
})
