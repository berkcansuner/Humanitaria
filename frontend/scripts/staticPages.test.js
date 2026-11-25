import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { privacyHtml, withStaticContent } from './staticPages.js'
import en from '../src/locales/en.json'
import { PRIVACY_EMAIL } from '../src/contact.js'

// Vitest runs from frontend/.
const indexHtml = readFileSync('index.html', 'utf8')

describe('privacyHtml', () => {
  const html = privacyHtml(en.privacy, PRIVACY_EMAIL)

  it('carries every section of the English policy', () => {
    for (const s of ['s1', 's2', 's3', 's4', 's5', 's6', 's7']) {
      expect(html).toContain(`<h2>${en.privacy[s].title}</h2>`)
    }
    expect(html).toContain('<h1>Privacy policy</h1>')
  })

  it('fills every slot, with the policy link, the cookie and the contact address', () => {
    expect(html).not.toMatch(/\{\w+\}/)
    expect(html).toContain('<code>rw_session</code>')
    expect(html).toContain(
      'href="https://developers.google.com/terms/api-services-user-data-policy"',
    )
    expect(html).toContain(`href="mailto:${PRIVACY_EMAIL}"`)
    expect(html).toContain('Limited Use')
  })

  it('escapes the message text', () => {
    const p = structuredClone(en.privacy)
    p.intro = 'a <b> & c'
    expect(privacyHtml(p, PRIVACY_EMAIL)).toContain('<p>a &lt;b&gt; &amp; c</p>')
  })

  it('fails the build on a slot it does not know', () => {
    const p = structuredClone(en.privacy)
    p.s2.p1 = 'See {nowhere}'
    expect(() => privacyHtml(p, PRIVACY_EMAIL)).toThrow(/nowhere/)
  })
})

describe('withStaticContent', () => {
  it('replaces the home text of the shell with the page text', () => {
    const out = withStaticContent(indexHtml, '<h1>Privacy policy</h1>')
    expect(out).toContain(
      '<noscript id="static-content"><main>\n<h1>Privacy policy</h1>\n</main></noscript>',
    )
    expect(out).not.toContain('Ask the humanitarian record')
    expect(out).toContain('<div id="app"></div>')
  })

  it('refuses a shell without the block', () => {
    expect(() => withStaticContent('<body></body>', 'x')).toThrow(/static-content/)
  })
})

describe('index.html without JavaScript', () => {
  const block = /<noscript id="static-content">([\s\S]*?)<\/noscript>/.exec(indexHtml)[1]

  it('says what the app is for, how Google sign-in is used, and links the policy', () => {
    expect(block).toContain('ReliefWeb')
    expect(block).toContain('Google')
    expect(block).toContain('href="/privacy"')
  })
})
