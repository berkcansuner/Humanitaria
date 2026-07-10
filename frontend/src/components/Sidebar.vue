<template>
  <div :class="['sidebar', { open }]">
    <router-link to="/reports" class="reports-nav-link" title="M&amp;E Reports">
      <FileText :size="16" />
      M&amp;E Reports
    </router-link>

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
      <UserMenu variant="sidebar" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Plus, Search, FileText } from 'lucide-vue-next'
import ConversationList from './ConversationList.vue'
import UserMenu from './UserMenu.vue'
import { filterConversations, groupConversationsByDate } from '../utils/conversationOps.js'

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
  groupConversationsByDate(filterConversations(props.conversations, query.value)),
)
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

/* Prominent nav entry to the M&E Reports page, just under New chat. */
.reports-nav-link {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  transition:
    background-color 0.15s,
    color 0.15s,
    border-color 0.15s;
}

.reports-nav-link:hover {
  background-color: var(--color-surface-container);
  color: var(--color-text);
}

.reports-nav-link.router-link-active {
  color: var(--color-accent);
  border-color: var(--color-accent);
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
