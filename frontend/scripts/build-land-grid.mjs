// One-off generator (run by hand): node scripts/build-land-grid.mjs
// Samples Natural Earth 110m land (public domain, via world-atlas) on a regular
// lat/lon grid and writes the cell centres that fall on land.
import { readFileSync, writeFileSync } from 'node:fs'
import { feature } from 'topojson-client'

const STEP = 2.4
const LAT_LIMIT = 70
const topo = JSON.parse(readFileSync('node_modules/world-atlas/land-110m.json', 'utf8'))
const land = feature(topo, topo.objects.land)
const polygons = land.features
  ? land.features.flatMap((f) => toPolys(f.geometry))
  : toPolys(land.geometry)

function toPolys(g) {
  return g.type === 'Polygon' ? [g.coordinates] : g.coordinates
}

// Even-odd ray casting across all rings of a polygon (holes included).
function inPolygon(lon, lat, rings) {
  let inside = false
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i]
      const [xj, yj] = ring[j]
      if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
        inside = !inside
      }
    }
  }
  return inside
}

const round = (n) => Math.round(n * 100) / 100
const cells = []
for (let lat = LAT_LIMIT - STEP / 2; lat > -LAT_LIMIT; lat -= STEP) {
  for (let lon = -180 + STEP / 2; lon < 180; lon += STEP) {
    if (polygons.some((p) => inPolygon(lon, lat, p))) cells.push([round(lat), round(lon)])
  }
}

const out = { source: 'Natural Earth 110m land via world-atlas', step: STEP, cells }
writeFileSync('src/marketing/data/land.json', JSON.stringify(out))
console.log(cells.length, 'cells')
