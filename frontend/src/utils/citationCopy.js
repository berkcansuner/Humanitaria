import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { isValidSource, ledgerDate } from './sources.js'
import { expandCitationGroups } from './renderMarkdown.js'
import { safeUrl } from './parseSSE.js'
import { i18n, t } from '../i18n/index.js'

/**
 * "Copy" keeps an answer's evidence: the copied text ends with a numbered
 * reference list, so the [n] markers still point somewhere once pasted into a
 * brief or report (PRODUCT: every claim is sourced, also outside the app).
 * The fixed labels ("Sources", "Untitled") and the date follow the interface
 * language at copy time; source titles and publishers are copied as they are.
 */

const locale = () => i18n.global.locale.value

/** Shown sources that a [n] marker can point to, in citation order. */
export function referenceEntries(sources) {
  return (sources || [])
    .filter((s) => isValidSource(s) && s.index != null)
    .slice()
    .sort((a, b) => a.index - b.index)
}

/** "[2] Sudan Access Update. OCHA, 2026-10-21. https://…" (missing parts dropped). */
export function referenceLine(src) {
  const date = ledgerDate(src.date, locale())
  const meta = [src.source, date].filter(Boolean).join(', ')
  const url = safeUrl(src.url)
  return [
    `[${src.index}] ${src.title || t('chat.sources.untitled')}.`,
    meta ? `${meta}.` : '',
    url !== '#' ? url : '',
  ]
    .filter(Boolean)
    .join(' ')
}

/** Plain-text clipboard payload: the answer markdown plus a "Sources" list. */
export function buildCopyText(markdown, sources) {
  const body = expandCitationGroups(String(markdown || '')).trim()
  const refs = referenceEntries(sources)
  if (!refs.length) return body
  return `${body}\n\n${t('chat.sources.heading')}\n${refs.map(referenceLine).join('\n')}`
}

function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Rich clipboard payload: the rendered answer plus a linked, numbered list. */
export function buildCopyHtml(markdown, sources) {
  const body = marked.parse(expandCitationGroups(String(markdown || '')), {
    gfm: true,
    breaks: true,
  })
  const refs = referenceEntries(sources)
  const list = refs.length
    ? `<p><strong>${esc(t('chat.sources.heading'))}</strong></p><ol>` +
      refs
        .map((s) => {
          const title = esc(s.title || t('chat.sources.untitled'))
          const href = safeUrl(s.url)
          const link = href && href !== '#' ? `<a href="${esc(href)}">${title}</a>` : title
          const meta = [s.source, ledgerDate(s.date, locale())].filter(Boolean).map(esc).join(', ')
          return `<li value="${Number(s.index)}">${link}${meta ? `. ${meta}.` : '.'}</li>`
        })
        .join('') +
      '</ol>'
    : ''
  return DOMPurify.sanitize(body + list)
}

/**
 * Write both payloads to the clipboard (rich where supported, plain text
 * otherwise). Resolves true on success, false when the clipboard is unavailable.
 */
export async function copyWithSources(markdown, sources) {
  const text = buildCopyText(markdown, sources)
  const clip = typeof navigator !== 'undefined' ? navigator.clipboard : null
  if (!clip) return false
  if (clip.write && typeof ClipboardItem !== 'undefined') {
    try {
      const html = buildCopyHtml(markdown, sources)
      await clip.write([
        new ClipboardItem({
          'text/plain': new Blob([text], { type: 'text/plain' }),
          'text/html': new Blob([html], { type: 'text/html' }),
        }),
      ])
      return true
    } catch {
      // Fall through to plain text (e.g. browsers that reject text/html items).
    }
  }
  try {
    await clip.writeText(text)
    return true
  } catch {
    return false
  }
}
