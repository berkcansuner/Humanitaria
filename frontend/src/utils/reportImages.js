/**
 * Inject a report's per-section images into its rendered HTML, right after the
 * matching <h2> heading. Pure string transform (the images are trusted base64
 * data URIs produced server-side). Returns the html unchanged when there are none.
 */
export function injectSectionImages(html, sectionImages) {
  if (!html || !sectionImages || !sectionImages.length) return html
  let out = html
  for (const { heading, image } of sectionImages) {
    if (!heading || !image) continue
    const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(<h2>${escaped}</h2>)`)
    out = out.replace(re, `$1<img class="section-img" src="${image}" alt="" />`)
  }
  return out
}
