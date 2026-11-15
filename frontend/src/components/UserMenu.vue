<template>
  <div ref="rootEl" class="user-menu">
    <button
      type="button"
      class="avatar-btn"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="menu"
      aria-label="Account menu"
      @click="open = !open"
    >
      {{ initials }}
    </button>
    <div v-if="open" class="menu" role="menu">
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

const open = ref(false)
const rootEl = ref(null)
const initials = computed(() => userInitials(auth.user))

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
