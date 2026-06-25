<template>
  <div class="sources" v-if="validSources.length">
    <div class="sources-header">SOURCES ({{ validSources.length }})</div>
    <ul class="source-list">
      <li
        v-for="(src, idx) in validSources"
        :key="idx"
        class="source-item"
        :id="src.index != null ? 'src-' + src.index : null"
        :data-srcid="src.index != null ? src.index : null"
      >
        <span v-if="src.index != null" class="source-index">[{{ src.index }}]</span>
        <a :href="safeUrl(src.url)" target="_blank" rel="noopener noreferrer" class="source-link">
          <span class="source-title-text">{{ src.title }}</span>
          <ExternalLink :size="12" class="source-external-icon" />
        </a>
        <span class="source-meta">
          <template v-if="src.source"> · {{ src.source }}</template>
          <template v-if="src.date"> · {{ formatDate(src.date) }}</template>
        </span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import { safeUrl } from '../utils/parseSSE.js'
import { isValidSource } from '../utils/sources.js'

const props = defineProps({
  sources: {
    type: Array,
    default: () => []
  }
})

function formatDate(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

const validSources = computed(() => (props.sources || []).filter(isValidSource))
</script>

<style scoped>
.sources {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.sources-header {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
  margin-bottom: var(--space-2);
}

.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.source-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  font-size: var(--text-xs);
  line-height: 1.5;
  padding-left: var(--space-2);
  border-left: 2px solid transparent;
  border-radius: var(--radius-md);
  transition: background-color 0.3s, border-color 0.2s;
}

/* Briefly pulse a source's background when its [n] citation chip is activated. */
.source-item.flash {
  background-color: var(--color-accent-soft);
}

/* Persistent marker for the last-activated source, so the [n] ↔ source link
   stays legible after the flash fades (until another citation is activated). */
.source-item.active {
  border-left-color: var(--color-accent);
}

.source-index {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
}

.source-link {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  text-decoration: none;
  color: var(--color-accent);
  font-weight: 600;
}

.source-link:hover {
  text-decoration: underline;
}

.source-title-text {
  font-family: var(--font-body);
}

.source-external-icon {
  color: var(--color-muted);
  flex-shrink: 0;
  opacity: 0.6;
  transform: translateY(1px);
}

.source-link:hover .source-external-icon {
  opacity: 1;
  color: var(--color-accent);
}

.source-meta {
  color: var(--color-muted);
}
</style>
