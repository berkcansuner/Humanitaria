<template>
  <div ref="rootEl" class="user-menu" :class="{ 'user-menu-sidebar': isSidebar }">
    <button
      v-if="isSidebar"
      type="button"
      class="who-btn"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="menu"
      aria-label="Account menu"
      @click="open = !open"
    >
      <span class="avatar">{{ initials }}</span>
      <span class="who-text">
        <span class="who-name">{{ displayName }}</span>
        <span v-if="secondary" class="who-org">{{ secondary }}</span>
      </span>
    </button>
    <button
      v-else
      type="button"
      class="avatar-btn"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="menu"
      aria-label="Account menu"
      @click="open = !open"
    >
      {{ initials }}
    </button>
    <div v-if="open" class="menu" :class="{ 'menu-up': isSidebar }" role="menu">
      <div class="menu-head">
        <div class="menu-name">{{ auth.user?.name || 'Account' }}</div>
        <div class="menu-email">{{ auth.user?.email }}</div>
      </div>
      <router-link class="menu-item" role="menuitem" to="/settings" @click="open = false">
        <Settings :size="15" /> Settings
      </router-link>
      <router-link
        v-if="auth.user?.is_admin"
        class="menu-item"
        role="menuitem"
        to="/admin/ingestion"
        @click="open = false"
      >
        <Shield :size="15" /> Admin panel
      </router-link>
      <button type="button" class="menu-item" role="menuitem" @click="logout">
        <LogOut :size="15" /> Log out
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Settings, Shield, LogOut } from 'lucide-vue-next'
import { auth, doLogout } from '../utils/authStore.js'
import { userInitials } from '../utils/userDisplay.js'

const props = defineProps({
  // 'header' renders the compact avatar circle (menu drops down, right-aligned);
  // 'sidebar' renders the full who-block trigger (menu opens upward, full width).
  variant: { type: String, default: 'header' },
})

const isSidebar = computed(() => props.variant === 'sidebar')

const open = ref(false)
const rootEl = ref(null)
const initials = computed(() => userInitials(auth.user))
const displayName = computed(() => auth.user?.name || auth.user?.email || 'Account')
const secondary = computed(() => (auth.user?.name ? auth.user?.email : '') || '')

const router = useRouter()
async function logout() {
  open.value = false
  await doLogout()
  router.push('/')
}

function onDocClick(e) {
  if (open.value && rootEl.value && !rootEl.value.contains(e.target)) open.value = false
}
function onKeydown(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.user-menu {
  position: relative;
}

.user-menu-sidebar {
  width: 100%;
}

.avatar-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background-color: var(--color-surface-container-high);
  color: var(--color-text-secondary);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background-color 0.2s,
    color 0.2s,
    border-color 0.2s;
}

.avatar-btn:hover {
  color: var(--color-accent);
  border-color: var(--color-outline);
}

/* Sidebar-footer trigger: mirrors the old .who block's look. */
.who-btn {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  width: 100%;
  padding: var(--space-1);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: background-color 0.2s;
}

.who-btn:hover {
  background-color: var(--color-surface-container-high);
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  background-color: var(--color-surface-container-high);
  color: var(--color-text-secondary);
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
}

.who-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.who-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.who-org {
  font-size: 11px;
  color: var(--color-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 200px;
  padding: var(--space-1);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 40;
}

/* Sidebar variant: open upward, span the footer width. */
.menu-up {
  top: auto;
  bottom: calc(100% + 6px);
  left: 0;
  right: 0;
  min-width: 0;
}

.menu-head {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-1);
}

.menu-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-email {
  font-size: 11.5px;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  text-align: left;
  text-decoration: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s;
}

.menu-item:hover {
  background-color: var(--color-surface-container);
  color: var(--color-text);
}
</style>
