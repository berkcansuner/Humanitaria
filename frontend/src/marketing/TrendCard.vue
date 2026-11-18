<script setup>
import { computed, shallowRef } from 'vue'
import {
  formatCompact,
  linePath,
  monthLabel as monthOf,
  nearestIndex,
  peakChange,
  peakPhrase,
} from './landingKit.js'

const props = defineProps({
  // [ISO date, value] pairs, oldest first.
  series: { type: Array, required: true },
  title: { type: String, required: true },
  credit: { type: String, required: true },
})

// Drawing box in SVG units; the SVG stretches to the card width.
const W = 300
const H = 56

const points = computed(() => props.series.map(([d, v]) => [Date.parse(d), v]))
const bounds = computed(() => {
  const values = props.series.map((p) => p[1])
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const pad = (hi - lo) * 0.12
  return { yMin: lo - pad, yMax: hi + pad }
})
const line = computed(() => linePath(points.value, W, H, bounds.value.yMin, bounds.value.yMax))
const area = computed(() => `${line.value} L${W},${H} L0,${H} Z`)

const change = computed(() => peakChange(props.series))
const latest = computed(() => change.value.latest)
// The latest point, as a share of the drawing box, for the HTML marker.
const dot = computed(() => {
  const { yMin, yMax } = bounds.value
  return { top: `${((yMax - latest.value[1]) / (yMax - yMin)) * 100}%` }
})

// Hover readout: the nearest point replaces the headline figure.
const hovered = shallowRef(null)
const xs = computed(() => points.value.map((p) => p[0]))
function onHover(event) {
  const box = event.currentTarget.getBoundingClientRect()
  const [t0, t1] = [xs.value[0], xs.value[xs.value.length - 1]]
  const t = t0 + ((event.clientX - box.left) / box.width) * (t1 - t0)
  hovered.value = nearestIndex(xs.value, t)
}
const readout = computed(() => (hovered.value === null ? null : props.series[hovered.value]))
const marker = computed(() => {
  if (hovered.value === null) return null
  const { yMin, yMax } = bounds.value
  const [t0, t1] = [xs.value[0], xs.value[xs.value.length - 1]]
  const [x, v] = points.value[hovered.value]
  return {
    left: `${((x - t0) / (t1 - t0 || 1)) * 100}%`,
    top: `${((yMax - v) / (yMax - yMin)) * 100}%`,
  }
})

const firstMonth = computed(() => monthOf(props.series[0][0]))
const lastMonth = computed(() => monthOf(latest.value[0]))
const summary = computed(
  () =>
    `${props.title}: ${formatCompact(latest.value[1])} in ${lastMonth.value}, ` +
    `${peakPhrase(props.series)} of ${formatCompact(change.value.peak[1])}. ` +
    `Series from ${firstMonth.value} to ${lastMonth.value}.`,
)
</script>

<template>
  <figure class="trend-card">
    <figcaption class="tc-title">{{ title }}</figcaption>
    <p class="tc-figure">
      <span class="tc-value">{{ formatCompact((readout ?? latest)[1]) }}</span>
      <span v-if="readout" class="tc-change">{{ monthOf(readout[0]) }}</span>
      <span v-else class="tc-change">{{ peakPhrase(series) }}</span>
    </p>
    <div class="tc-chart" @pointermove="onHover" @pointerleave="hovered = null">
      <svg
        class="tc-svg"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="none"
        role="img"
        :aria-label="summary"
      >
        <path class="trend-area" :d="area" />
        <path class="trend-line" :d="line" />
      </svg>
      <span class="trend-dot" :style="dot" aria-hidden="true"></span>
      <template v-if="marker">
        <span class="tc-crosshair" :style="{ left: marker.left }" aria-hidden="true"></span>
        <span class="tc-marker" :style="marker" aria-hidden="true"></span>
      </template>
    </div>
    <div class="tc-axis" aria-hidden="true">
      <span>{{ firstMonth }}</span
      ><span>{{ lastMonth }}</span>
    </div>
    <p class="tc-credit">{{ credit }}</p>
  </figure>
</template>

<style scoped>
.trend-card {
  margin: 0;
  padding: 16px 18px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow:
    0 1px 2px rgb(11 29 46 / 0.06),
    0 18px 40px -18px rgb(11 29 46 / 0.32);
}
.tc-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.tc-figure {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2px 10px;
  margin-top: 4px;
}
.tc-value {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  color: var(--color-text);
}
.tc-change {
  font-size: 12.5px;
  color: var(--color-text-secondary);
}
.tc-chart {
  position: relative;
  height: 56px;
  margin-top: 10px;
}
.tc-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.trend-area {
  fill: var(--mkt-brand-tint);
  opacity: 0.85;
}
.trend-line {
  fill: none;
  stroke: var(--mkt-brand-chart);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.trend-dot {
  position: absolute;
  right: 0;
  width: 10px;
  height: 10px;
  margin: -5px -5px 0 0;
  border-radius: 50%;
  background: var(--mkt-coral);
  box-shadow: 0 0 0 2px var(--color-surface);
}
.tc-crosshair {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--color-border-strong);
  pointer-events: none;
}
.tc-marker {
  position: absolute;
  width: 8px;
  height: 8px;
  margin: -4px 0 0 -4px;
  border-radius: 50%;
  background: var(--mkt-brand-chart);
  box-shadow: 0 0 0 2px var(--color-surface);
  pointer-events: none;
}
.tc-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-muted);
}
.tc-credit {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-muted);
  overflow-wrap: anywhere;
}
</style>
