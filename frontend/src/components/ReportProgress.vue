<template>
  <!-- The wait for a report, said with what is known: what was asked for, what the
       pipeline is doing, how long it has been, and the sections the report type
       always has. The server sends nothing before the first word, so nothing here
       pretends to measure progress. -->
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { reportTypeLabel, sectorLabel } from '../utils/reportTypes.js'
import { formatPeriod } from '../utils/reportTitle.js'
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
})

const { t, te } = useI18n()

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
  }),
)
// The document reports keep the viewer's long-standing note for the first wait.
const stageText = computed(() =>
  stage.value === 'reading' ? t('reports.viewer.reading') : t(`reports.progress.${stage.value}`),
)

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
  .scan-line {
    animation: none;
  }
}
</style>
