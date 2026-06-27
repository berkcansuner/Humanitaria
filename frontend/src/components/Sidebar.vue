<template>
  <div :class="['sidebar', { open }]">
    <div class="sidebar-header">
      <button type="button" class="new-chat-btn" @click="$emit('new-chat')">
        <Plus :size="16" />
        New chat
      </button>
    </div>

    <div class="conv-search">
      <Search :size="15" />
      <input v-model="query" type="text" placeholder="Search conversations" />
    </div>

    <ConversationList
      :groups="groups"
      :active-id="activeId"
      :has-query="hasQuery"
      :loading="loading"
      @select="$emit('select', $event)"
      @rename="(id, title) => $emit('rename', id, title)"
      @delete="$emit('delete', $event)"
    />

    <div class="sidebar-foot">
      <div class="who">
        <div class="avatar">{{ initials }}</div>
        <div class="who-text">
          <div class="who-name">{{ displayName }}</div>
          <div v-if="secondary" class="who-org">{{ secondary }}</div>
        </div>
      </div>
      <router-link
        v-if="auth.user?.is_admin"
        to="/admin/ingestion"
        class="admin-link"
        title="Ingestion admin"
        aria-label="Ingestion admin"
      >
        <Shield :size="16" />
      </router-link>
      <button type="button" class="logout-btn" title="Log out" aria-label="Log out" @click="logout">
        <LogOut :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, LogOut, Shield } from 'lucide-vue-next'
import ConversationList from './ConversationList.vue'
import { filterConversations, groupConversationsByDate } from '../utils/conversationOps.js'
import { auth, doLogout } from '../utils/authStore.js'

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }, // initial conversation fetch in flight
})

defineEmits(['select', 'new-chat', 'rename', 'delete'])

const query = ref('')
const hasQuery = computed(() => query.value.trim().length > 0)
const groups = computed(() =>
  groupConversationsByDate(filterConversations(props.conversations, query.value))
)

// Footer reflects the signed-in user (from the auth store).
const displayName = computed(() => auth.user?.name || auth.user?.email || 'Account')
const secondary = computed(() => (auth.user?.name ? auth.user?.email : '') || '')
const initials = computed(() => {
  const n = auth.user?.name?.trim()
  if (n) {
    const p = n.split(/\s+/)
    return ((p[0]?.[0] || '') + (p[1]?.[0] || '')).toUpperCase() || n[0].toUpperCase()
  }
  const e = auth.user?.email
  return e ? e[0].toUpperCase() : '?'
})

const router = useRouter()
async function logout() {
  await doLogout()
  router.push('/')
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  height: 100%;
  background-color: var(--color-surface-container-low);
  border-right: 1px solid var(--color-border);
  padding: var(--space-3);
  gap: var(--space-3);
}

.sidebar-header {
  flex-shrink: 0;
}

.new-chat-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background-color: var(--color-accent);
}

.conv-search {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
}

.conv-search input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  outline: none;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.conv-search input::placeholder {
  color: var(--color-muted);
}

.sidebar-foot {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.who {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
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

.logout-btn {
  margin-left: auto;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.logout-btn:hover {
  background-color: var(--color-surface-container-high);
  color: var(--color-text);
}

.admin-link {
  margin-left: auto;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: background-color 0.2s, color 0.2s;
}

.admin-link:hover {
  background-color: var(--color-surface-container-high);
  color: var(--color-text);
}

/* When the admin link is present it owns the right-alignment; the logout button
   then sits beside it instead of grabbing its own margin-left:auto. */
.admin-link + .logout-btn {
  margin-left: var(--space-1);
}

/* ConversationList grows to fill the middle; the list itself scrolls. */
.sidebar :deep(.conv-list) {
  flex: 1;
}

@media (max-width: 640px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 30;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: var(--shadow-lg);
  }
  .sidebar.open {
    transform: translateX(0);
  }
}
</style>
