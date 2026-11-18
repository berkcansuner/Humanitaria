<template>
  <!-- The wait for a report, said with what is known: what was asked for, what the
       pipeline is doing, how long it has been, what the server says it is reading
       (or, for technical monitoring, which indicators it computed), and the sections
       the report type always has. Nothing here pretends to measure progress. -->
  <div class="report-progress">
    <p class="progress-request">{{ requestLine }}</p>
    <p class="progress-status">
      <!-- The one live region: it names the stage (announced when it changes), never
           the time. Filled just after it is in the page, so it is announced. -->
      <span class="progress-stage" role="status">{{ ready ? stageText : '' }}</span>
      <span class="progress-elapsed">{{
        t('reports.progress.elapsed', { time: elapsedClock(elapsed) })
      }}</span>
    </p>
    <!-- The report's reading list as the server sent it: titles and publishers as
         they are (never translated). Five rows at a time keep the outline and its
         motion in view; the rows turn over slowly through the whole list (a reading
         list, not a claim about which one is being read now). Under reduced motion
         the first five stay put. -->
    <section v-if="!started && reading" class="progress-read" aria-labelledby="read-caption">
      <p id="read-caption" class="read-caption">{{ t('reports.progress.readCaption') }}</p>
      <ul :key="readStart" class="read-list">
        <li v-for="(src, i) in visibleSources" :key="i" class="read-row" :style="{ '--i': i }">
          <span class="read-title" :title="src.title">{{ src.title }}</span>
          <span class="read-meta">{{ sourceMeta(src) }}</span>
        </li>
      </ul>
      <p v-if="moreCount > 0" class="read-more">
        {{ t('reports.progress.readMore', { n: moreCount }, moreCount) }}
      </p>
    </section>
    <section v-else-if="!started && stats" class="progress-read" aria-labelledby="read-caption">
      <p id="read-caption" class="read-caption">{{ t('reports.progress.computedCaption') }}</p>
      <!-- Indicator names come in the report's language, from the computed findings. -->
      <ul class="read-list" :lang="language || undefined">
        <li
          v-for="(name, i) in stats.indicators || []"
          :key="name"
          class="read-row"
          :style="{ '--i': i }"
        >
          <span class="read-title">{{ name }}</span>
        </li>
      </ul>
      <p v-if="computedPeriod" class="read-period">
        {{ t('reports.progress.periodAnalysed', { period: computedPeriod }) }}
      </p>
    </section>
    <div v-if="!started" class="progress-outline">
      <p class="outline-caption">{{ t('reports.progress.outline') }}</p>
      <ol class="outline-list">
        <li v-for="(key, i) in outline" :key="key" class="outline-item">
          <span class="outline-name">{{ t(`reports.outline.${key}`) }}</span>
          <span class="outline-lines" aria-hidden="true">
            <span
              v-for="n in LINES"
              :key="n"
              class="scan-line"
              :style="{ '--n': i * LINES + n, '--w': `${widthOf(i, n)}%` }"
            ></span>
          </span>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { reportTypeLabel, sectorLabel } from '../utils/reportTypes.js'
import { formatPeriod } from '../utils/reportTitle.js'
import { ledgerDate } from '../utils/sources.js'
import { reportOutline, progressStage, elapsedClock } from '../utils/reportProgress.js'

const props = defineProps({
  type: { type: String, default: 'situation' },
  country: { type: String, default: '' },
  theme: { type: String, default: '' },
  dateFrom: { type: String, default: '' },
  dateTo: { type: String, default: '' },
  language: { type: String, default: '' },
  // The period of the report this one continues ("Run next period"), already formatted.
  comparedPeriod: { type: String, default: '' },
  started: { type: Boolean, default: false }, // the first words have arrived
  checking: { type: Boolean, default: false }, // "What changed" is being checked
  // The server's status before the first word: { count, sources: [{ title, source,
  // date }] } for document reports, { indicators, date_from, date_to } for technical.
  reading: { type: Object, default: null },
  stats: { type: Object, default: null },
})

const { t, te, locale } = useI18n()

const readSources = computed(() => (props.reading && props.reading.sources) || [])
// Five rows at a time, turning over every few seconds and wrapping round, so every
// listed source is shown; "and N more" counts every document read besides the rows
// in view, so it stays the same as they turn.
const READ_SHOWN = 5
const TURN_MS = 6000
const readStart = ref(0)
const visibleSources = computed(() => {
  const list = readSources.value
  if (list.length <= READ_SHOWN) return list
  return Array.from({ length: READ_SHOWN }, (_, k) => list[(readStart.value + k) % list.length])
})
const moreCount = computed(() =>
  props.reading ? Math.max(0, (props.reading.count || 0) - visibleSources.value.length) : 0,
)
const reducedMotion = () =>
  typeof window.matchMedia !== 'function' ||
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
let turn = null
watch(
  () => props.reading,
  () => {
    clearInterval(turn)
    readStart.value = 0
    if (readSources.value.length <= READ_SHOWN || reducedMotion()) return
    turn = setInterval(() => {
      readStart.value = (readStart.value + READ_SHOWN) % readSources.value.length
    }, TURN_MS)
  },
  { immediate: true },
)
// "OCHA · 2026-10-11" ("OCHA · 11 Eki 2026"): the publisher as it is, the date in
// the interface's format.
const sourceMeta = (src) =>
  [src.source, ledgerDate(src.date, locale.value)].filter(Boolean).join(' · ')
