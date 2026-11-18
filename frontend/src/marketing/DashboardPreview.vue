<script setup>
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import syria from './data/syria.json'
import {
  axisTicks,
  countUp,
  dayLabel,
  formatCompact,
  formatNumber,
  linePath,
  monthLabel,
  nearestIndex,
  peakChange,
  peakPhrase,
  signedPct,
  yearChange,
} from './landingKit.js'

gsap.registerPlugin(ScrollTrigger)

const { t, locale } = useI18n()

// The chart is the hero card's series: Syrian refugees abroad, annual UNHCR figures.
const unhcrCredit = `${syria.refugees.credit} · HDX HAPI`
const series = syria.refugees.series
const { latest, peak } = peakChange(series)
const yearOf = (iso) => Number(iso.slice(0, 4))
const returnees = yearChange(syria.returnees.series.map(([d, v]) => [yearOf(d), v]))
const funding = yearChange(syria.funding)

// Labels and formats follow the interface language; `to` (the counted value) does not,
// so a count-up that is running when the language changes ends on the right text.
const kpis = computed(() => {
  const l = locale.value
  const compact = (v) => formatCompact(v, l)
  const change = (c) => t('landing.dash.change', { pct: signedPct(c.pct, l), year: c.prevYear })
  return [
    {
      key: 'returnees',
      label: t('landing.dash.returnees', { year: returnees.year }),
      to: returnees.value,
      format: compact,
      note: change(returnees),
      source: `${syria.returnees.credit} · HDX HAPI`,
    },
    {
      key: 'refugees',
      label: t('landing.dash.refugees'),
      to: syria.refugees.latest,
      format: compact,
      note: t('landing.dash.refugeesNote', { year: syria.refugees.period }),
      source: unhcrCredit,
    },
    {
      key: 'funding',
      label: t('landing.dash.funding', { year: funding.year }),
      to: funding.value,
      format: (v) => t('landing.dash.usd', { amount: compact(v) }),
      note: change(funding),
      source: 'OCHA FTS · HDX HAPI',
    },
    {
      key: 'reports',
      label: t('landing.dash.reports'),
      to: syria.reports.count,
      format: (v) => formatNumber(Math.round(v), l),
      note: t('landing.dash.reportsNote', { date: dayLabel(syria.reports.since, l) }),
      source: 'ReliefWeb',
    },
  ].map((k) => ({ ...k, text: k.format(k.to) }))
})

// Refugee chart: drawing box in SVG units; the SVG stretches to the panel.
const W = 600
const H = 200
const STEP = 1_000_000
const values = series.map((p) => p[1])
const ticks = axisTicks(Math.min(...values), Math.max(...values), STEP)
const yMin = ticks[0]
const yMax = ticks[ticks.length - 1]
const times = series.map(([d]) => Date.parse(d))
const t0 = times[0]
const t1 = times[times.length - 1]
const xShare = (time) => (time - t0) / (t1 - t0)
const yShare = (v) => (yMax - v) / (yMax - yMin)
const pct = (share) => `${share * 100}%`

const line = linePath(
  series.map(([, v], i) => [times[i], v]),
  W,
  H,
  yMin,
  yMax,
)
const gridlines = computed(() =>
  ticks.map((v) => ({ value: v, label: formatCompact(v, locale.value), top: pct(yShare(v)) })),
)
// Annual points: every other year is labelled, from the first.
const firstYear = yearOf(series[0][0])
const lastYear = yearOf(latest[0])
const years = []
for (let y = firstYear; y <= lastYear; y += 2) {
  years.push({ label: String(y), left: pct(xShare(Date.UTC(y, 0, 1))) })
}
const latestDot = { top: pct(yShare(latest[1])) }
const range = `${firstYear} – ${lastYear}`
const chartSummary = computed(() =>
  t('landing.trend.summary', {
    title: t('landing.trend.title'),
    value: formatCompact(latest[1], locale.value),
    last: lastYear,
    phrase: peakPhrase(series, t, locale.value, { annual: true }),
    peak: formatCompact(peak[1], locale.value),
    first: firstYear,
  }),
)

// Hover readout: the nearest observation under the pointer.
const hovered = shallowRef(null)
function onHover(event) {
  const box = event.currentTarget.getBoundingClientRect()
  hovered.value = nearestIndex(times, t0 + ((event.clientX - box.left) / box.width) * (t1 - t0))
}
const readout = computed(() => {
  if (hovered.value === null) return null
  const [d, v] = series[hovered.value]
  const x = xShare(times[hovered.value])
  const y = yShare(v)
  return {
    text: `${yearOf(d)} · ${formatCompact(v, locale.value)}`,
    line: { left: pct(x) },
    dot: { left: pct(x), top: pct(y) },
    // Above the point, or below it near the top; kept inside the plot at either edge.
    tip: { left: pct(Math.min(0.88, Math.max(0.12, x))), top: pct(y) },
    below: y < 0.3,
  }
})

