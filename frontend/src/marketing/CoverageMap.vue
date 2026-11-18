<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import coverage from './data/coverage.json'
import land from './data/land.json'
import { project, pulseRadius, prefersReducedMotion, drawablePoints } from './landingKit.js'

const BASE = '#C9D3DE'
const LAND = '#D5DDE7' // quieter than BASE so country points stay the foreground
const PULSE = '10, 143, 136' // brand-chart #0A8F88
const PERIOD = 4200 // ms per pulse cycle

// `figure`: the map is the subject (Coverage section), not a backdrop (hero): each
// country also gets a solid dot sized by its report volume, and wider rings.
const props = defineProps({ figure: { type: Boolean, default: false } })
const RING_SCALE = 2.2

const canvas = ref(null)
const points = drawablePoints(coverage.points)
const maxReports = Math.max(1, ...points.map((p) => p.reports))
// Stable phase offset per country so rings never pulse in unison.
const phases = points.map((p) => {
  let h = 0
  for (const c of String(p.iso3 ?? '')) h = (h * 31 + c.charCodeAt(0)) % 997
  return h / 997
})

let ctx = null
let landLayer = null // offscreen canvas: static land dots, redrawn only on resize
let width = 0
let height = 0
let frame = 0
let inView = false
let resizeObserver = null
let viewObserver = null
const reduced = prefersReducedMotion()

function drawLandLayer(dpr) {
  landLayer ??= document.createElement('canvas')
  landLayer.width = Math.round(width * dpr)
  landLayer.height = Math.round(height * dpr)
  const lctx = landLayer.getContext('2d')
  if (!lctx) return
  lctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  lctx.fillStyle = LAND
  const r = Math.max(0.8, (land.step / 360) * width * 0.3)
  lctx.beginPath()
  for (const [lat, lon] of land.cells) {
    const { x, y } = project(lat, lon, width, height)
    lctx.moveTo(x + r, y)
    lctx.arc(x, y, r, 0, Math.PI * 2)
  }
  lctx.fill()
}

function draw(now) {
  ctx.clearRect(0, 0, width, height)
  if (landLayer?.width) {
    ctx.drawImage(landLayer, 0, 0, width, height)
  }
  points.forEach((p, i) => {
    const { x, y } = project(p.lat, p.lon, width, height)
    // As a figure, marks shrink with the map below 760px so a phone stays legible.
    const size = pulseRadius(p.reports, maxReports) * (props.figure ? Math.min(1, width / 760) : 1)
    const core = props.figure ? size * 0.7 : 1.2
    ctx.fillStyle = props.figure ? `rgba(${PULSE}, 0.7)` : BASE
    ctx.beginPath()
    ctx.arc(x, y, core, 0, Math.PI * 2)
    ctx.fill()

    const max = props.figure ? size * RING_SCALE : size
    // Static frame (reduced motion): hold each ring at a mid-cycle phase.
    const t = reduced ? 0.5 : (now / PERIOD + phases[i]) % 1
    ctx.strokeStyle = `rgba(${PULSE}, ${0.35 * (1 - t)})`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(x, y, core + (max - core) * t, 0, Math.PI * 2)
    ctx.stroke()
  })
}

function tick(now) {
  draw(now)
  frame = requestAnimationFrame(tick)
}

function stop() {
  cancelAnimationFrame(frame)
  frame = 0
}

// The loop runs only while the canvas is on screen and the tab is visible.
function sync() {
  if (reduced) return
  const shouldRun = inView && document.visibilityState === 'visible'
  if (shouldRun && !frame) frame = requestAnimationFrame(tick)
  else if (!shouldRun) stop()
}

function resize() {
  const el = canvas.value
  const dpr = window.devicePixelRatio || 1
  width = el.clientWidth
  height = el.clientHeight
  el.width = Math.round(width * dpr)
  el.height = Math.round(height * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  drawLandLayer(dpr)
  draw(performance.now())
}

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  resize()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(canvas.value)
  if (reduced) return
  viewObserver = new IntersectionObserver((entries) => {
    inView = entries[entries.length - 1].isIntersecting
    sync()
  })
  viewObserver.observe(canvas.value)
  document.addEventListener('visibilitychange', sync)
})

onBeforeUnmount(() => {
  stop()
  resizeObserver?.disconnect()
  viewObserver?.disconnect()
  landLayer = null
  document.removeEventListener('visibilitychange', sync)
})
</script>

<template>
  <canvas ref="canvas" class="coverage-map" aria-hidden="true"></canvas>
</template>

<style scoped>
.coverage-map {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
