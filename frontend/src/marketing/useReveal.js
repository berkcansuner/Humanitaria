import { onMounted, onBeforeUnmount } from 'vue'

/**
 * Scroll-reveal for marketing pages. Mirrors the prototype's IntersectionObserver:
 * elements that start well below the fold fade/slide in as they enter the viewport.
 * Staggers children of grid groups. No-ops when IntersectionObserver is missing
 * or the user prefers reduced motion (CSS already neutralises .reveal in that case).
 *
 * @param {import('vue').Ref<HTMLElement|null>} rootRef  page root element ref
 */
export function useReveal(rootRef) {
  let io = null

  onMounted(() => {
    const root = rootRef.value
    if (!root || !('IntersectionObserver' in window)) return

    // Stagger items inside grid groups.
    ;['.features', '.uses'].forEach((g) => {
      root.querySelectorAll(`${g} > *`).forEach((k, i) => {
        k.style.transitionDelay = `${i * 85}ms`
      })
    })

    const sel = '.section-head,.fcard,.ucard,.cit-grid > div,.cta'
    const els = Array.from(root.querySelectorAll(sel))
    io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' },
    )

    const vh = window.innerHeight || 800
    els.forEach((el) => {
      if (el.getBoundingClientRect().top >= vh * 0.92) {
        el.classList.add('reveal')
        io.observe(el)
      }
    })
  })

  onBeforeUnmount(() => {
    if (io) io.disconnect()
  })
}
