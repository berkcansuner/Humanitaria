<template>
  <div class="app">
    <Sidebar
      :conversations="visibleConversations"
      :active-id="activeId"
      :open="sidebarOpen"
      :loading="isLoadingConversations"
      @select="selectConversation"
      @new-chat="newChat"
      @rename="onRename"
      @delete="onDelete"
    />
    <div v-if="sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false"></div>

    <div class="main">
      <header class="topbar">
        <button class="hamburger" aria-label="Toggle menu" @click="sidebarOpen = !sidebarOpen">
          <Menu :size="20" />
        </button>
        <router-link class="brand" to="/" title="Back to home">
          <HelpingHandLogo :size="34" :radius="11" />
          <div class="brand-text">
            <h1 class="brand-title">Humanitaria</h1>
            <span class="brand-sub">Humanitarian Information Assistant</span>
          </div>
        </router-link>
        <div class="topbar-spacer"></div>
      </header>
      <div v-if="actionError" class="action-error" role="alert">
        <span>{{ actionError }}</span>
        <button class="action-error-dismiss" aria-label="Dismiss" @click="actionError = null">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>
      <main class="content">
        <Chat :conversation-id="activeId" @session="onSession" />
      </main>
    </div>
    <UndoToast
      :message="pendingDelete ? 'Conversation deleted.' : ''"
      action-label="Undo"
      focus-action
      :focus-key="pendingDelete ? pendingDelete.id : null"
      @action="undoDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import Chat from '../components/Chat.vue'
import Sidebar from '../components/Sidebar.vue'
import HelpingHandLogo from '../components/HelpingHandLogo.vue'
import UndoToast from '../components/UndoToast.vue'
import { listConversations, renameConversation, deleteConversation } from '../utils/api.js'
import { useUndoableDelete } from '../utils/undoableDelete.js'

const conversations = ref([])
const activeId = ref(null)
const sidebarOpen = ref(false)
const actionError = ref(null)
const isLoadingConversations = ref(false)
let errorTimer = null

// Surface a transient, dismissible error for sidebar actions that previously
// failed silently (the old behaviour only logged to the console).
function showActionError(message) {
  actionError.value = message
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    actionError.value = null
  }, 5000)
}

async function loadConversations() {
  isLoadingConversations.value = true
  try {
    conversations.value = await listConversations()
  } catch (e) {
    console.error('Failed to load conversations:', e)
    showActionError('Could not load your conversations. Please try again.')
  } finally {
    isLoadingConversations.value = false
  }
}

function selectConversation(id) {
  activeId.value = id
  sidebarOpen.value = false
}

function newChat() {
  activeId.value = null
  sidebarOpen.value = false
}

// Chat reports the server-assigned session id (covers a freshly created
// conversation); reflect it as active and refresh the list so it appears.
function onSession(id) {
  activeId.value = id
  loadConversations()
}

async function onRename(id, title) {
  try {
    await renameConversation(id, title)
    await loadConversations()
  } catch (e) {
    console.error('Rename failed:', e)
    showActionError('Could not rename the conversation.')
  }
}

// Delete hides the conversation at once and offers Undo for 8 s before the
// DELETE is sent (see useUndoableDelete).
const {
  hiddenIds,
  pending: pendingDelete,
  remove: removeConversation,
  undo: undoDelete,
  flush: flushDelete,
} = useUndoableDelete({
  commit: deleteConversation,
  onCommitted: loadConversations,
  onError: (e) => {
    console.error('Delete failed:', e)
    showActionError('Could not delete the conversation. It is back in the list.')
  },
  // Reopen it if it was the open conversation.
  onUndo: (id, meta) => {
    if (meta && meta.wasActive) activeId.value = id
  },
})

const visibleConversations = computed(() =>
  conversations.value.filter((c) => !hiddenIds.value.has(c.id)),
)

function onDelete(id) {
  const wasActive = activeId.value === id
  if (wasActive) activeId.value = null
  removeConversation(id, { wasActive })
}

onMounted(loadConversations)
onBeforeUnmount(flushDelete)
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.action-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin: var(--space-3) var(--space-5) 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  background-color: var(--color-error-bg);
  color: var(--color-error-accent);
  font-size: var(--text-sm);
}

.action-error-dismiss {
  flex-shrink: 0;
  display: inline-flex;
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  background-color: var(--color-bg);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  min-width: 0;
}

.brand-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  white-space: nowrap;
}

.brand-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-muted);
  white-space: nowrap;
}

.topbar-spacer {
  flex: 1;
}

.hamburger {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.content {
  flex: 1;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-5);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 640px) {
  .hamburger {
    display: inline-flex;
  }
  .brand-sub {
    display: none;
  }
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 20;
    background-color: rgba(0, 0, 0, 0.4);
  }
  .content {
    padding: var(--space-3) var(--space-4);
  }
}
</style>
