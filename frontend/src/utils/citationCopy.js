import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { isValidSource, ledgerDate } from './sources.js'
import { expandCitationGroups } from './renderMarkdown.js'
import { orderCitationRuns } from './citationRuns.js'
import { safeUrl } from './parseSSE.js'
import { i18n, t } from '../i18n/index.js'

/**
 * "Copy" keeps an answer's evidence: the copied text ends with a numbered
 * reference list, so the [n] markers still point somewhere once pasted into a
 * brief or report (PRODUCT: every claim is sourced, also outside the app).
 * The fixed labels ("Sources", "Untitled") and the date follow the interface
 * language at copy time, or `lang` when given (a saved report is copied in its
 * own language, like its PDF); source titles and publishers are copied as they are.
 */

const LABEL_LANGS = ['en', 'tr']
const locale = (lang) => (LABEL_LANGS.includes(lang) ? lang : i18n.global.locale.value)
const label = (key, lang, params = {}) => t(key, params, { locale: locale(lang) })

// After the title: publisher and date.
function metaParts(src, lang) {
  return [src.source, ledgerDate(src.date, locale(lang))].filter(Boolean)
}

/** Shown sources that a [n] marker can point to, in citation order. */
export function referenceEntries(sources) {
  return (sources || [])
    .filter((s) => isValidSource(s) && s.index != null)
    .slice()
    .sort((a, b) => a.index - b.index)
}

/** "[2] Sudan Access Update. OCHA, 2026-10-21. https://…" (missing parts dropped). */
export function referenceLine(src, lang) {
  const meta = metaParts(src, lang).join(', ')
  const url = safeUrl(src.url)
  return [
    `[${src.index}] ${src.title || label('chat.sources.untitled', lang)}.`,
    meta ? `${meta}.` : '',
    url !== '#' ? url : '',
  ]
    .filter(Boolean)
    .join(' ')
}

/** Plain-text clipboard payload: the answer markdown plus a "Sources" list. */
export function buildCopyText(markdown, sources, lang) {
  const body = orderCitationRuns(expandCitationGroups(String(markdown || ''))).trim()
  const refs = referenceEntries(sources)
  if (!refs.length) return body
  const lines = refs.map((s) => referenceLine(s, lang)).join('\n')
  return `${body}\n\n${label('chat.sources.heading', lang)}\n${lines}`
}

function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Rich clipboard payload: the rendered answer plus a linked, numbered list. */
export function buildCopyHtml(markdown, sources, lang) {
  const body = marked.parse(orderCitationRuns(expandCitationGroups(String(markdown || ''))), {
    gfm: true,
    breaks: true,
  })
  const refs = referenceEntries(sources)
  const list = refs.length
    ? `<p><strong>${esc(label('chat.sources.heading', lang))}</strong></p><ol>` +
      refs
        .map((s) => {
          const title = esc(s.title || label('chat.sources.untitled', lang))
          const href = safeUrl(s.url)
          const link = href && href !== '#' ? `<a href="${esc(href)}">${title}</a>` : title
          const meta = metaParts(s, lang).map(esc).join(', ')
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
 * `lang` names the language of the fixed labels (default: the interface's).
 */
export async function copyWithSources(markdown, sources, { lang } = {}) {
  const text = buildCopyText(markdown, sources, lang)
  const clip = typeof navigator !== 'undefined' ? navigator.clipboard : null
  if (!clip) return false
  if (clip.write && typeof ClipboardItem !== 'undefined') {
    try {
      const html = buildCopyHtml(markdown, sources, lang)
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