const computedPeriod = computed(() => {
  const c = props.stats
  return c && (c.date_from || c.date_to)
    ? formatPeriod(`${c.date_from || ''} – ${c.date_to || ''}`)
    : ''
})

// Counted from when the waiting state appears, which is when the request is sent.
const startedAt = Date.now()
const elapsed = ref(0)
const ready = ref(false)
let tick = null
let readyTimer = null
onMounted(() => {
  tick = setInterval(() => {
    elapsed.value = Math.floor((Date.now() - startedAt) / 1000)
  }, 1000)
  readyTimer = setTimeout(() => (ready.value = true))
})
onBeforeUnmount(() => {
  clearInterval(tick)
  clearInterval(turn)
  clearTimeout(readyTimer)
})

// "Situation Report · Sudan · Health · 18.08.2026 - 18.11.2026 · English": each
// "·" is glued to the part before it, so no line of a wrapped request starts with one.
const requestLine = computed(() => {
  const period =
    props.dateFrom || props.dateTo ? formatPeriod(`${props.dateFrom} – ${props.dateTo}`) : ''
  const language = te(`lang.names.${props.language}`)
    ? t(`lang.names.${props.language}`)
    : props.language
  return [
    reportTypeLabel(props.type, t),
    props.country,
    sectorLabel(props.theme, t),
    period,
    language,
    props.comparedPeriod ? t('reports.progress.compared', { period: props.comparedPeriod }) : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const stage = computed(() =>
  progressStage({
    type: props.type,
    started: props.started,
    checking: props.checking,
    elapsed: elapsed.value,
    reading: props.reading,
    computed: props.stats,
  }),
)
// The document reports keep the viewer's long-standing note for the first wait; the
// counted stages name what the server said it read or computed.
const stageText = computed(() => {
  if (stage.value === 'reading') return t('reports.viewer.reading')
  if (stage.value === 'readingCount') {
    const n = props.reading.count || 0
    return t('reports.progress.readingCount', { n }, n)
  }
  if (stage.value === 'computed') {
    const n = (props.stats.indicators || []).length
    return t('reports.progress.computed', { n }, n)
  }
  return t(`reports.progress.${stage.value}`)
})

const outline = computed(() => reportOutline(props.type, { comparing: !!props.comparedPeriod }))

// A few lines of text-to-come under each section name, of varied (fixed) lengths.
const LINES = 3
const WIDTHS = [100, 94, 97, 88, 100, 72, 91, 99, 64]
const widthOf = (section, line) =>
  line === LINES ? WIDTHS[(section * 3) % WIDTHS.length] * 0.6 : WIDTHS[(section + line) % 9]
</script>

<style scoped>
.report-progress {
  margin: 0 0 var(--space-4);
}
/* The request, in the meta line's quiet type: it holds the place the report's title
   takes once it is saved. */
.progress-request {
  margin: 0;
  font-family: var(--font-body);
  font-size: 12px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.progress-status {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px var(--space-3);
  margin: var(--space-2) 0 0;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
  line-height: 1.45;
}
.progress-stage {
  flex: 1 1 22rem;
  min-width: 0;
  color: var(--color-text);
}
.progress-elapsed {
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

/* What is being read: hairline-ruled rows like the Sources list the report ends with,
   the title on one line (cut with an ellipsis, whole in its tooltip), publisher and
   date under it. */
.progress-read {
  margin-top: var(--space-5);
}
.read-caption {
  margin: 0 0 var(--space-2);
  font-size: 12px;
  color: var(--color-text-secondary);
}
.read-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--color-border);
}
.read-row {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  padding: 7px 0;
  border-bottom: 1px solid var(--color-border);
  animation: read-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--i) * 0.09s);
}
.read-title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: var(--text-sm);
  color: var(--color-text);
}
.read-meta {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.read-more,
.read-period {
  margin: var(--space-2) 0 0;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
@keyframes read-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

.progress-outline {
  margin-top: var(--space-5);
}
.outline-caption {
  margin: 0 0 var(--space-3);
  font-size: 12px;
  color: var(--color-text-secondary);
}
.outline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
/* Section names in the report's heading face, but quiet: they are what is to come. */
.outline-name {
  display: block;
  margin-bottom: var(--space-2);
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-text-secondary);
}
.outline-lines {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
/* A light band passes along each line, one line after another down the outline:
   reading, not loading. Under reduced motion the lines stand still. */
.scan-line {
  display: block;
  width: var(--w);
  height: 10px;
  border-radius: var(--radius-sm);
  background:
    linear-gradient(
        90deg,
        transparent 0%,
        color-mix(in oklch, var(--color-accent-soft) 85%, transparent) 50%,
        transparent 100%
      )
      no-repeat,
    var(--color-surface-container);
  background-size:
    40% 100%,
    100% 100%;
  background-position:
    -60% 0,
    0 0;
  animation: scan 2.4s cubic-bezier(0.45, 0, 0.55, 1) infinite;
  animation-delay: calc(var(--n) * 0.18s);
}
@keyframes scan {
  0% {
    background-position:
      -60% 0,
      0 0;
  }
  60%,
  100% {
    background-position:
      160% 0,
      0 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .scan-line,
  .read-row {
    animation: none;
  }
}
</style>
