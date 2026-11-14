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
      .join(''),
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
  const fragment = DOMPurify.sanitize(html, { RETURN_DOM_FRAGMENT: true })
  const validIndexes =
    sources && sources.length ? new Set(sources.filter(isValidSource).map((s) => s.index)) : null
  // Turn each [n] into a chip by editing TEXT NODES only. Rewriting the sanitized
  // HTML string also matched [n] inside attribute values and broke out of them.
  // The click handler in Chat.vue scrolls to the matching source within the message.
  const walker = document.createTreeWalker(fragment, NodeFilter.SHOW_TEXT)
  const textNodes = []
  while (walker.nextNode()) textNodes.push(walker.currentNode)
  for (const node of textNodes) {
    const text = expandCitationGroups(node.nodeValue)
    if (!/\[\d+\]/.test(text)) continue
    const parts = document.createDocumentFragment()
    let last = 0
    for (const m of text.matchAll(/( ?)\[(\d+)\]/g)) {
      parts.append(text.slice(last, m.index))
      last = m.index + m[0].length
      // A citation with no displayed source is dropped (with a leading space) rather
      // than left as a dead [n] the reader can't click. During streaming (no sources
      // yet) every [n] is chipped, then re-rendered once sources arrive.
      if (validIndexes && !validIndexes.has(Number(m[2]))) continue
      const a = document.createElement('a')
      a.className = 'cite'
      a.dataset.cite = m[2]
      a.href = `#src-${m[2]}`
      a.textContent = m[2]
      parts.append(m[1], a)
    }
    parts.append(text.slice(last))
    node.replaceWith(parts)
  }
  const out = document.createElement('div')
  out.append(fragment)
  return out.innerHTML
}
