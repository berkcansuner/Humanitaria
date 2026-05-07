<template>
  <div class="sources" v-if="sources && sources.length">
    <div class="sources-header">Kaynaklar</div>
    <div class="source-list">
      <div v-for="(src, idx) in sources" :key="idx" class="source-item">
        <a :href="src.url" target="_blank" rel="noopener" class="source-title">{{ src.title }}</a>
        <div class="source-meta">
          <span v-if="src.country">{{ src.country }}</span>
          <span v-if="src.date">{{ src.date }}</span>
          <span v-if="src.source">{{ src.source }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  sources: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.sources {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.sources-header {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted);
  margin-bottom: 0.75rem;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.source-item {
  padding: 0.5rem 0;
}

.source-title {
  font-family: var(--font-body);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
  line-height: 1.4;
}

.source-title:hover {
  text-decoration: underline;
}

.source-meta {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--color-muted);
}

.source-meta span {
  position: relative;
}

.source-meta span:not(:last-child)::after {
  content: '·';
  position: absolute;
  right: -0.5rem;
  color: var(--color-border);
}
</style>
