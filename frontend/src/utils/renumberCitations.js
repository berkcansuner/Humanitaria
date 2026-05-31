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

  const firstPos = (idx) => {
    const at = content.indexOf(`[${idx}]`)
    return at === -1 ? Infinity : at
  }

  // Sources cited in the text come first (in reading order); any uncited
  // sources (the no-citation fallback) keep their relative order at the end.
  const ordered = [...sources].sort((a, b) => firstPos(a.index) - firstPos(b.index))

  const remap = new Map()
  ordered.forEach((s, i) => remap.set(s.index, i + 1))

  // Single pass over the original text: each [old] reads its number and writes
  // the new one, so there is no double-remapping. Unknown markers stay as-is.
  const newContent = content.replace(/\[(\d+)\]/g, (full, n) => {
    const mapped = remap.get(Number(n))
    return mapped != null ? `[${mapped}]` : full
  })

  const newSources = ordered.map((s) => ({ ...s, index: remap.get(s.index) }))
  return { content: newContent, sources: newSources }
}
