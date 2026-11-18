import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { decorateCodeBlocks } from './codeCopy.js'
import { setLocale } from '../i18n/locale.js'

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
    const btn = root.querySelector('button.copy-code')
    expect(btn.textContent).toBe('Copy')
    expect(btn.getAttribute('aria-label')).toBe('Copy code')
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

  describe('in Turkish', () => {
    afterEach(() => {
      setLocale('en')
      localStorage.clear()
    })

    it('labels the button in the interface language', () => {
      setLocale('tr')
      const root = makeRoot('<pre><code>print(1)</code></pre>')
      decorateCodeBlocks(root)
      const btn = root.querySelector('button.copy-code')
      expect(btn.textContent).toBe('Kopyala')
      expect(btn.getAttribute('aria-label')).toBe('Kodu kopyala')
    })

    it('relabels an existing button when run again after a language switch', () => {
      const root = makeRoot('<pre><code>print(1)</code></pre>')
      decorateCodeBlocks(root)
      setLocale('tr')
      decorateCodeBlocks(root)
      expect(root.querySelectorAll('button.copy-code')).toHaveLength(1)
      expect(root.querySelector('button.copy-code').getAttribute('aria-label')).toBe('Kodu kopyala')
    })

    it('shows "Copied" in the interface language, then returns to the current label', async () => {
      vi.useFakeTimers()
      vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockResolvedValue() } })
      setLocale('tr')
      const root = makeRoot('<pre><code>print(1)</code></pre>')
      decorateCodeBlocks(root)
      const btn = root.querySelector('button.copy-code')
      btn.click()
      expect(btn.textContent).toBe('Kopyalandı')
      await vi.advanceTimersByTimeAsync(1500)
      expect(btn.textContent).toBe('Kopyala')
      vi.useRealTimers()
      vi.unstubAllGlobals()
    })
  })
})
