<template>
  <div :class="['sidebar', { open }]">
    <div class="sidebar-header">
      <button type="button" class="new-chat-btn" @click="$emit('new-chat')">
        <Plus :size="16" />
        {{ t('chat.newChat') }}
      </button>
    </div>

    <div class="conv-search">
      <Search :size="15" />
      <input v-model="query" type="text" :placeholder="t('chat.search')" />
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Search } from 'lucide-vue-next'
import ConversationList from './ConversationList.vue'
import { filterConversations, groupConversationsByDate } from '../utils/conversationOps.js'

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }, // initial conversation fetch in flight
})

defineEmits(['select', 'new-chat', 'rename', 'delete'])

const { t } = useI18n()

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
  /* 288px of Cloud Ground beside the white content, 12px padding, 32px rows. */
  width: 288px;
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
  min-height: 38px;
  padding: 0 var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  line-height: 21px;
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background-color: color-mix(in srgb, var(--color-accent-container) 86%, #000);
}

/* Prominent nav entry to the M&E Reports page, just under New chat. */
.conv-search {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 36px;
  padding: 0 12px;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

/* The field takes the ring; the borderless input inside draws none of its own. */
.conv-search:focus-within {
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}
.conv-search input:focus-visible {
  box-shadow: none;
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
