<template>
  <div class="sources" v-if="validSources.length">
    <div class="sources-header">Sources</div>
    <div class="source-list">
      <a v-for="(src, idx) in validSources" :key="idx"
         :href="safeUrl(src.url)" target="_blank" rel="noopener noreferrer" class="source-item">
        <div class="source-title-row">
          <div class="source-icon-wrapper" aria-hidden="true">
            <FileText :size="16" />
          </div>
          <span class="source-title-text">{{ src.title }}</span>
          <ExternalLink :size="14" class="source-external-icon" />
        </div>
        <div class="source-meta">
          <span v-if="src.country">{{ src.country }}</span>
          <span v-if="src.date">{{ formatDate(src.date) }}</span>
          <span v-if="src.source">{{ src.source }}</span>
        </div>
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ExternalLink, FileText } from 'lucide-vue-next'

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

function safeUrl(url) {
  // Only allow http(s) URLs to prevent javascript: or data: XSS vectors
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? url : '#'
  } catch {
    return '#'
  }
}

function isValidSource(src) {
  if (!src || !src.url) return false
  if (src.doctype === 'country' && src.title === src.country) return false
  return true
}

const validSources = computed(() => (props.sources || []).filter(isValidSource))
</script>

<style scoped>
.sources {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.sources-header {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-accent);
  margin-bottom: var(--space-3);
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.source-item {
  display: block;
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-accent);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s, transform 0.15s, border-color 0.2s;
  text-decoration: none;
}

.source-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
  border-color: var(--color-accent);
}

.source-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.source-icon-wrapper {
  color: var(--color-accent);
  flex-shrink: 0;
}

.source-title-text {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-accent);
  line-height: 1.4;
  flex: 1;
}

.source-external-icon {
  color: var(--color-muted);
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.source-item:hover .source-external-icon {
  opacity: 1;
  color: var(--color-accent);
}

.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin-top: var(--space-2);
  margin-left: calc(16px + var(--space-2));
  font-size: var(--text-xs);
  color: var(--color-muted);
}

.source-meta span {
  position: relative;
}

.source-meta span:not(:last-child)::after {
  content: '\2022';
  position: absolute;
  right: -0.55rem;
  color: var(--color-border);
}
</style>
