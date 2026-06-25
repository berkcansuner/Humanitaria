import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { isValidSource } from './sources.js'

/**
 * Expand a comma-separated citation group into adjacent single citations so the
 * single-[n] machinery (chip injection + renumbering) handles every number:
 *   "deteriorated [1, 3, 4]" -> "deteriorated [1][3][4]"
 * Single citations and non-numeric brackets (e.g. "[note]") are left untouched.
 */
export function expandCitationGroups(text) {
  if (!text) return text
  return text.replace(/\[(\d+(?:\s*,\s*\d+)+)\]/g, (_full, group) =>
    group
      .split(',')
      .map((n) => `[${n.trim()}]`)
      .join('')
  )
}

/**
 * Render answer markdown to safe HTML and turn citation markers [n] into
 * clickable green chips.
 *
 * @param {string} text - the answer markdown (citations already renumbered)
 * @param {Array<{index:number}>} [sources] - displayed sources; when provided,
 *   only citations with a matching valid source become clickable chips, so a
 *   number the model cited but that has no shown source stays plain text rather
 *   than a chip whose click goes nowhere. Omit (streaming) to chip every [n].
 */
export function renderMarkdown(text, sources = null) {
  if (!text) return ''
  const html = marked.parse(text, { gfm: true, breaks: true })
  const clean = DOMPurify.sanitize(html)
  // Expand groups, then turn each [n] into a chip. Done AFTER sanitize so the
  // injected anchors (digits only — no injection risk) are not stripped; the
  // click handler in Chat.vue scrolls to the matching source within the message.
  const expanded = expandCitationGroups(clean)
  const validIndexes =
    sources && sources.length
      ? new Set(sources.filter(isValidSource).map((s) => s.index))
      : null
  return expanded.replace(/\[(\d+)\]/g, (full, n) => {
    if (validIndexes && !validIndexes.has(Number(n))) return full
    return `<a class="cite" data-cite="${n}" href="#src-${n}">${n}</a>`
  })
}
