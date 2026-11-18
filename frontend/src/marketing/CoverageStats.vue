<script setup>
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { gsap } from 'gsap'
import coverage from './data/coverage.json'
import { countUp, dayLabel, onVisible, prefersReducedMotion } from './landingKit.js'

const grouped = (n) => n.toLocaleString('en-US')
const stats = [
  { key: 'countries', value: coverage.countries, label: 'countries and territories with reports' },
  { key: 'reports', value: coverage.reports, label: 'reports indexed, newest added daily' },
  { key: 'publishers', value: coverage.publishers, label: 'publishing organisations' },
]
const asOf = dayLabel(coverage.generated)

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
      <dl class="stats">
        <div v-for="s in stats" :key="s.key" class="stat">
          <dt class="stat-v" :data-count="s.value">{{ grouped(s.value) }}</dt>
          <dd>{{ s.label }}</dd>
        </div>
      </dl>
      <p class="stats-src">ReliefWeb · as of {{ asOf }}</p>
    </div>
  </section>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0;
  border-top: 1px solid var(--color-border);
}
.stat {
  padding: 28px 24px 0 0;
}
.stat-v {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: clamp(36px, 5vw, 56px);
  font-weight: 600;
  letter-spacing: -0.04em;
  line-height: 1.05;
}
.stat dd {
  margin: 6px 0 0;
  font-size: 15px;
  color: var(--color-text-secondary);
}
.stats-src {
  margin-top: 28px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-muted);
}
@media (max-width: 700px) {
  .stats {
    grid-template-columns: minmax(0, 1fr);
  }
  .stat {
    padding: 22px 0;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
