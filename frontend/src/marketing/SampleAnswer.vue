<template>
  <!-- Inline sample answer in the citations section: a real answer the app gave on
       2026-11-16, word for word, with its five real sources. Every figure was checked
       against the report it cites. Mirrors the app's answer: quiet [n] chips and a
       collapsed sources line that opens a # · Source · Date ledger (see SourceList.vue). -->
  <figure ref="root" class="sample" aria-label="Sample answer" @click="onCiteClick">
    <div class="sample-head">
      <HandMark :size="26" :radius="7" :stroke="1.7" solid />
      <span class="sample-title">Humanitaria</span>
      <span class="sample-tag" aria-hidden="true">Sample answer</span>
    </div>
    <div class="sample-body">
      <div class="q">How many people are internally displaced in Haiti, and where?</div>
      <div class="a">
        <p>
          In Haiti, as of late 2026, there are an estimated
          <strong>1.5 million internally displaced persons (IDPs)</strong>, accounting for
          approximately 12 percent of the population<template v-for="n in [1, 2, 3, 5]" :key="n"
            ><a class="cite" :href="'#sample-src-' + n" :data-cite="n">{{ n }}</a></template
          >.
        </p>
        <p>Regarding their locations:</p>
        <ul>
          <li>
            <strong>Geographical Distribution:</strong> Nearly 80 percent of the displaced
            population is now located outside of the capital, Port-au-Prince, as violence spreads
            across the country<template v-for="n in [1, 3]" :key="n"
              ><a class="cite" :href="'#sample-src-' + n" :data-cite="n">{{ n }}</a></template
            >. Earlier data from mid-2026 showed concentrations in the Grand Sud (39%) and Ouest
            (28%) departments, alongside growing numbers in the Centre and Artibonite departments<a
              class="cite"
              href="#sample-src-4"
              data-cite="4"
              >4</a
            >.
          </li>
          <li>
            <strong>Recent Displacement Hotspots:</strong> Ongoing armed violence and clashes
            continue to displace thousands in specific areas. For example, recent attacks have
            uprooted people in the Artibonite department (including Petite-Rivière de l’Artibonite
            and Gros Morne) and the Ouest department (including Couyo in Arcahaie and
            Croix-des-Bouquets on the outskirts of Port-au-Prince)<template
              v-for="n in [1, 5]"
              :key="n"
              ><a class="cite" :href="'#sample-src-' + n" :data-cite="n">{{ n }}</a></template
            >.
          </li>
        </ul>
        <p>
          Most of those displaced are currently staying with host families rather than in
          displacement sites<template v-for="n in [1, 4]" :key="n"
            ><a class="cite" :href="'#sample-src-' + n" :data-cite="n">{{ n }}</a></template
          >.
        </p>
        <details class="sources" @toggle="open = $event.target.open">
          <summary class="sources-summary">
            <span>5 sources</span>
            <span aria-hidden="true">·</span>
            <span>OCHA, WFP, IOM +1</span>
            <span aria-hidden="true">·</span>
            <span class="sources-toggle">{{ open ? 'Hide' : 'Show' }}</span>
          </summary>
          <div class="ledger">
            <table class="ledger-table">
              <thead>
                <tr>
                  <th scope="col" class="col-index">#</th>
                  <th scope="col">Source</th>
                  <th scope="col" class="col-date">Date</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="src in sources"
                  :id="'sample-src-' + src.n"
                  :key="src.n"
                  class="source-item"
                  :data-srcid="src.n"
                >
                  <td class="col-index">
                    <span class="source-index">{{ src.n }}</span>
                  </td>
                  <td>
                    <a
                      class="source-title"
                      :href="src.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      >{{ src.title }}</a
                    >
                    <span class="source-meta">{{ src.meta }}</span>
                  </td>
                  <td class="col-date">
                    <time :datetime="src.date">{{ src.date }}</time>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </div>
  </figure>
</template>

<script setup>
import { ref } from 'vue'
import HandMark from './HandMark.vue'
import { revealSource } from '../utils/sources.js'

const root = ref(null)
// Mirrors the <details> state for the Show/Hide label; a chip may open it directly.
const open = ref(false)

// The answer's real sources on ReliefWeb, as the app listed them (titles in the
// report's own language).
const sources = [
  {
    n: 1,
    title: 'Latin America & The Caribbean Weekly Situation Update as of 6 November 2026',
    meta: 'OCHA · Haiti',
    date: '2026-11-06',
    url: 'https://reliefweb.int/report/haiti/latin-america-caribbean-weekly-situation-update-6-november-2026',
  },
  {
    n: 2,
    title: 'WFP Haiti Country Brief, October 2026',
    meta: 'WFP · Haiti',
    date: '2026-11-04',
    url: 'https://reliefweb.int/report/haiti/wfp-haiti-country-brief-october-2026',
  },
  {
    n: 3,
    title:
      'Nuevos datos de la OIM: Cerca de 1,5 millones de personas desplazadas en Haití mientras aumentan los riesgos de huracanes',
    meta: 'IOM · Haiti',
    date: '2026-09-25',
    url: 'https://reliefweb.int/report/haiti/nuevos-datos-de-la-oim-cerca-de-15-millones-de-personas-desplazadas-en-haiti-mientras-aumentan-los-riesgos-de-huracanes',
  },
  {
    n: 4,
    title: 'Haïti : Cluster Abris et Biens non alimentaires - Aperçu de la réponse : aout 2026',
    meta: 'IOM · Haiti',
    date: '2026-09-21',
    url: 'https://reliefweb.int/report/haiti/haiti-cluster-abris-et-biens-non-alimentaires-apercu-de-la-reponse-aout-2026',
  },
  {
    n: 5,
    title:
      'Oficina Integrada de las Naciones Unidas en Haití - Informe del Secretario General (S/2026/800)',
    meta: 'UN Security Council · Haiti',
    date: '2026-10-20',
    url: 'https://reliefweb.int/report/haiti/oficina-integrada-de-las-naciones-unidas-en-haiti-informe-del-secretario-general-s2026800',
  },
]

// Same behaviour as a chip in the app: open the ledger and point at the cited row.
function onCiteClick(event) {
  const cite = event.target.closest('.cite')
  if (!cite) return
  event.preventDefault()
  revealSource(root.value, cite.dataset.cite)
}
</script>
