<script setup>
import { computed, onBeforeUnmount, onMounted, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { sampleAnswer, sampleIndicators, samplePassage, sampleReport } from './samples.js'
import { asOfLabel, citedParts, monthLabel, passageSources } from './landingKit.js'
import { ledgerDate, revealSource } from '../utils/sources.js'

gsap.registerPlugin(ScrollTrigger)

const { t, te, locale } = useI18n()

// Sector names as the UI shows them; the report stores the ReliefWeb theme name.
const SECTOR_KEYS = { 'Protection and Human Rights': 'protection' }

const chipLabel = (sources, n) => {
  const src = sources.find((s) => s.n === n)
  return t('landing.chip', {
    n,
    title: src.title,
    publisher: src.publisher,
    date: ledgerDate(src.date, locale.value),
  })
}

// A passage of the hero's Syria answer, quoted verbatim with its own citations.
const sample = computed(() => samplePassage(locale.value))
const sampleSources = computed(() =>
  passageSources(sample.value, sampleAnswer(locale.value).sources).map((s) => ({
    ...s,
    publisher: s.meta.split(' · ')[0],
  })),
)

// One sample report generated for this page (scripts/generate_landing_report.py) in
// the interface language; its Key Findings sentences are quoted verbatim, chips open
// their source rows.
const report = computed(() => {
  const r = sampleReport(locale.value)
  const l = locale.value
  const typeKey = `landing.reportTypes.${r.report_type}`
  const sectorKey = SECTOR_KEYS[r.sector] && `landing.sectors.${SECTOR_KEYS[r.sector]}`
  return {
    head: [
      t('landing.country'),
      te(typeKey) ? t(typeKey) : r.type,
      sectorKey ? t(sectorKey) : r.sector,
    ].join(' · '),
    period: `${monthLabel(r.date_from, l)} – ${monthLabel(r.date_to, l)}`,
    findings: r.findings.map(citedParts),
    sources: r.sources,
  }
})

// Four other rows of the hero's indicator report (scripts/generate_landing_report.py
// --type indicator_monitoring), verbatim, with their dates and cited sources.
const indicators = computed(() => {
  const r = sampleIndicators(locale.value, 'flow')
  const l = locale.value
  return {
    head: [t('landing.country'), t('landing.reportTypes.indicator_monitoring')].join(' · '),
    period: `${monthLabel(r.date_from, l)} – ${monthLabel(r.date_to, l)}`,
    columns: r.columns,
    rows: r.rows.map((row) => ({
      ...row,
      parts: citedParts(row.value),
      asOf: asOfLabel(row.asOf),
    })),
    sources: r.sources,
  }
})

const root = useTemplateRef('root')

// Chip -> its source row inside the same panel, as in the hero.
function onCite(event) {
  const cite = event.target.closest('.cite')
  if (cite) revealSource(event.currentTarget, cite.dataset.cite, cite, { block: 'nearest' })
}

// Each card rises in as it reaches the viewport; side by side they arrive staggered.
// Opacity, not autoAlpha: a hidden card would drop its chips and links from the tab
// order, and tabbing to them scrolls the card in, which plays its entrance.
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
          opacity: 0,
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
        <h2>{{ t('landing.flows.title') }}</h2>
        <p>{{ t('landing.flows.lede') }}</p>
      </div>

      <div class="flows">
        <article class="flow">
          <h3>{{ t('landing.flows.chat.title') }}</h3>
          <p>{{ t('landing.flows.chat.lede') }}</p>
          <figure
            class="flow-ui fu-panel"
            :aria-label="t('landing.flows.chat.panel')"
            @click="onCite"
          >
            <p class="fu-answer">
              <template v-for="(part, i) in sample" :key="i"
                ><button
                  v-if="part.cite"
                  class="cite"
                  type="button"
                  :data-cite="part.cite"
                  :aria-label="chipLabel(sampleSources, part.cite)"
                >
                  {{ part.cite }}</button
                ><template v-else>{{ part.text }}</template></template
              >.
            </p>
            <ol class="fu-sources" :aria-label="t('landing.answer.sources')">
              <li v-for="src in sampleSources" :key="src.n" class="source-item" :data-srcid="src.n">
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
                    <time class="fu-date" :datetime="src.date">{{
                      ledgerDate(src.date, locale)
                    }}</time></span
                  >
                </span>
              </li>
            </ol>
          </figure>
        </article>

        <article class="flow">
          <h3>{{ t('landing.flows.report.title') }}</h3>
          <p>{{ t('landing.flows.report.lede') }}</p>
          <figure
            class="flow-ui fu-panel"
            :aria-label="t('landing.flows.report.panel')"
            @click="onCite"
          >
            <p class="fu-head">{{ report.head }}</p>
            <p class="fu-meta">{{ report.period }}</p>
            <p class="fu-label">{{ t('landing.flows.report.findings') }}</p>
            <p v-for="(finding, f) in report.findings" :key="f" class="fu-finding">
              <template v-for="(part, i) in finding" :key="i"
                ><button
                  v-if="part.cite"
                  class="cite"
                  type="button"
                  :data-cite="part.cite"
                  :aria-label="chipLabel(report.sources, part.cite)"
                >
                  {{ part.cite }}</button
                ><template v-else>{{ part.text }}</template></template
              >
            </p>
            <ol class="fu-sources" :aria-label="t('landing.answer.sources')">
              <li
                v-for="src in report.sources"
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
                    <time class="fu-date" :datetime="src.date">{{
                      ledgerDate(src.date, locale)
                    }}</time></span
                  >
                </span>
              </li>
            </ol>
          </figure>
        </article>

        <article class="flow">
          <h3>{{ t('landing.flows.indicators.title') }}</h3>
          <p>{{ t('landing.flows.indicators.lede') }}</p>
          <figure
            class="flow-ui fu-panel"
            :aria-label="t('landing.flows.indicators.panel')"
            @click="onCite"
          >
            <p class="fu-head">{{ indicators.head }}</p>
            <p class="fu-meta">{{ indicators.period }}</p>
            <dl class="fu-ind">
              <div v-for="row in indicators.rows" :key="row.indicator" class="fu-ind-row">
                <dt>{{ row.indicator }}</dt>
                <dd class="fu-ind-value">
                  <span
                    ><template v-for="(part, i) in row.parts" :key="i"
                      ><button
                        v-if="part.cite"
                        class="cite"
                        type="button"
                        :data-cite="part.cite"
                        :aria-label="chipLabel(indicators.sources, part.cite)"
                      >
                        {{ part.cite }}</button
                      ><template v-else>{{ part.text }}</template></template
                    ></span
                  >
                  <span class="fu-asof"
                    ><span class="sr-only">{{ indicators.columns[2] }}: </span>{{ row.asOf }}</span
                  >
                </dd>
              </div>
            </dl>
            <ol class="fu-sources" :aria-label="t('landing.answer.sources')">
              <li
                v-for="src in indicators.sources"
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
                    <time class="fu-date" :datetime="src.date">{{
                      ledgerDate(src.date, locale)
                    }}</time></span
                  >
                </span>
              </li>
            </ol>
          </figure>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.flows {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 32px;
}
/* Heading and lede sit on the ground; the product panel is the only card. */
.flow {
  display: flex;
  flex-direction: column;
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
  padding: 18px;
  font-size: 12.5px;
  background: var(--color-surface-container-low);
  border: 1px solid var(--color-border);
  border-radius: 16px;
}
.fu-answer {
  line-height: 1.65;
  color: var(--color-text);
}
.fu-panel {
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
.fu-panel .cite {
  line-height: 1;
  vertical-align: 1px;
}
.fu-ind {
  margin: 10px 0 0;
}
.fu-ind-row {
  padding: 8px 0;
  border-top: 1px solid var(--color-border);
}
.fu-ind dt {
  line-height: 1.45;
  color: var(--color-text-secondary);
  text-wrap: pretty;
}
.fu-ind-value {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 2px 12px;
  margin: 2px 0 0;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  color: var(--color-text);
}
.fu-ind-value .cite {
  margin-left: 4px;
}
.fu-asof {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-muted);
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
  /* Stronger than the hero's tint: these rows sit on the soft panel ground. */
  background: color-mix(in oklch, var(--mkt-brand-chart) 16%, var(--color-surface-container-low));
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
.fu-date {
  white-space: nowrap;
}

@media (max-width: 900px) {
  .flows {
    grid-template-columns: minmax(0, 1fr);
    gap: 48px;
  }
  .fu-sources .source-link {
    line-height: 24px;
  }
}
</style>
