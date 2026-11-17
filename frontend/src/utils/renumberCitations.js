import { expandCitationGroups } from './renderMarkdown.js'
import { isValidSource } from './sources.js'

/**
 * Renumber inline [n] citation markers and their source list to a contiguous
 * 1..M sequence, ordered by each source's first appearance in the answer text.
 *
 * The backend filters retrieved docs down to the ones the model actually cited
 * but preserves their original 1-based retrieval position, so a lone cited
 * source can end up labelled [3] with no [1]/[2] in sight. This remaps the
 * surviving citations so the panel reads [1], [2], … and the inline markers
 * match.
 *
 * A marker with no matching source (e.g. the model cited a doc that lacked a
 * url/title and never became a source) is left untouched.
 *
 * @param {string} content - the full answer text (citations already streamed)
 * @param {Array<{index:number}>} sources - cited sources carrying original index
 * @returns {{content: string, sources: Array}}
 */
export function renumberCitations(content, sources) {
  if (!sources || sources.length === 0) return { content, sources }

  // Expand "[1, 3]" groups into "[1][3]" so the single-[n] remap below reaches
  // every cited number (otherwise grouped citations keep stale indices).
  content = expandCitationGroups(content)

  // Only sources that render as clickable chips earn a number; markers with no
  // such source are dropped below so the reader never sees a dead [n].
  const valid = sources.filter(isValidSource)

  const firstPos = (idx) => {
    const at = content.indexOf(`[${idx}]`)
    return at === -1 ? Infinity : at
  }

  // Sources cited in the text come first (in reading order); any uncited
  // sources (the no-citation fallback) keep their relative order at the end.
  const ordered = [...valid].sort((a, b) => firstPos(a.index) - firstPos(b.index))

  const remap = new Map()
  ordered.forEach((s, i) => remap.set(s.index, i + 1))

  // Single pass over the original text: each [old] reads its number and writes
  // the new one. A marker with no valid source (the model cited a doc that never
  // became a shown source, or hallucinated a number) is stripped — along with a
  // leading space — so it neither lingers as a dead bracket nor collides with a
  // renumbered marker that happens to reuse its old number.
  const newContent = content.replace(/( ?)\[(\d+)\]/g, (_full, space, n) => {
    const mapped = remap.get(Number(n))
    return mapped != null ? `${space}[${mapped}]` : ''
  })

  const newSources = ordered.map((s) => ({ ...s, index: remap.get(s.index) }))
  return { content: newContent, sources: newSources }
}

/**
 * Number the [n] markers of a still-streaming text 1, 2, 3… in order of first
 * appearance, before its sources are known. The model writes retrieval positions
 * ([15], [16]); renumberCitations (and the server, on save) reorders by first
 * appearance too, so the numbers shown while streaming are the ones that stay.
 *
 * @param {string} content - the text streamed so far
 * @returns {string}
 */
export function numberByFirstAppearance(content) {
  if (!content) return content
  const text = expandCitationGroups(content)
  const order = new Map()
  return text.replace(/\[(\d+)\]/g, (_full, n) => {
    if (!order.has(n)) order.set(n, order.size + 1)
    return `[${order.get(n)}]`
  })
}
