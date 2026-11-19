<script setup>
import { computed, onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { gsap } from 'gsap'
import coverage from './data/coverage.json'
import CoverageMap from './CoverageMap.vue'
import {
  countUp,
  dayLabel,
  formatNumber,
  mapCountries,
  mapLabels,
  onVisible,
  prefersReducedMotion,
  project,
} from './landingKit.js'

const { t, te, locale } = useI18n()

const grouped = (n) => formatNumber(n, locale.value)
const STATS = [
  { key: 'countries', value: coverage.countries },
  { key: 'reports', value: coverage.reports },
  { key: 'publishers', value: coverage.publishers },
]

// The highest-volume countries named on the map, placed in percent of its box. Short
// names per language live in landing.coverage.mapNames; others keep the data's name.
const points = mapLabels(mapCountries(coverage.points), { count: 4 }).map((p) => {
  const { x, y } = project(p.lat, p.lon, 100, 100)
  return { ...p, style: { left: `${x}%`, top: `${y}%` } }
})
const labels = computed(() =>
  points.map((p) => {
    const key = `landing.coverage.mapNames.${p.iso3}`
    return {
      iso3: p.iso3,
      name: te(key) ? t(key) : p.name.replace(/\s*\(.*\)$/, ''),
      reports: grouped(p.reports),
      style: p.style,
    }
  }),
)

const root = useTemplateRef('root')
let ctx = null
const stops = []

// Each figure counts up the first time its section is on screen. The markup
// already holds the final numbers, so reduced motion and no-JS read correctly.
onMounted(() => {
  if (prefersReducedMotion()) return
  ctx = gsap.context(() => {
    root.value.querySelectorAll('[data-count]').forEach((el) => {
      const to = Number(el.dataset.count)
      stops.push(
        onVisible(el, () =>
          // ctx.add records the late tween, so revert() kills it on unmount. The
          // start text is set here, so a render that never scrolls keeps the finals.
          ctx.add(() => {
            el.textContent = '0'
            // The grouping is read on every frame, so a language switch mid-count
            // continues in the new language.
            countUp(el, to, { duration: 1.6, format: (v) => grouped(Math.round(v)) })
          }),
        ),
      )
    })
  }, root.value)
})

onBeforeUnmount(() => {
  stops.forEach((stop) => stop())
  ctx?.revert()
})
</script>

<template>
  <section id="coverage" ref="root" class="section coverage">
    <div class="wrap">
      <div class="section-head">
        <h2>{{ t('landing.coverage.title') }}</h2>
        <p>{{ t('landing.coverage.lede') }}</p>
      </div>
      <div class="cov">
        <dl class="stats">
          <div v-for="s in STATS" :key="s.key" class="stat">
            <dt class="stat-v" :data-count="s.value">{{ grouped(s.value) }}</dt>
            <dd>{{ t(`landing.coverage.${s.key}`) }}</dd>
          </div>
        </dl>
        <figure class="cov-map">
          <div class="cov-canvas">
            <CoverageMap figure />
            <span v-for="l in labels" :key="l.iso3" class="cov-label" :style="l.style"
              >{{ l.name }} <b>{{ l.reports }}</b></span
            >
          </div>
          <figcaption>{{ t('landing.coverage.caption') }}</figcaption>
        </figure>
      </div>
      <p class="stats-src">
        {{ t('landing.coverage.asOf', { date: dayLabel(coverage.generated, locale) }) }}
      </p>
    </div>
  </section>
</template>

<style scoped>
/* The figures annotate the map: a narrow column beside it, the map at full size. */
.cov {
  display: grid;
  grid-template-columns: minmax(200px, 260px) minmax(0, 1fr);
  gap: 48px;
  align-items: center;
}
.stats {
  margin: 0;
}
.stat {
  padding: 18px 0 20px;
  border-top: 1px solid var(--color-border);
}
.stat-v {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: clamp(34px, 4vw, 48px);
  font-weight: 600;
  letter-spacing: -0.04em;
  line-height: 1.05;
}
.stat dd {
  margin: 6px 0 0;
  font-size: 15px;
  color: var(--color-text-secondary);
}
.cov-map {
  margin: 0;
}
.cov-canvas {
  position: relative;
  aspect-ratio: 360 / 140;
}
.cov-label {
  position: absolute;
  transform: translate(10px, -50%);
  padding: 1px 6px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--mkt-ground) 82%, transparent);
  font-size: 12px;
  font-weight: 550;
  line-height: 1.5;
  white-space: nowrap;
  color: var(--color-text);
  pointer-events: none;
}
.cov-label b {
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.cov-map figcaption {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-muted);
}
.stats-src {
  margin-top: 28px;
  font-size: 12px;
  color: var(--color-muted);
}
@media (max-width: 900px) {
  .cov {
    grid-template-columns: minmax(0, 1fr);
    gap: 28px;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0 20px;
  }
}
@media (max-width: 560px) {
  .stats {
    grid-template-columns: minmax(0, 1fr);
  }
  /* Too small to name countries without labels colliding. */
  .cov-label {
    display: none;
  }
}
</style>
