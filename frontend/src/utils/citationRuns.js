// Citation runs, kept free of the markdown renderer so the landing page can use
// them without loading marked and DOMPurify.

/**
 * Order each run of citation markers by number and drop a number that repeats
 * within the run, so a reader sees chips 2, 5 rather than 5, 2:
 *   "lean season [5][2]" -> "lean season [2][5]"
 *   "lean season [5] [2]" -> "lean season [2][5]"
 * A run is markers that touch or stand one space apart: their chips render side by
 * side either way. Two spaces, a line break, punctuation or words separate citations.
 * A run already in order is left exactly as written. Applied to text whose numbers
 * are the ones displayed (after renumbering), so the order matches what is shown and
 * each [n] keeps pointing at source n.
 */
export function orderCitationRuns(text) {
  if (!text) return text
  return text.replace(/\[\d+\](?: ?\[\d+\])+/g, (run) => {
    const numbers = run.match(/\d+/g).map(Number)
    const ordered = [...new Set(numbers)].sort((a, b) => a - b)
    if (ordered.length === numbers.length && ordered.every((n, i) => n === numbers[i])) return run
    return ordered.map((n) => `[${n}]`).join('')
  })
}
