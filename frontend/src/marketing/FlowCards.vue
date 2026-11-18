<script setup>
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import sudan from './data/sudan.json'
import { parts, sources } from './haitiAnswer.js'
import { dayLabel, formatCompact, passage, passageSources } from './landingKit.js'

gsap.registerPlugin(ScrollTrigger)

const top = sudan.regions[0][1]
const regions = sudan.regions.map(([name, value]) => ({
  name,
  value: formatCompact(value),
  width: `${(value / top) * 100}%`,
}))
const dtmCredit = `${sudan.idps.credit} · HDX HAPI`

// A passage of the hero's Haiti answer, quoted with its own citations.
const sample = passage(parts, 'Nearly 80 percent', 'Grand Sud (39%)')
const cited = passageSources(sample, sources)
const sampleCredit = `From the Haiti answer above · ${cited.publishers.join(', ')} · `
const sampleDate = dayLabel(cited.newest)

const root = useTemplateRef('root')

// Each card rises in as it reaches the viewport; side by side they arrive staggered.
// Reduced motion never runs this, so the cards stay in place.
let mm = null
onMounted(() => {
  mm = gsap.matchMedia()
  mm.add(
    '(prefers-reduced-motion: no-preference)',
    () => {
      gsap.utils.toArray('.flow', root.value).forEach((card, i) => {
        gsap.from(card, {
          y: 28,
          autoAlpha: 0,
          duration: 0.9,
          ease: 'expo.out',
          delay: i * 0.09,
          scrollTrigger: { trigger: card, start: 'top 88%', once: true },
        })
      })
    },
    root.value,
  )
})

onBeforeUnmount(() => mm?.revert())
</script>

<template>
  <section id="workflows" ref="root" class="section">
    <div class="wrap">
      <div class="section-head">
        <h2>From a quick question to the brief you hand in.</h2>
        <p>
          Chat for the latest state of a crisis, reports that synthesise many sources at once, and
          technical monitoring with the statistics done in code.
        </p>
      </div>

      <div class="flows">
        <article class="flow">
          <h3>Cited chat</h3>
          <p>Answers only from retrieved reports, each claim one click from its source.</p>
          <div class="flow-ui">
            <p class="fu-answer">
              <template v-for="(part, i) in sample" :key="i"
                ><span v-if="part.cite" class="cite" aria-hidden="true">{{ part.cite }}</span
                ><template v-else>{{ part.text }}</template></template
              >.
            </p>
            <p class="fu-credit">
              {{ sampleCredit
              }}<time class="fu-date" :datetime="cited.newest">{{ sampleDate }}</time>
            </p>
          </div>
        </article>

        <article class="flow">
          <h3>M&amp;E reports</h3>
          <p>Pick a country, sector, period and language; get a structured, cited brief.</p>
          <div class="flow-ui" aria-hidden="true">
            <p class="fu-head">Yemen · Situation Report · Health</p>
            <span class="fu-line" style="width: 96%"></span>
            <span class="fu-line" style="width: 88%"></span>
            <p class="fu-head">Key findings</p>
            <span class="fu-line" style="width: 92%"></span>
            <span class="fu-line" style="width: 64%"></span>
          </div>
        </article>

        <article class="flow">
          <h3>Technical monitoring</h3>
          <p>Indicator trends and regional comparisons, tested in code, narrated by the model.</p>
          <div class="flow-ui">
            <ul class="fu-bars" aria-label="Internally displaced people in Sudan, top 5 states">
              <li v-for="r in regions" :key="r.name">
                <span class="fu-name">{{ r.name }}</span>
                <span class="fu-track"><i :style="{ width: r.width }"></i></span>
                <b>{{ r.value }}</b>
              </li>
            </ul>
            <p class="fu-credit">{{ dtmCredit }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.flows {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}
.flow {
  display: flex;
  flex-direction: column;
  padding: 22px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
}
.flow h3 {
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.01em;
}
.flow > p {
  margin-top: 8px;
  font-size: 14.5px;
  line-height: 1.55;
  color: var(--color-text-secondary);
  text-wrap: pretty;
}
.flow-ui {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 170px;
  margin-top: 18px;
  padding: 14px;
  font-size: 12.5px;
  background: var(--color-surface-container-low);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.fu-answer {
  line-height: 1.65;
  color: var(--color-text);
}
.fu-answer .cite {
  cursor: default;
}
.fu-line {
  display: block;
  height: 8px;
  margin-top: 10px;
  border-radius: 4px;
  background: var(--color-surface-container-high);
}
.fu-head {
  margin-top: 12px;
  font-weight: 650;
  color: var(--color-text);
}
.fu-head:first-child {
  margin-top: 0;
}
.fu-bars {
  margin: 0;
  padding: 0;
  list-style: none;
}
.fu-bars li {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) 44px;
  gap: 8px;
  align-items: center;
  margin: 2px 0 8px;
  color: var(--color-text-secondary);
}
.fu-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fu-track i {
  display: block;
  height: 10px;
  border-radius: 0 4px 4px 0;
  background: var(--mkt-brand-chart);
}
.fu-bars b {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--color-text);
}
.fu-date {
  white-space: nowrap;
}
.fu-credit {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-muted);
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .flows {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
