<script setup>
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import { gsap } from 'gsap'
import CoverageMap from './CoverageMap.vue'
import TrendCard from './TrendCard.vue'
import HandMark from './HandMark.vue'
import sudan from './data/sudan.json'
import { question, parts, sources } from './haitiAnswer.js'
import { answerLength, revealedParts } from './landingKit.js'
import { citeLabel, revealSource } from '../utils/sources.js'

const MS_PER_CHAR = 14
const PARALLAX = { chat: -5, trend: 8 } // px at the composite's edge

const root = useTemplateRef('root')
const chat = useTemplateRef('chat')
const answer = useTemplateRef('answer')

// Characters typed so far. Starts complete, so reduced motion (and any
// failure before the intro runs) shows the whole answer.
const total = answerLength(parts)
const typed = shallowRef(total)
// Visible parts grouped into paragraphs (a blank line in the text starts a new one).
const paragraphs = computed(() => {
  const out = [[]]
  for (const part of revealedParts(parts, typed.value)) {
    if (part.text === undefined) {
      out[out.length - 1].push(part)
      continue
    }
    part.text.split('\n\n').forEach((text, i) => {
      if (i > 0) out.push([])
      if (text) out[out.length - 1].push({ ...part, text })
    })
  }
  return out
})
const streaming = computed(() => typed.value < total)

const publisher = (src) => src.meta.split(' · ')[0]
const chipLabel = (n) => {
  const src = sources.find((s) => s.n === n)
  return citeLabel(n, { title: src.title, source: publisher(src), date: src.date })
}
const trendCredit = `${sudan.idps.credit} · HDX HAPI`

// Keep the newest line in view while streaming, unless the reader scrolled up.
let follow = true
const scrolled = shallowRef(false)
function onAnswerScroll() {
  const el = answer.value
  follow = el.scrollTop + el.clientHeight >= el.scrollHeight - 8
  scrolled.value = el.scrollTop > 2
}
watch(
  typed,
  () => {
    if (streaming.value && follow) answer.value.scrollTop = answer.value.scrollHeight
  },
  { flush: 'post' },
)

// Chip -> source row, the app's behaviour; 'nearest' keeps the page still.
function onCite(event) {
  const cite = event.target.closest('.cite')
  if (!cite) return
  event.preventDefault()
  revealSource(chat.value, cite.dataset.cite, cite, { block: 'nearest' })
}

// Once typed, the answer settles back at its start (the same rest state reduced
// motion shows), unless the reader scrolled it themselves.
function settle() {
  if (follow) answer.value.scrollTo({ top: 0, behavior: 'smooth' })
}

// The composite's part of the hero timeline; LandingView places it.
function intro() {
  const q = gsap.utils.selector(root.value)
  const stream = { n: 0 }
  const streamAt = 0.55
  const streamFor = (total * MS_PER_CHAR) / 1000
  typed.value = 0
  follow = true
  return gsap
    .timeline({ defaults: { ease: 'expo.out', duration: 1 } })
    .from(q('.hc-map'), { autoAlpha: 0, duration: 1.6, ease: 'power1.out' }, 0)
    .from(q('.hc-chat'), { y: 28, autoAlpha: 0 }, 0)
    .from(q('.hc-trend'), { y: 36, autoAlpha: 0 }, 0.18)
    .to(
      stream,
      {
        n: total,
        duration: streamFor,
        ease: 'none',
        onUpdate: () => {
          typed.value = Math.round(stream.n)
        },
      },
      streamAt,
    )
    .call(settle, null, streamAt + streamFor + 0.9)
    .fromTo(
      q('.tc-svg'),
      { clipPath: 'inset(-4px 100% -4px 0)' },
      { clipPath: 'inset(-4px 0% -4px 0)', duration: 1.8, ease: 'power2.inOut' },
      0.8,
    )
    .from(q('.trend-dot'), { scale: 0, autoAlpha: 0, duration: 0.5, ease: 'back.out(2.4)' }, 2.5)
}

