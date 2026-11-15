<template>
  <!-- One top bar for every signed-in screen: brand (back to chat), the Chat ↔
       Reports switch, and the account menu always in the same place. -->
  <header class="app-topbar">
    <slot name="start" />
    <router-link class="brand" to="/app" title="Humanitaria: back to chat">
      <HelpingHandLogo :size="28" :radius="8" />
      <div class="brand-text">
        <h1 class="brand-title">Humanitaria</h1>
        <span v-if="context" class="brand-sub">{{ context }}</span>
      </div>
    </router-link>
    <nav class="app-nav" aria-label="Main">
      <!-- router-link marks the exact match with aria-current="page". -->
      <router-link to="/app" class="app-nav-link">Chat</router-link>
      <router-link to="/reports" class="app-nav-link">Reports</router-link>
    </nav>
    <span class="app-topbar-spacer"></span>
    <UserMenu />
  </header>
</template>

<script setup>
import HelpingHandLogo from './HelpingHandLogo.vue'
import UserMenu from './UserMenu.vue'

defineProps({
  // Mono line under the brand naming the screen ("M&E Reports", "Settings").
  context: { type: String, default: '' },
})
</script>

<style scoped>
/* About Claude's 41px top bar: 6px vertical padding around 28px controls. */
.app-topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 6px var(--space-4);
  background-color: var(--color-bg);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
  border-radius: var(--radius-md);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  min-width: 0;
}

.brand-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  white-space: nowrap;
}

.brand-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: var(--space-4);
}

.app-nav-link {
  padding: 4px 10px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition:
    background-color 0.15s,
    color 0.15s;
}

.app-nav-link:hover {
  color: var(--color-text);
  background-color: var(--color-surface-container);
}

/* Same treatment as the active conversation row: Shelf Gray Deep, Field Green. */
.app-nav-link.router-link-exact-active {
  color: var(--color-accent);
  font-weight: 600;
  background-color: var(--color-surface-container-high);
}

.brand:focus-visible,
.app-nav-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.app-topbar-spacer {
  flex: 1;
}
/* The brand sits over the 288px sidebar: exactly the sidebar's width less the
   bar's 16px padding, on every screen. The subtitle fits inside it (longest:
   "Humanitarian Information Assistant"), and the Chat · Reports switch starts
   just past the sidebar edge, in the same place everywhere. */
@media (min-width: 641px) {
  .brand {
    width: 272px;
    min-width: 272px;
  }
}

@media (max-width: 640px) {
  .app-topbar {
    padding: 6px var(--space-3);
  }
  .brand-sub {
    display: none;
  }
  .app-nav {
    margin-left: var(--space-2);
  }
}

@media (max-width: 480px) {
  .brand-text {
    display: none;
  }
}
</style>
