import { describe, it, expect } from 'vitest'
import { injectSectionImages } from './reportImages.js'

describe('injectSectionImages', () => {
  it('inserts an <img> after the matching <h2>', () => {
    const html = '<h2>Overview</h2><p>text</p><h2>Outlook</h2><p>x</p>'
    const out = injectSectionImages(html, [
      { heading: 'Overview', image: 'data:image/png;base64,AAA' },
    ])
    expect(out).toContain('<h2>Overview</h2><img')
    expect(out).toContain('src="data:image/png;base64,AAA"')
    // only the matched heading gets an image
    expect(out.match(/<img/g).length).toBe(1)
  })

  it('is a no-op with no section images', () => {
    const html = '<h2>Overview</h2><p>text</p>'
    expect(injectSectionImages(html, null)).toBe(html)
    expect(injectSectionImages(html, [])).toBe(html)
  })

  it('skips a heading not present in the html', () => {
    const html = '<h2>Overview</h2>'
    const out = injectSectionImages(html, [{ heading: 'Missing', image: 'data:...' }])
    expect(out).toBe(html)
  })

  it('matches a heading with special chars against marked-escaped HTML', () => {
    // marked escapes '&' to '&amp;' in the rendered <h2>, so the matcher must too.
    const html = '<h2>Food Security &amp; Livelihoods</h2><p>x</p>'
    const out = injectSectionImages(html, [
      { heading: 'Food Security & Livelihoods', image: 'data:image/png;base64,AAA' },
    ])
    expect(out).toContain('</h2><img')
    expect(out).toContain('src="data:image/png;base64,AAA"')
  })
})
