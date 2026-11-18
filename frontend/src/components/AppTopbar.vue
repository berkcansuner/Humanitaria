<template>
  <!-- One top bar for every signed-in screen: brand (back to chat), the Chat ↔
       Reports switch, a link to the home page, and the account menu always in the
       same place. -->
  <header class="app-topbar">
    <slot name="start" />
    <router-link class="brand" to="/app" :title="t('chat.topbar.home')">
      <HelpingHandLogo :size="28" :radius="8" />
      <div class="brand-text">
        <h1 class="brand-title">Humanitaria</h1>
        <span v-if="context" class="brand-sub">{{ context }}</span>
      </div>
    </router-link>
    <nav class="app-nav" :aria-label="t('chat.topbar.nav')">
      <!-- router-link marks the exact match with aria-current="page". -->
      <router-link to="/app" class="app-nav-link">{{ t('nav.chat') }}</router-link>
      <router-link to="/reports" class="app-nav-link">{{ t('nav.reports') }}</router-link>
    </nav>
    <span class="app-topbar-spacer"></span>
    <!-- The landing page, one click from every screen: a quiet utility beside the
         language and account controls, not a third tab. On phones the house alone
         shows; the label stays as the link's name (and tooltip). -->
    <router-link to="/" class="home-link" :title="t('chat.topbar.homePage')">
      <House :size="16" aria-hidden="true" />
      <span class="home-label">{{ t('chat.topbar.homePage') }}</span>
    </router-link>
    <LanguageSwitcher variant="app" />
    <UserMenu />
  </header>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { House } from 'lucide-vue-next'
import HelpingHandLogo from './HelpingHandLogo.vue'
import UserMenu from './UserMenu.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'

defineProps({
  // Small line under the brand naming the screen ("M&E Reports", "Settings").
  context: { type: String, default: '' },
})

const { t } = useI18n()
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
  font-family: var(--font-body);
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

/* Home page: the language button's quiet 28px shape (icon, then label) in muted
   text, so it reads as a utility, not a fourth destination beside the tabs. An
   invisible pad brings the hit area to 44px. */
.home-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 8px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  white-space: nowrap;
  border-radius: var(--radius-md);
  transition:
    background-color 0.15s,
    color 0.15s;
}
.home-link::after {
  content: '';
  position: absolute;
  inset: -8px -4px;
}
.home-link:hover {
  color: var(--color-text);
  background-color: var(--color-surface-container);
}

.brand:focus-visible,
.app-nav-link:focus-visible,
.home-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.app-topbar-spacer {
  flex: 1;
}
/* The brand sits over the 288px sidebar: exactly the sidebar's width less the
   bar's 16px padding, on every screen. The subtitle fits inside it (longest:
   "M&E Reports"), and the Chat · Reports switch starts
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

@media (max-width: 640px) {
  /* The house alone; the label stays in the page as the link's name. */
  .home-label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  .home-link {
    padding: 0 6px;
  }
}

@media (max-width: 480px) {
  .brand-text {
    display: none;
  }
  /* Room for the house at 390px (Turkish tabs are the widest): the bar's gaps and
     side padding step down one notch, the tabs keep their 28px height. */
  .app-topbar {
    gap: var(--space-2);
    padding: 6px var(--space-2);
  }
  .app-nav {
    margin-left: 0;
  }
  .app-nav-link {
    padding: 4px 8px;
  }
}
</style>