// Host countries in the latest year, named in the interface language. HAPI gives
// English names; a name without a region code here is shown as HAPI writes it.
const HOST_REGIONS = {
  Türkiye: 'TR',
  Germany: 'DE',
  Lebanon: 'LB',
  Jordan: 'JO',
  Iraq: 'IQ',
  Egypt: 'EG',
  Sweden: 'SE',
  Austria: 'AT',
  Netherlands: 'NL',
}
const hosts = syria.refugees.by_host
const topHost = hosts[0][1]
const regions = computed(() => {
  const names = new Intl.DisplayNames([locale.value], { type: 'region' })
  return hosts.map(([name, value]) => ({
    key: name,
    name: HOST_REGIONS[name] ? names.of(HOST_REGIONS[name]) : name,
    value: formatCompact(value, locale.value),
    width: pct(value / topHost),
  }))
})

const root = useTemplateRef('root')

// On first view: tiles and panels rise in, figures count up, the line draws and
// the bars grow. Reduced motion never runs it, so everything renders final.
let mm = null
onMounted(() => {
  mm = gsap.matchMedia()
  mm.add(
    '(prefers-reduced-motion: no-preference)',
    (ctx) => {
      const q = gsap.utils.selector(root.value)
      // DOM order is the kpis order (template refs in v-for are not ordered).
      const kpiValues = q('.kpi-value')
      ctx.add('count', () => {
        // The format is read on every frame, so a language switch mid-count
        // continues in the new language.
        kpiValues.forEach((el, i) =>
          countUp(el, kpis.value[i].to, {
            duration: 1.4,
            format: (v) => kpis.value[i].format(v),
          }),
        )
      })
      gsap
        .timeline({
          defaults: { ease: 'expo.out', duration: 0.9 },
          scrollTrigger: { trigger: q('.dash')[0], start: 'top 75%', once: true },
        })
        .from(q('.kpi, .panel'), { y: 24, autoAlpha: 0, stagger: 0.07 }, 0)
        .call(() => ctx.count(), null, 0.05)
        .from(q('.dp-line'), { strokeDashoffset: 1, duration: 1.8, ease: 'power2.inOut' }, 0.45)
        .from(q('.dp-dot'), { scale: 0, autoAlpha: 0, duration: 0.5, ease: 'back.out(2.4)' }, 2.1)
        .from(q('.dp-bar'), { scaleX: 0, transformOrigin: '0 50%', stagger: 0.08 }, 0.5)
      // Reduced motion switched on mid-count: show the final figures.
      return () => kpiValues.forEach((el, i) => (el.textContent = kpis.value[i].text))
    },
    root.value,
  )
})

onBeforeUnmount(() => mm?.revert())
</script>

<template>
  <section id="dashboards" ref="root" class="section night">
    <div class="wrap">
      <div class="section-head">
        <h2>{{ t('landing.dash.title') }}</h2>
        <p>{{ t('landing.dash.lede') }}</p>
      </div>

      <div class="dash">
        <div class="dash-head">
          <h3>{{ t('landing.country') }}</h3>
          <time class="dash-month" :datetime="syria.generated">{{
            monthLabel(syria.generated, locale)
          }}</time>
          <span class="dash-label">{{ t('landing.dash.label') }}</span>
        </div>

        <dl class="kpis">
          <div v-for="k in kpis" :key="k.key" class="kpi">
            <dt>{{ k.label }}</dt>
            <dd class="kpi-value">{{ k.text }}</dd>
            <dd class="kpi-note">{{ k.note }}</dd>
            <dd class="kpi-src">{{ k.source }}</dd>
          </div>
        </dl>

        <div class="panels">
          <figure class="panel">
            <i18n-t keypath="landing.dash.chart" tag="figcaption" scope="global">
              <template #range>
                <span class="dp-range">{{ range }}</span>
              </template>
            </i18n-t>
            <div class="dp-chart">
              <div class="dp-y" aria-hidden="true">
                <span v-for="g in gridlines" :key="g.value" :style="{ top: g.top }">{{
                  g.label
                }}</span>
              </div>
              <div class="dp-plot" @pointermove="onHover" @pointerleave="hovered = null">
                <span
                  v-for="g in gridlines"
                  :key="g.value"
                  class="dp-grid"
                  :style="{ top: g.top }"
                  aria-hidden="true"
                ></span>
                <svg
                  class="dp-svg"
                  :viewBox="`0 0 ${W} ${H}`"
                  preserveAspectRatio="none"
                  role="img"
                  :aria-label="chartSummary"
                >
                  <path class="dp-line" :d="line" pathLength="1" />
                </svg>
                <span class="dp-dot" :style="latestDot" aria-hidden="true"></span>
                <template v-if="readout">
                  <span class="dp-crosshair" :style="readout.line" aria-hidden="true"></span>
                  <span class="dp-marker" :style="readout.dot" aria-hidden="true"></span>
                  <span
                    class="dp-tip"
                    :class="{ below: readout.below }"
                    :style="readout.tip"
                    aria-hidden="true"
                    >{{ readout.text }}</span
                  >
                </template>
                <div class="dp-x" aria-hidden="true">
                  <span v-for="y in years" :key="y.label" :style="{ left: y.left }">{{
                    y.label
                  }}</span>
                </div>
              </div>
            </div>
          </figure>

          <figure class="panel">
            <figcaption>{{ t('landing.dash.bars', { year: syria.refugees.period }) }}</figcaption>
            <ul class="dp-bars">
              <li v-for="r in regions" :key="r.key">
                <span class="dp-name">{{ r.name }}</span>
                <span class="dp-track"><i class="dp-bar" :style="{ width: r.width }"></i></span>
                <b>{{ r.value }}</b>
              </li>
            </ul>
          </figure>
        </div>
        <p class="dp-src">{{ t('landing.dash.source', { credit: unhcrCredit }) }}</p>

        <p class="dp-foot">{{ t('landing.dash.foot') }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.night {
  background: var(--mkt-night);
  color: var(--mkt-night-ink);
}
.night .section-head p {
  color: var(--mkt-night-ink-2);
}
.dash {
  padding: 24px;
  background: var(--mkt-night-2);
  border: 1px solid var(--mkt-night-line);
  border-radius: 18px;
}
.dash-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  font-size: 14px;
  color: var(--mkt-night-ink-2);
}
.dash-head h3 {
  font-size: 18px;
  font-weight: 650;
  color: var(--mkt-night-ink);
}
.dash-month {
  padding: 3px 9px;
  font-size: 12px;
  border: 1px solid var(--mkt-night-line);
  border-radius: 999px;
}
.dash-label {
  margin-left: auto;
}

