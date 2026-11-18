<script setup>
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { gsap } from 'gsap'
import coverage from './data/coverage.json'
import CoverageMap from './CoverageMap.vue'
import { countUp, dayLabel, mapLabels, onVisible, prefersReducedMotion, project } from './landingKit.js'

const grouped = (n) => n.toLocaleString('en-US')
const stats = [
  { key: 'countries', value: coverage.countries, label: 'countries and territories with reports' },
  { key: 'reports', value: coverage.reports, label: 'reports indexed, newest added daily' },
  { key: 'publishers', value: coverage.publishers, label: 'publishing organisations' },
]
const asOf = dayLabel(coverage.generated)

// The highest-volume countries named on the map, placed in percent of its box.
const SHORT = { PSE: 'oPt', COD: 'DR Congo' }
const labels = mapLabels(coverage.points, { count: 5 }).map((p) => {
  const { x, y } = project(p.lat, p.lon, 100, 100)
  return {
    iso3: p.iso3,
    name: SHORT[p.iso3] ?? p.name.replace(/\s*\(.*\)$/, ''),
    reports: grouped(p.reports),
    style: { left: `${x}%`, top: `${y}%` },
  }
})

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
      el.textContent = '0'
      stops.push(onVisible(el, () => countUp(el, to, { duration: 1.6, format: (v) => grouped(Math.round(v)) })))
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
        <h2>Built on the last year of ReliefWeb.</h2>
        <p>
          Every answer and report draws on the same index, so you can see how much record stands
          behind it.
        </p>
      </div>
      <div class="cov">
        <dl class="stats">
          <div v-for="s in stats" :key="s.key" class="stat">
            <dt class="stat-v" :data-count="s.value">{{ grouped(s.value) }}</dt>
            <dd>{{ s.label }}</dd>
          </div>
        </dl>
        <figure class="cov-map">
          <div class="cov-canvas">
            <CoverageMap figure />
            <span v-for="l in labels" :key="l.iso3" class="cov-label" :style="l.style"
              >{{ l.name }} <b>{{ l.reports }}</b></span
            >
          </div>
          <figcaption>
            Each dot is a country, sized by its indexed reports.
          </figcaption>
        </figure>
      </div>
      <p class="stats-src">ReliefWeb · as of {{ asOf }}</p>
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
  font-family: var(--font-mono);
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
