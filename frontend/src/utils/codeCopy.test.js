import { describe, it, expect, beforeEach, vi } from 'vitest'
import { decorateCodeBlocks } from './codeCopy.js'

function makeRoot(html) {
  const root = document.createElement('div')
  root.innerHTML = html
  return root
}

describe('decorateCodeBlocks', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('appends a copy button to each pre block', () => {
    const root = makeRoot('<pre><code>print(1)</code></pre><pre><code>x=2</code></pre>')
    decorateCodeBlocks(root)
    expect(root.querySelectorAll('button.copy-code')).toHaveLength(2)
  })

  it('does not double-decorate when called twice', () => {
    const root = makeRoot('<pre><code>print(1)</code></pre>')
    decorateCodeBlocks(root)
    decorateCodeBlocks(root)
    expect(root.querySelectorAll('button.copy-code')).toHaveLength(1)
  })

  it('ignores a null root', () => {
    expect(() => decorateCodeBlocks(null)).not.toThrow()
  })

  it('copies the code text when the button is clicked', async () => {
    const writeText = vi.fn().mockResolvedValue()
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const root = makeRoot('<pre><code>print(1)</code></pre>')
    decorateCodeBlocks(root)
    root.querySelector('button.copy-code').click()
    expect(writeText).toHaveBeenCalledWith('print(1)')
  })
})