// Snap to the final state (reduced motion switched on mid-intro, or unmount).
function finish() {
  typed.value = total
  if (answer.value) answer.value.scrollTop = 0
}

defineExpose({ intro, finish })

// Pointer parallax on the two cards: fine pointers only, never under reduced motion.
let mm = null
onMounted(() => {
  mm = gsap.matchMedia()
  mm.add(
    '(prefers-reduced-motion: no-preference) and (hover: hover) and (pointer: fine)',
    () => {
      const el = root.value
      const layers = Object.entries(PARALLAX).map(([name, depth]) => {
        const target = el.querySelector(`.hc-${name}-slot`)
        return {
          depth,
          x: gsap.quickTo(target, 'x', { duration: 0.9, ease: 'power3' }),
          y: gsap.quickTo(target, 'y', { duration: 0.9, ease: 'power3' }),
        }
      })
      const move = (nx, ny) => layers.forEach((l) => (l.x(nx * l.depth), l.y(ny * l.depth)))
      const onMove = (e) => {
        const box = el.getBoundingClientRect()
        const nx = gsap.utils.clamp(-1, 1, ((e.clientX - box.left) / box.width) * 2 - 1)
        const ny = gsap.utils.clamp(-1, 1, ((e.clientY - box.top) / box.height) * 2 - 1)
        move(nx, ny)
      }
      const onLeave = () => move(0, 0)
      el.addEventListener('pointermove', onMove)
      el.addEventListener('pointerleave', onLeave)
      return () => {
        el.removeEventListener('pointermove', onMove)
        el.removeEventListener('pointerleave', onLeave)
      }
    },
    root.value,
  )
})

onBeforeUnmount(() => mm?.revert())
</script>

<template>
  <div ref="root" class="hero-composite">
    <div class="hc-map">
      <CoverageMap />
    </div>

    <div class="hc-chat-slot">
      <figure ref="chat" class="hc-chat" aria-label="Sample answer" @click="onCite">
        <p class="hc-q">{{ question }}</p>
        <div
          ref="answer"
          class="hc-answer"
          :class="{ 'is-scrolled': scrolled }"
          role="region"
          aria-label="Answer"
          :aria-busy="streaming"
          tabindex="0"
          @scroll.passive="onAnswerScroll"
        >
          <p v-for="(para, p) in paragraphs" :key="p">
            <template v-for="(part, i) in para" :key="i"
              ><a
                v-if="part.cite"
                class="cite"
                :href="'#hero-src-' + part.cite"
                :data-cite="part.cite"
                :aria-label="chipLabel(part.cite)"
                >{{ part.cite }}</a
              ><strong v-else-if="part.strong">{{ part.text }}</strong
              ><template v-else>{{ part.text }}</template></template
            ><span
              v-if="streaming && p === paragraphs.length - 1"
              class="hc-caret"
              aria-hidden="true"
            ></span>
          </p>
        </div>
        <ol class="hc-sources" aria-label="Sources">
          <li
            v-for="src in sources"
            :id="'hero-src-' + src.n"
            :key="src.n"
            class="source-item"
            :data-srcid="src.n"
          >
            <span class="hc-src-n">{{ src.n }}</span>
            <a
              class="source-link"
              :href="src.url"
              target="_blank"
              rel="noopener noreferrer"
              :title="src.title"
              ><span class="hc-src-pub">{{ publisher(src) }}</span> {{ src.title }}</a
            >
            <time class="hc-src-date" :datetime="src.date">{{ src.date }}</time>
          </li>
        </ol>
        <figcaption class="hc-tag">
          <HandMark :size="20" :radius="6" :stroke="1.8" solid />Sample answer
        </figcaption>
      </figure>
    </div>

    <div class="hc-trend-slot">
      <TrendCard
        class="hc-trend"
        :series="sudan.idps.series"
        title="Internally displaced people · Sudan"
        :credit="trendCredit"
      />
    </div>
  </div>
</template>

<style scoped>
.hero-composite {
  position: relative;
  display: flex;
  flex-direction: column;
  padding-top: 40px;
}

