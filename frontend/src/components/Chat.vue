<template>
  <div class="chat">
    <div class="messages" ref="messagesContainer">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-bubble">
          <div class="message-content" v-html="formatContent(msg.content)"></div>
          <SourceList v-if="msg.sources" :sources="msg.sources" />
        </div>
      </div>
      <div v-if="loading" class="message assistant loading">
        <div class="message-bubble">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
    <form class="input-area" @submit.prevent="sendMessage">
      <input
        v-model="input"
        type="text"
        placeholder="Soru sorun... (örn: İran'da gıda durumu)"
        class="chat-input"
        :disabled="loading"
      />
      <button type="submit" class="send-btn" :disabled="loading || !input.trim()">
        Gönder
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SourceList from './SourceList.vue'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

function formatContent(text) {
  return text.replace(/\n/g, '<br>')
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
      })
    })
    if (!res.ok) throw new Error('API hatası')
    const data = await res.json()
    messages.value.push({ role: 'assistant', content: data.answer, sources: data.sources })
  } catch (err) {
    messages.value.push({ role: 'assistant', content: 'Bir hata oluştu: ' + err.message })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  setTimeout(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }, 50)
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 1rem 1.25rem;
  border-radius: 2px;
}

.message.user .message-bubble {
  background-color: var(--color-text);
  color: var(--color-bg);
}

.message.assistant .message-bubble {
  background-color: #fff;
  border: 1px solid var(--color-border);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.message-content {
  font-size: 1.05rem;
  line-height: 1.7;
}

.typing-indicator {
  display: flex;
  gap: 0.4rem;
  padding: 0.5rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: var(--color-muted);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
  display: flex;
  gap: 0.75rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.chat-input {
  flex: 1;
  padding: 0.875rem 1rem;
  font-family: var(--font-body);
  font-size: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 2px;
  background-color: #fff;
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: var(--color-accent);
}

.chat-input::placeholder {
  color: #aaa;
  font-style: italic;
}

.send-btn {
  padding: 0.875rem 1.5rem;
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 600;
  background-color: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: 2px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.send-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
