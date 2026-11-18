// Citation runs, kept free of the markdown renderer so the landing page can use
// them without loading marked and DOMPurify.

/**
 * Order each run of adjacent citation markers by number and drop a number that
 * repeats within the run, so a reader sees chips 2, 5 rather than 5, 2:
 *   "lean season [5][2]" -> "lean season [2][5]"
 * Applied to text whose numbers are the ones displayed (after renumbering), so the
 * order matches what is shown and each [n] keeps pointing at source n. Markers
 * separated by anything, even a space, are separate citations and stay put.
 */
export function orderCitationRuns(text) {
  if (!text) return text
  return text.replace(/\[\d+\](?:\[\d+\])+/g, (run) =>
    [...new Set(run.match(/\d+/g).map(Number))]
      .sort((a, b) => a - b)
      .map((n) => `[${n}]`)
      .join(''),
  )
}
