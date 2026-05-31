<template>
  <div :class="['sidebar', { open }]">
    <div class="sidebar-header">
      <button type="button" class="new-chat-btn" @click="$emit('new-chat')">
        <Plus :size="16" />
        Yeni sohbet
      </button>
    </div>

    <ConversationList
      :conversations="conversations"
      :active-id="activeId"
      @select="$emit('select', $event)"
      @rename="(id, title) => $emit('rename', id, title)"
      @delete="$emit('delete', $event)"
    />

    <div class="sidebar-footer">
      <ThemeToggle />
    </div>
  </div>
</template>

<script setup>
import { Plus } from 'lucide-vue-next'
import ConversationList from './ConversationList.vue'
import ThemeToggle from './ThemeToggle.vue'

defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  open: { type: Boolean, default: false },
})

defineEmits(['select', 'new-chat', 'rename', 'delete'])
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

.sidebar-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
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