.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0 0;
}
.kpi {
  display: flex;
  flex-direction: column;
  padding: 14px 16px;
  border: 1px solid var(--mkt-night-line);
  border-radius: 12px;
}
.kpi dt {
  font-size: 13px;
  font-weight: 550;
  color: var(--mkt-night-ink-2);
}
.kpi dd {
  margin-left: 0;
}
.kpi-value {
  margin-top: 6px;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  color: var(--mkt-night-ink);
}
.kpi-note {
  margin-top: 2px;
  font-size: 13px;
  color: var(--mkt-night-ink-2);
}
.kpi-src {
  margin-top: auto;
  padding-top: 12px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--mkt-night-ink-2);
  overflow-wrap: anywhere;
}

.panels {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 14px;
  margin-top: 14px;
}
.panel {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 16px;
  border: 1px solid var(--mkt-night-line);
  border-radius: 12px;
}
.dp-range {
  white-space: nowrap;
}
.panel figcaption {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--mkt-night-ink);
}

.dp-chart {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 8px;
  margin-top: 16px;
  padding-bottom: 24px;
}
.dp-y {
  position: relative;
  height: 200px;
}
.dp-y span,
.dp-x span {
  position: absolute;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1;
  color: var(--mkt-night-ink-2);
}
.dp-y span {
  right: 0;
  transform: translateY(-50%);
}
.dp-plot {
  position: relative;
  height: 200px;
  touch-action: pan-y;
}
.dp-grid {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--mkt-night-line);
}
.dp-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.dp-line {
  fill: none;
  stroke: var(--mkt-teal-d);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 0;
  vector-effect: non-scaling-stroke;
}
.dp-dot,
.dp-marker {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.dp-dot {
  right: 0;
  width: 10px;
  height: 10px;
  margin: -5px -5px 0 0;
  background: var(--mkt-coral-d);
  box-shadow: 0 0 0 2px var(--mkt-night-2);
}
.dp-marker {
  width: 8px;
  height: 8px;
  margin: -4px 0 0 -4px;
  background: var(--mkt-teal-d);
  box-shadow: 0 0 0 2px var(--mkt-night-2);
}
.dp-crosshair {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--mkt-night-ink-2);
  opacity: 0.5;
  pointer-events: none;
}
.dp-tip {
  position: absolute;
  transform: translate(-50%, calc(-100% - 12px));
  padding: 4px 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: nowrap;
  color: var(--mkt-night-ink);
  background: var(--mkt-night);
  border: 1px solid var(--mkt-night-line);
  border-radius: 6px;
  pointer-events: none;
}
.dp-tip.below {
  transform: translate(-50%, 12px);
}
.dp-x {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 10px);
}
.dp-x span {
  transform: translateX(-50%);
}

.dp-bars {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-around;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}
.dp-bars li {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) 56px;
  gap: 10px;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  color: var(--mkt-night-ink-2);
}
.dp-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dp-bar {
  display: block;
  height: 12px;
  border-radius: 0 4px 4px 0;
  background: var(--mkt-teal-d);
}
.dp-bars b {
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--mkt-night-ink);
}
.dp-src {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--mkt-night-ink-2);
  overflow-wrap: anywhere;
}
.dp-foot {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--mkt-night-line);
  font-size: 13px;
  color: var(--mkt-night-ink-2);
}

@media (max-width: 1023px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .panels {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 560px) {
  .dash {
    padding: 16px;
  }
  .kpis {
    grid-template-columns: minmax(0, 1fr);
  }
  .dash-label {
    margin-left: 0;
    flex-basis: 100%;
  }
  .dp-bars li {
    grid-template-columns: 100px minmax(0, 1fr) 56px;
  }
}
</style>
