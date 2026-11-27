<script setup>
// The hero's indicator card: three rows of the sample indicator monitoring report's
// Indicator Table, quoted verbatim, each value with its citation chip, and the
// sources those rows cite. A chip lights its source row, as in the chat card.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { sampleIndicators } from './samples.js'
import { citedParts } from './landingKit.js'
import { ledgerDate, revealSource } from '../utils/sources.js'

const { t, locale } = useI18n()

const sample = computed(() => {
  const s = sampleIndicators(locale.value, 'hero')
  return { ...s, rows: s.rows.map((r) => ({ ...r, parts: citedParts(r.value) })) }
})

const chipLabel = (n) => {
  const src = sample.value.sources.find((s) => s.n === n)
  return t('landing.chip', {
    n,
    title: src.title,
    publisher: src.publisher,
    date: ledgerDate(src.date, locale.value),
  })
}

function onCite(event) {
  const cite = event.target.closest('.cite')
  if (cite) revealSource(event.currentTarget, cite.dataset.cite, cite, { block: 'nearest' })
}
</script>

<template>
  <figure class="ic" :aria-label="t('landing.indicators.panel')" @click="onCite">
    <p class="ic-title">
      {{ t('landing.indicators.head', { country: t('landing.country') }) }}
    </p>
    <dl class="ic-rows">
      <div v-for="row in sample.rows" :key="row.indicator" class="ic-row">
        <dt class="ic-label">{{ row.indicator }}</dt>
        <dd class="ic-value">
          <template v-for="(part, i) in row.parts" :key="i"
            ><button
              v-if="part.cite"
              class="cite"
              type="button"
              :data-cite="part.cite"
              :aria-label="chipLabel(part.cite)"
            >
              {{ part.cite }}</button
            ><template v-else>{{ part.text }}</template></template
          >
        </dd>
      </div>
    </dl>
    <ol class="ic-sources" :aria-label="t('landing.answer.sources')">
      <li v-for="src in sample.sources" :key="src.n" class="source-item" :data-srcid="src.n">
        <span class="ic-src-n">{{ src.n }}</span>
        <a
          class="source-link"
          :href="src.url"
          target="_blank"
          rel="noopener noreferrer"
          :title="src.title"
          ><span class="ic-src-pub">{{ src.publisher }}</span> {{ src.title }}</a
        >
        <time class="ic-src-date" :datetime="src.date">{{ ledgerDate(src.date, locale) }}</time>
      </li>
    </ol>
  </figure>
</template>

<style scoped>
.ic {
  margin: 0;
  padding: 16px 18px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow:
    0 1px 2px rgb(11 29 46 / 0.06),
    0 18px 40px -18px rgb(11 29 46 / 0.32);
}
.ic-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.ic-rows {
  margin: 6px 0 0;
}
.ic-row {
  padding: 7px 0;
  border-top: 1px solid var(--color-border);
}
.ic-row:first-child {
  border-top: 0;
}
.ic-label {
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  text-wrap: pretty;
}
.ic-value {
  margin: 2px 0 0;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.4;
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
  color: var(--color-text);
}
.ic-value .cite {
  margin-left: 4px;
}

/* Citation chips mirror the app: quiet outlines that fill on hover/focus. */
.cite {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  vertical-align: 2px;
  cursor: pointer;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.cite:hover,
.cite:focus-visible {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
  outline: none;
}

.ic-sources {
  margin: 4px 0 0;
  padding: 8px 0 0;
  list-style: none;
  border-top: 1px solid var(--color-border);
}
.source-item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 2px 6px;
  margin: 0 -6px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  transition: background-color 0.25s;
}
.source-item.active {
  background: var(--color-accent-soft);
  color: var(--color-text);
}
.ic-src-n {
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.source-item.active .ic-src-n {
  color: var(--color-accent);
}
.source-link {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  border-radius: 4px;
}
.source-link:hover {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.ic-src-pub {
  font-weight: 600;
  color: var(--color-text);
}
.ic-src-date {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1023px) {
  /* Touch-sized source rows (24px link targets). */
  .source-link {
    line-height: 24px;
  }
}
</style>
