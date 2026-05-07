<template>
  <div class="chat">
    <div class="messages" ref="messagesContainer">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-bubble">
          <div class="message-content" v-text="msg.content"></div>
          <SourceList v-if="msg.sources" :sources="msg.sources" />
        </div>
      </div>
      <div v-if="loading && !streaming" class="message assistant loading">
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
const streaming = ref(false)
const sessionId = ref(null)
const messagesContainer = ref(null)

function parseSSE(chunk) {
  let event = null
  let data = null
  for (const line of chunk.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      data = line.slice(5).trim()
    }
  }
  if (data !== null) {
    return { event: event || 'message', data }
  }
  return null
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  streaming.value = false

  const assistantMsg = { role: 'assistant', content: '', sources: null }
  messages.value.push(assistantMsg)
  const msgIndex = messages.value.length - 1
  scrollToBottom()

  try {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content })),
        session_id: sessionId.value,
      })
    })
    if (!res.ok) throw new Error('API hatası')

    streaming.value = true
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split(/\r?\n\r?\n/)
      buffer = parts.pop()

      for (const part of parts) {
        if (!part.trim()) continue
        const sse = parseSSE(part)
        if (!sse) continue

        if (sse.event === 'token') {
          const data = JSON.parse(sse.data)
          assistantMsg.content += data.content
          messages.value[msgIndex] = { ...assistantMsg }
          scrollToBottom()
        } else if (sse.event === 'sources') {
          const data = JSON.parse(sse.data)
          assistantMsg.sources = data.sources
          messages.value[msgIndex] = { ...assistantMsg }
        } else if (sse.event === 'session') {
          const data = JSON.parse(sse.data)
          sessionId.value = data.session_id
        } else if (sse.event === 'error') {
          const data = JSON.parse(sse.data)
          assistantMsg.content += '\n\n[Hata: ' + data.message + ']'
          messages.value[msgIndex] = { ...assistantMsg }
        }
      }
    }
  } catch (err) {
    if (!assistantMsg.content) {
      assistantMsg.content = 'Bir hata oluştu: ' + err.message
    } else {
      assistantMsg.content += '\n\n[Bağlantı kesildi]'
    }
    messages.value[msgIndex] = { ...assistantMsg }
  } finally {
    loading.value = false
    streaming.value = false
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
  white-space: pre-wrap;
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