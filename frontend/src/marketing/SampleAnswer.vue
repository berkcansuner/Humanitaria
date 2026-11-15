<template>
  <!-- Inline sample answer in the citations section. Example content, labelled as such
       in the card header. Mirrors the app's answer: quiet [n] chips and a collapsed
       sources line that opens a # · Source · Date ledger (see SourceList.vue). -->
  <figure ref="root" class="sample" aria-label="Sample answer" @click="onCiteClick">
    <div class="sample-head">
      <HandMark :size="26" :radius="7" :stroke="1.7" solid />
      <span class="sample-title">Humanitaria</span>
      <span class="sample-tag" aria-hidden="true">Sample answer</span>
    </div>
    <div class="sample-body">
      <div class="q">What's the latest humanitarian situation in Sudan?</div>
      <div class="a">
        <h3>Sudan — current situation</h3>
        <p>
          Sudan is facing one of the world's largest displacement crises, with
          <strong>millions forced from their homes</strong> since April 2023 — most displaced inside
          the country, and many seeking refuge across borders<a
            class="cite"
            href="#sample-src-1"
            data-cite="1"
            >1</a
          >.
        </p>
        <p>
          Food insecurity has deteriorated sharply. Market collapse and disrupted farming have
          pushed several regions to <strong>critical levels of acute food insecurity</strong>, with
          famine conditions confirmed in some areas<a
            class="cite"
            href="#sample-src-2"
            data-cite="2"
            >2</a
          >.
        </p>
        <p>The health system is under severe strain:</p>
        <ul>
          <li>
            A large share of health facilities are partly or fully out of service<a
              class="cite"
              href="#sample-src-3"
              data-cite="3"
              >3</a
            >
          </li>
          <li>
            Outbreaks of cholera and malaria are on the rise<a
              class="cite"
              href="#sample-src-3"
              data-cite="3"
              >3</a
            >
          </li>
          <li>
            Supplies of medicine and essentials are limited<a
              class="cite"
              href="#sample-src-2"
              data-cite="2"
              >2</a
            >
          </li>
        </ul>
        <p>
          Humanitarian access remains difficult in many areas due to insecurity and bureaucratic
          constraints<a class="cite" href="#sample-src-1" data-cite="1">1</a>.
        </p>
        <details class="sources" @toggle="open = $event.target.open">
          <summary class="sources-summary">
            <span>3 sources</span>
            <span aria-hidden="true">·</span>
            <span>OCHA, IPC, WHO</span>
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
                    <span class="source-title">{{ src.title }}</span>
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

// Example sources only: titles and publishers illustrate the format, so they are not links.
const sources = [
  { n: 1, title: 'Sudan Situation Report', meta: 'OCHA · Sudan', date: '2025-03-12' },
  { n: 2, title: 'Acute Food Insecurity Snapshot', meta: 'IPC · Sudan', date: '2024-12-20' },
  { n: 3, title: 'Sudan Health Cluster Bulletin', meta: 'WHO · Sudan', date: '2025-02-28' },
]

// Same behaviour as a chip in the app: open the ledger and point at the cited row.
function onCiteClick(event) {
  const cite = event.target.closest('.cite')
  if (!cite) return
  event.preventDefault()
  revealSource(root.value, cite.dataset.cite)
}
</script>
