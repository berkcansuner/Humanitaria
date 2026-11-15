<template>
  <!-- Quiet Archive: one count line at rest; "Show" opens a # · Source · Date ledger.
       Native <details> keeps keyboard and screen-reader behaviour for free, and lets
       revealSource() open it from a citation chip without Vue owning `open`. -->
  <details v-if="validSources.length" class="sources" @toggle="open = $event.target.open">
    <summary class="sources-summary">
      <span>{{ countLabel }}</span>
      <template v-if="publishers">
        <span aria-hidden="true">·</span>
        <span class="sources-publishers">{{ publishers }}</span>
      </template>
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
            v-for="(src, idx) in validSources"
            :id="src.index != null ? 'src-' + src.index : null"
            :key="idx"
            class="source-item"
            :data-srcid="src.index != null ? src.index : null"
          >
            <td class="col-index">
              <span v-if="src.index != null" class="source-index">{{ src.index }}</span>
            </td>
            <td class="col-source">
              <a
                :href="safeUrl(src.url)"
                target="_blank"
                rel="noopener noreferrer"
                class="source-link"
              >
                <span class="source-title-text">{{ src.title }}</span>
                <ExternalLink :size="12" class="source-external-icon" aria-hidden="true" />
              </a>
              <span v-if="metaLine(src)" class="source-meta">{{ metaLine(src) }}</span>
            </td>
            <td class="col-date">
              <time v-if="ledgerDate(src.date)" :datetime="ledgerDate(src.date)">{{
                ledgerDate(src.date)
              }}</time>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import { safeUrl } from '../utils/parseSSE.js'
import { isValidSource, summarizePublishers, ledgerDate } from '../utils/sources.js'

const props = defineProps({
  sources: {
    type: Array,
    default: () => [],
  },
})

// Mirrors the <details> element's state for the Show/Hide label only; the element
// itself stays the source of truth (a citation chip may open it directly).
const open = ref(false)

const validSources = computed(() => (props.sources || []).filter(isValidSource))
const countLabel = computed(() => {
  const n = validSources.value.length
  return `${n} ${n === 1 ? 'source' : 'sources'}`
})
const publishers = computed(() => summarizePublishers(validSources.value))

function metaLine(src) {
  return [src.source, src.country].filter(Boolean).join(' · ')
}
</script>

<style scoped>
.sources {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  font-size: var(--text-xs);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.sources-summary {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) 6px;
  cursor: pointer;
  list-style: none;
  border-radius: var(--radius-sm);
}

.sources-summary::-webkit-details-marker {
  display: none;
}

.sources-summary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.sources-publishers {
  overflow-wrap: anywhere;
}

.sources-toggle {
  color: var(--color-accent);
  font-weight: 600;
}

.sources-summary:hover .sources-toggle {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.sources[open] .sources-toggle {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.ledger {
  margin-top: var(--space-3);
  overflow-x: auto;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

.ledger-table th {
  text-align: left;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  padding: 6px var(--space-2);
  border-bottom: 1px solid var(--color-outline);
}

.ledger-table td {
  padding: 7px var(--space-2);
  border-bottom: 1px solid var(--color-border);
  vertical-align: top;
}

.ledger-table tr:last-child td {
  border-bottom: none;
}

.col-index {
  width: 1%;
}

.col-date {
  width: 1%;
  white-space: nowrap;
  font-family: var(--font-mono);
}

.col-source {
  min-width: 0;
}

/* Briefly pulse a row when its [n] citation chip is activated. */
.source-item {
  transition: background-color 0.3s;
}

.source-item.flash {
  background-color: var(--color-accent-soft);
}

/* Persistent marker for the last-activated source, so the [n] ↔ source link
   stays legible after the flash fades (until another citation is activated). */
.source-item.active .source-index {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

/* Row number: the same quiet chip as the inline [n] citations (style.css .cite). */
.source-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  transition:
    color 0.15s,
    border-color 0.15s;
}

.source-link {
  display: inline;
  text-decoration: none;
  color: var(--color-accent);
  font-weight: 600;
  font-size: var(--text-sm);
  overflow-wrap: anywhere;
}

.source-link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.source-external-icon {
  display: inline;
  margin-left: 3px;
  color: var(--color-text-secondary);
  opacity: 0.7;
  vertical-align: -1px;
}

.source-link:hover .source-external-icon {
  opacity: 1;
  color: var(--color-accent);
}

.source-meta {
  display: block;
  color: var(--color-text-secondary);
}
</style>
