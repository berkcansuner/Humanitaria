<template>
  <div class="app">
    <header class="masthead">
      <h1 class="masthead-title">ReliefWeb RAG</h1>
      <p class="masthead-subtitle">İnsani yardım belgeleri üzerine akıllı asistan</p>
    </header>
    <main class="content">
      <Chat />
    </main>
  </div>
</template>

<script setup>
import Chat from './components/Chat.vue'
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.masthead {
  text-align: center;
  padding: 3rem 1rem 2rem;
  border-bottom: 1px solid var(--color-border);
}

.masthead-title {
  font-family: var(--font-display);
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: 0.5rem;
}

.masthead-subtitle {
  font-family: var(--font-body);
  font-size: 1.1rem;
  color: var(--color-muted);
  font-style: italic;
}

.content {
  flex: 1;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1rem;
}
</style>
