<script setup>
import { computed, shallowRef } from 'vue'
import { formatCompact, linePath, monthLabel, nearestIndex } from './landingKit.js'

const props = defineProps({
  // [ISO date, value] pairs, oldest first: the observed series of a tested window.
  series: { type: Array, required: true },
  label: { type: String, required: true },
})

// Drawing box in SVG units; the SVG stretches to the panel width.
const W = 300
const H = 64

const points = computed(() => props.series.map(([d, v]) => [Date.parse(d), v]))
const xs = computed(() => points.value.map((p) => p[0]))
const bounds = computed(() => {
  const values = props.series.map((p) => p[1])
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const pad = (hi - lo) * 0.12
  return { yMin: lo - pad, yMax: hi + pad }
})
const line = computed(() => linePath(points.value, W, H, bounds.value.yMin, bounds.value.yMax))

// Share of the drawing box for an HTML marker at point i (round dots on a stretched SVG).
function at(i) {
  const { yMin, yMax } = bounds.value
  const [t0, t1] = [xs.value[0], xs.value[xs.value.length - 1]]
  const [x, v] = points.value[i]
  return {
    left: `${((x - t0) / (t1 - t0 || 1)) * 100}%`,
    top: `${((yMax - v) / (yMax - yMin)) * 100}%`,
  }
}

const first = computed(() => props.series[0])
const last = computed(() => props.series[props.series.length - 1])
const lastDot = computed(() => at(props.series.length - 1))

// Hover: the nearest observation replaces the start-to-latest readout.
const hovered = shallowRef(null)
function onHover(event) {
  const box = event.currentTarget.getBoundingClientRect()
  const [t0, t1] = [xs.value[0], xs.value[xs.value.length - 1]]
  hovered.value = nearestIndex(xs.value, t0 + ((event.clientX - box.left) / box.width) * (t1 - t0))
}
const marker = computed(() => (hovered.value === null ? null : at(hovered.value)))
const readout = computed(() => {
  if (hovered.value === null) {
    return `${formatCompact(first.value[1])} → ${formatCompact(last.value[1])}`
  }
  const [d, v] = props.series[hovered.value]
  return `${monthLabel(d)} · ${formatCompact(v)}`
})
const summary = computed(
  () =>
    `${props.label}: ${formatCompact(first.value[1])} in ${monthLabel(first.value[0])}, ` +
    `${formatCompact(last.value[1])} in ${monthLabel(last.value[0])}, ` +
    `${props.series.length} observations.`,
)
</script>

<template>
  <figure class="wc">
    <p class="wc-readout" aria-hidden="true">{{ readout }}</p>
    <div class="wc-chart" @pointermove="onHover" @pointerleave="hovered = null">
      <svg
        class="wc-svg"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="none"
        role="img"
        :aria-label="summary"
      >
        <path class="wc-line" :d="line" />
      </svg>
      <span class="wc-dot" :style="lastDot" aria-hidden="true"></span>
      <template v-if="marker">
        <span class="wc-crosshair" :style="{ left: marker.left }" aria-hidden="true"></span>
        <span class="wc-marker" :style="marker" aria-hidden="true"></span>
      </template>
    </div>
    <div class="wc-axis" aria-hidden="true">
      <span>{{ monthLabel(first[0]) }}</span
      ><span>{{ monthLabel(last[0]) }}</span>
    </div>
  </figure>
</template>

<style scoped>
.wc {
  margin: 14px 0 0;
}
.wc-readout {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.wc-chart {
  position: relative;
  height: 64px;
  margin-top: 8px;
  cursor: crosshair;
}
.wc-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.wc-line {
  fill: none;
  stroke: var(--mkt-brand-chart);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.wc-dot,
.wc-marker {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 2px var(--color-surface-container-low);
}
.wc-dot {
  left: 100%;
  background: var(--mkt-coral);
}
.wc-marker {
  background: var(--color-text);
}
.wc-crosshair {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--color-border-strong);
}
.wc-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-muted);
}
</style>
