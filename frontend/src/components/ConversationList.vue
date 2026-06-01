<template>
  <ul class="conv-list">
    <template v-if="groups.length">
      <template v-for="group in groups" :key="group.key">
        <li class="conv-section-label">{{ group.label }}</li>
        <li
          v-for="c in group.items"
          :key="c.id"
          :class="['conv-item', { active: c.id === activeId }]"
        >
          <template v-if="editingId === c.id">
            <input
              ref="editInput"
              v-model="editTitle"
              class="conv-edit-input"
              @keyup.enter="commitRename(c.id)"
              @keyup.esc="cancelRename"
              @blur="commitRename(c.id)"
            />
          </template>
          <template v-else>
            <button type="button" class="conv-select" :title="c.title" @click="$emit('select', c.id)">
              {{ c.title }}
            </button>
            <div class="conv-actions">
              <button type="button" class="conv-action" aria-label="Rename" @click.stop="startRename(c)">
                <Pencil :size="13" />
              </button>
              <button type="button" class="conv-action" aria-label="Delete" @click.stop="$emit('delete', c.id)">
                <Trash2 :size="13" />
              </button>
            </div>
          </template>
        </li>
      </template>
    </template>
    <li v-else-if="hasQuery" class="conv-section-label conv-empty">No results</li>
  </ul>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { Pencil, Trash2 } from 'lucide-vue-next'

defineProps({
  // [{ key, label, items: [{ id, title, ... }] }] — pre-filtered & grouped by the Sidebar.
  groups: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  hasQuery: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'rename', 'delete'])

const editingId = ref(null)
const editTitle = ref('')
const editInput = ref(null)

function startRename(c) {
  editingId.value = c.id
  editTitle.value = c.title
  nextTick(() => {
    const el = Array.isArray(editInput.value) ? editInput.value[0] : editInput.value
    el?.focus()
    el?.select()
  })
}

function commitRename(id) {
  if (editingId.value !== id) return
  const title = editTitle.value.trim()
  editingId.value = null
  if (title) emit('rename', id, title)
}

function cancelRename() {
  editingId.value = null
}
</script>

<style scoped>
.conv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.conv-section-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
  padding: var(--space-2) var(--space-2) var(--space-1);
}

.conv-empty {
  opacity: 0.7;
  text-transform: none;
  letter-spacing: 0;
}

.conv-item {
  display: flex;
  align-items: center;
  border-radius: var(--radius-md);
  transition: background-color 0.15s;
}

.conv-item:hover {
  background-color: var(--color-surface-container);
}

.conv-item.active {
  background-color: var(--color-surface-container-high);
}

.conv-select {
  flex: 1;
  min-width: 0;
  text-align: left;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-item.active .conv-select {
  color: var(--color-accent);
  font-weight: 600;
}

.conv-actions {
  display: flex;
  gap: 2px;
  padding-right: var(--space-2);
  opacity: 0;
  transition: opacity 0.15s;
}

.conv-item:hover .conv-actions,
.conv-item.active .conv-actions {
  opacity: 1;
}

.conv-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
}

.conv-action:hover {
  color: var(--color-accent);
  background-color: var(--color-surface);
}

.conv-edit-input {
  flex: 1;
  min-width: 0;
  margin: 2px var(--space-2);
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-sm);
  outline: none;
}
</style>
