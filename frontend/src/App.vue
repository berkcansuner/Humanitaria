<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :active-id="activeId"
      :open="sidebarOpen"
      @select="selectConversation"
      @new-chat="newChat"
      @rename="onRename"
      @delete="onDelete"
    />
    <div v-if="sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false"></div>

    <div class="main">
      <header class="topbar">
        <button class="hamburger" aria-label="Menüyü aç/kapat" @click="sidebarOpen = !sidebarOpen">
          <Menu :size="20" />
        </button>
        <h1 class="topbar-title">ReliefWeb RAG</h1>
      </header>
      <main class="content">
        <Chat :conversation-id="activeId" @session="onSession" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Menu } from 'lucide-vue-next'
import Chat from './components/Chat.vue'
import Sidebar from './components/Sidebar.vue'
import {
  listConversations,
  renameConversation,
  deleteConversation,
} from './utils/api.js'

const conversations = ref([])
const activeId = ref(null)
const sidebarOpen = ref(false)

async function loadConversations() {
  try {
    conversations.value = await listConversations()
  } catch (e) {
    console.error('Failed to load conversations:', e)
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
  }
}

async function onDelete(id) {
  try {
    await deleteConversation(id)
    if (activeId.value === id) activeId.value = null
    await loadConversations()
  } catch (e) {
    console.error('Delete failed:', e)
  }
}

onMounted(loadConversations)
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

.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-bg);
  flex-shrink: 0;
}

.topbar-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-accent);
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
  max-width: var(--content-max-width);
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
