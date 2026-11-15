import { describe, it, expect } from 'vitest'
import { comparisonNote, injectComparisonNote } from './comparisonNote.js'

const HTML =
  '<h2>Executive Summary</h2><p>a</p><h2>What changed since the last report</h2><p>b</p>' +
  '<h2>Key Findings</h2><p>c</p>'

describe('comparisonNote', () => {
  it('names the previous period while checking', () => {
    expect(comparisonNote({ checking: true, period: '2026-07-01 – 2026-09-30' })).toEqual({
      checking: true,
      text: 'Checking against the previous report (2026-07-01 – 2026-09-30)…',
    })
  })

  it('says how many statements the check removed', () => {
    expect(comparisonNote({ removed: 2 }).text).toBe(
      'Checked against the previous report: 2 statements removed because they presented older or undated information as new.',
    )
    expect(comparisonNote({ removed: 1 }).text).toBe(
      'Checked against the previous report: 1 statement removed because it presented older or undated information as new.',
    )
  })

  it('says when nothing was removed', () => {
    expect(comparisonNote({ removed: 0 }).text).toBe(
      'Checked against the previous report: nothing removed.',
    )
  })

  it('has nothing to say for a report that was not checked in this view', () => {
    expect(comparisonNote({})).toBeNull()
    expect(comparisonNote(null)).toBeNull()
  })
})

describe('injectComparisonNote', () => {
  it('puts the note right under the "What changed" heading', () => {
    const out = injectComparisonNote(HTML, { checking: false, text: 'Checked: nothing removed.' })
    expect(out).toContain(
      '<h2>What changed since the last report</h2><p class="compare-note" role="status">Checked: nothing removed.</p><p>b</p>',
    )
    expect(out.match(/compare-note/g).length).toBe(1)
  })

  it('adds a spinner while checking', () => {
    const out = injectComparisonNote(HTML, { checking: true, text: 'Checking…' })
    expect(out).toContain(
      '<p class="compare-note" role="status"><span class="compare-note-spin" aria-hidden="true"></span>Checking…</p>',
    )
  })

  it('finds the Turkish heading', () => {
    const html = '<h2>Son rapordan bu yana neler değişti</h2><p>b</p>'
    expect(injectComparisonNote(html, { text: 'x' })).toContain('</h2><p class="compare-note"')
  })

  it('escapes the note text', () => {
    const out = injectComparisonNote(HTML, { text: '<b>x</b> & y' })
    expect(out).toContain('&lt;b&gt;x&lt;/b&gt; &amp; y')
  })

  it('leaves the html alone without a note or without the section', () => {
    expect(injectComparisonNote(HTML, null)).toBe(HTML)
    expect(injectComparisonNote('<h2>Overview</h2>', { text: 'x' })).toBe('<h2>Overview</h2>')
  })
})