/* The living map sits behind both cards. Scaled and placed so the densest
   report regions (West Africa, the Middle East, South and South-East Asia)
   frame the chat card above and to its right; it fades out before the copy. */
.hc-map {
  position: absolute;
  left: -22%;
  width: 160%;
  top: -15%;
  aspect-ratio: 360 / 140;
  pointer-events: none;
  -webkit-mask-image: radial-gradient(ellipse 64% 62% at 62% 50%, #000 50%, transparent);
  mask-image: radial-gradient(ellipse 64% 62% at 62% 50%, #000 50%, transparent);
}

/* The trend card overlaps only the chat card's caption strip, whose text
   sits on the left, so no answer text or source row is ever covered. */
.hc-chat-slot {
  position: relative;
  height: 480px;
  margin-right: 64px;
}
.hc-trend-slot {
  position: relative;
  align-self: flex-end;
  width: min(340px, 64%);
  margin: -44px -16px 0 0;
}

.hc-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  margin: 0;
  padding: 20px 22px 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow:
    0 1px 2px rgb(11 29 46 / 0.05),
    0 30px 60px -30px rgb(11 29 46 / 0.28);
  overflow: hidden;
}

.hc-q {
  align-self: flex-end;
  max-width: 86%;
  text-wrap: balance;
  padding: 10px 14px;
  border-radius: 14px 14px 4px 14px;
  background: var(--mkt-ink);
  color: var(--mkt-ground);
  font-size: 14px;
  line-height: 1.45;
}

.hc-answer {
  flex: 1;
  min-height: 0;
  margin-top: 16px;
  overflow-y: auto;
  overscroll-behavior: contain;
  font-size: 14.5px;
  line-height: 1.62;
  color: var(--color-text);
  scrollbar-color: auto;
}
.hc-answer p + p {
  margin-top: 10px;
}
.hc-answer.is-scrolled {
  -webkit-mask-image: linear-gradient(transparent, #000 32px);
  mask-image: linear-gradient(transparent, #000 32px);
}
.hc-answer::-webkit-scrollbar {
  width: 6px;
}
.hc-answer::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: var(--color-border-strong);
}

.hc-answer:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 4px;
  border-radius: 4px;
}
.hc-answer strong {
  font-weight: 650;
}
.hc-caret {
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 2px;
  vertical-align: -0.15em;
  background: var(--mkt-brand-chart);
  animation: hc-blink 1s steps(2) infinite;
}
@keyframes hc-blink {
  50% {
    opacity: 0;
  }
}

/* Citation chips mirror the app: quiet outlines that fill on hover/focus. */
.cite {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  margin: 0 1px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  vertical-align: 1px;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.cite:hover,
.cite:focus-visible {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
  outline: none;
}

.hc-sources {
  margin: 14px 0 0;
  padding: 10px 0 0;
  list-style: none;
  border-top: 1px solid var(--color-border);
}
.source-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 3px 6px;
  margin: 0 -6px;
  border-radius: 8px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  transition: background-color 0.25s;
}
.source-item.active {
  background: var(--color-accent-soft);
  color: var(--color-text);
}
.hc-src-n {
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.source-item.active .hc-src-n {
  color: var(--color-accent);
}
.source-link {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  border-radius: 4px;
}
.source-link:hover {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.hc-src-pub {
  font-weight: 600;
  color: var(--color-text);
}
.hc-src-date {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.hc-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  font-size: 12px;
  color: var(--color-muted);
}

@media (prefers-reduced-motion: reduce) {
  .hc-caret {
    display: none;
  }
}

/* Below the two-column hero the cards stack in flow, the trend card
   overlapping the chat card's foot. */
@media (max-width: 1023px) {
  .hc-map {
    left: -30%;
    top: -100px;
  }
  .hc-chat-slot {
    height: auto;
    margin-right: 0;
  }
  .hc-answer {
    flex: none;
    height: 300px;
  }
  .hc-trend-slot {
    width: min(340px, 92%);
    margin: -14px 0 0;
  }
}
</style>
