<script setup>
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import sudan from './data/sudan.json'
import meReport from './data/meReport.json'
import { parts, sources } from './haitiAnswer.js'
import { citedParts, dayLabel, formatCompact, monthLabel, passage, passageSources } from './landingKit.js'
import { citeLabel, revealSource } from '../utils/sources.js'

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

// One sample report generated for this page (scripts/generate_landing_report.py);
// its Key Findings sentences are quoted verbatim, chips open their source rows.
const reportHead = `${meReport.country} · ${meReport.type} · ${meReport.sector}`
const reportPeriod = `${monthLabel(meReport.date_from)} – ${monthLabel(meReport.date_to)}`
const reportGenerated = dayLabel(meReport.generated)
const findings = meReport.findings.map(citedParts)
const reportSources = meReport.sources
const reportChip = (n) => {
  const src = reportSources.find((s) => s.n === n)
  return citeLabel(n, { title: src.title, source: src.publisher, date: src.date })
}

const root = useTemplateRef('root')
const report = useTemplateRef('report')

function onReportCite(event) {
  const cite = event.target.closest('.cite')
  if (cite) revealSource(report.value, cite.dataset.cite, cite, { block: 'nearest' })
}

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
          <figure ref="report" class="flow-ui fu-report" aria-label="Sample report" @click="onReportCite">
            <p class="fu-head">{{ reportHead }}</p>
            <p class="fu-meta">{{ reportPeriod }}</p>
            <p class="fu-label">Key findings</p>
            <p v-for="(finding, f) in findings" :key="f" class="fu-finding">
              <template v-for="(part, i) in finding" :key="i"
                ><button
                  v-if="part.cite"
                  class="cite"
                  type="button"
                  :data-cite="part.cite"
                  :aria-label="reportChip(part.cite)"
                >
                  {{ part.cite }}</button
                ><template v-else>{{ part.text }}</template></template
              >
            </p>
            <ol class="fu-sources" aria-label="Sources">
              <li
                v-for="src in reportSources"
                :key="src.n"
                class="source-item"
                :data-srcid="src.n"
              >
                <span class="fu-src-n">{{ src.n }}</span>
                <span class="fu-src-body">
                  <a
                    class="source-link"
                    :href="src.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    :title="src.title"
                    >{{ src.title }}</a
                  >
                  <span class="fu-src-meta"
                    >{{ src.publisher }} ·
                    <time class="fu-date" :datetime="src.date">{{ src.date }}</time></span
                  >
                </span>
              </li>
            </ol>
            <figcaption class="fu-credit">
              Sample report · generated
              <time :datetime="meReport.generated">{{ reportGenerated }}</time>
            </figcaption>
          </figure>
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
.fu-report {
  margin-bottom: 0;
  margin-inline: 0;
}
.fu-meta {
  font-size: 12px;
  color: var(--color-muted);
}
.fu-label {
  margin-top: 12px;
  font-weight: 650;
  color: var(--color-text);
}
.fu-finding {
  margin-top: 6px;
  line-height: 1.6;
  color: var(--color-text);
  text-wrap: pretty;
}
.fu-report .cite {
  line-height: 1;
  vertical-align: 1px;
}
.fu-sources {
  margin: 12px 0 0;
  padding: 8px 0 0;
  list-style: none;
  border-top: 1px solid var(--color-border);
}
.fu-sources .source-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 6px;
  padding: 4px 6px;
  margin: 0 -6px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  transition: background-color 0.25s;
}
.fu-sources .source-item.active {
  background: var(--color-accent-soft);
  color: var(--color-text);
}
.fu-src-n {
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.source-item.active .fu-src-n {
  color: var(--color-accent);
}
.fu-src-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.fu-sources .source-link {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-weight: 550;
  color: var(--color-text);
  border-radius: 4px;
}
.fu-sources .source-link:hover {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.fu-src-meta {
  font-size: 12px;
  color: var(--color-muted);
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
