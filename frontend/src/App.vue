<template>
  <div class="app">
    <header class="masthead">
      <div class="masthead-inner">
        <h1 class="masthead-title">ReliefWeb RAG</h1>
        <p class="masthead-subtitle">Intelligent assistant on humanitarian aid documents</p>
      </div>
      <div class="masthead-actions">
        <ThemeToggle />
      </div>
    </header>
    <main class="content">
      <Chat />
    </main>
  </div>
</template>

<script setup>
import Chat from './components/Chat.vue'
import ThemeToggle from './components/ThemeToggle.vue'
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.masthead {
  position: relative;
  background: linear-gradient(180deg, var(--color-surface-container) 0%, var(--color-bg) 100%);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.masthead-actions {
  position: absolute;
  top: var(--space-4);
  right: var(--space-5);
}

@media (max-width: 640px) {
  .masthead-actions {
    top: var(--space-3);
    right: var(--space-4);
  }
}

.masthead-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--space-5) var(--space-5) var(--space-3);
  text-align: center;
}

.masthead-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-accent);
  margin-bottom: var(--space-1);
  line-height: 1.2;
}

.masthead-subtitle {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-muted);
  font-style: italic;
  opacity: 0.9;
}

.content {
  flex: 1;
  max-width: var(--content-max-width);
  width: 100%;
  margin: 0 auto;
  padding: var(--space-4) var(--space-5);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 640px) {
  .masthead-inner {
    padding: var(--space-5) var(--space-4) var(--space-4);
  }
  .masthead-title {
    font-size: var(--text-2xl);
  }
  .masthead-subtitle {
    font-size: var(--text-base);
  }
  .content {
    padding: var(--space-3) var(--space-4);
  }
}
</style>
