<template>
  <div class="chat">
    <div class="messages" ref="messagesContainer" role="log" aria-live="polite">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-row">
          <!-- Assistant avatar -->
          <div v-if="msg.role === 'assistant'" class="assistant-avatar" aria-hidden="true">
            <Bot :size="20" />
          </div>
          <div class="message-bubble">
            <template v-if="msg.role === 'assistant' && !msg.content && !msg.error && !msg.clarification">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </template>
            <template v-else>
              <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
              <div v-if="msg.error" class="error-banner">
                <AlertCircle :size="16" class="error-icon" />
                {{ msg.error }}
              </div>
              <div v-if="msg.clarification && !msg.clarification.resolved" class="clarification-card">
                <p class="clarification-message">{{ msg.clarification.message }}</p>
                <div class="suggestion-groups">
                  <div v-if="msg.clarification.suggestions.countries.length" class="suggestion-group">
                    <span class="suggestion-label">Country:</span>
                    <button v-for="c in msg.clarification.suggestions.countries" :key="c"
                            @click="applySuggestion(msg, 'country', c)" class="suggestion-chip">{{ c }}</button>
                  </div>
                  <div v-if="msg.clarification.suggestions.time_periods.length" class="suggestion-group">
                    <span class="suggestion-label">Time:</span>
                    <button v-for="t in msg.clarification.suggestions.time_periods" :key="t"
                            @click="applySuggestion(msg, 'date', t)" class="suggestion-chip">{{ t }}</button>
                  </div>
                  <div v-if="msg.clarification.suggestions.themes.length" class="suggestion-group">
                    <span class="suggestion-label">Topic:</span>
                    <button v-for="th in msg.clarification.suggestions.themes" :key="th"
                            @click="applySuggestion(msg, 'theme', th)" class="suggestion-chip">{{ th }}</button>
                  </div>
                </div>
              </div>
              <SourceList v-if="msg.sources" :sources="msg.sources" />
            </template>
          </div>
        </div>
      </div>
    </div>
    <form class="input-area" @submit.prevent="sendMessage">
      <input
        v-model="input"
        type="text"
        placeholder="Ask about humanitarian aid..."
        class="chat-input"
        :disabled="loading"
        enterkeyhint="send"
      />
      <button type="submit" class="send-btn" :disabled="loading || !input.trim()" aria-label="Send message">
        <Loader2 v-if="loading" :size="20" class="spin" />
        <Send v-else :size="20" />
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Send, Loader2, Bot, AlertCircle } from 'lucide-vue-next'
import SourceList from './SourceList.vue'
import { renderMarkdown } from '../utils/renderMarkdown.js'

const ERROR_MESSAGES = {
  connection: 'Connection lost. Please try again.',
  stream_interrupted: 'Response interrupted. Some content may be missing.',
  empty_response: 'No response received. Please try again.',
  sse_parse: 'Something went wrong. Please try again.',
}

const messages = ref([])
const input = ref('')
const loading = ref(false)
const sessionId = ref(null)
const messagesContainer = ref(null)

function parseSSE(chunk) {
  let event = null
  const dataLines = []
  for (const line of chunk.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      // Accumulate all data: lines — multi-line data fields are joined with \n per SSE spec
      dataLines.push(line.slice(5).trim())
    }
  }
  if (dataLines.length > 0) {
    return { event: event || 'message', data: dataLines.join('\n') }
  }
  return null
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, error: null })
  input.value = ''
  loading.value = true

  const assistantMsg = { role: 'assistant', content: '', sources: null, error: null, clarification: null }
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
    if (!res.ok) {
      console.error(`API error: ${res.status} ${res.statusText} — POST /chat/stream`)
      assistantMsg.error = ERROR_MESSAGES.connection
      messages.value[msgIndex] = { ...assistantMsg }
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      assistantMsg.error = ERROR_MESSAGES.connection
      messages.value[msgIndex] = { ...assistantMsg }
      return
    }
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
          try {
            const data = JSON.parse(sse.data)
            assistantMsg.content += data.content
            messages.value[msgIndex] = { ...assistantMsg }
            scrollToBottom()
          } catch (e) {
            console.error('SSE token parse error:', e, sse.data)
          }
        } else if (sse.event === 'sources') {
          try {
            const data = JSON.parse(sse.data)
            assistantMsg.sources = data.sources
            messages.value[msgIndex] = { ...assistantMsg }
          } catch (e) {
            console.error('SSE sources parse error:', e, sse.data)
          }
        } else if (sse.event === 'clarification') {
          try {
            const data = JSON.parse(sse.data)
            assistantMsg.clarification = { ...data, resolved: false }
            messages.value[msgIndex] = { ...assistantMsg }
          } catch (e) {
            console.error('SSE clarification parse error:', e, sse.data)
          }
        } else if (sse.event === 'session') {
          try {
            const data = JSON.parse(sse.data)
            sessionId.value = data.session_id
          } catch (e) {
            console.error('SSE session parse error:', e, sse.data)
          }
        } else if (sse.event === 'error') {
          try {
            const data = JSON.parse(sse.data)
            console.error('SSE error event:', data.message)
            assistantMsg.error = ERROR_MESSAGES.sse_parse
            messages.value[msgIndex] = { ...assistantMsg }
          } catch (e) {
            console.error('SSE error parse error:', e, sse.data)
            assistantMsg.error = ERROR_MESSAGES.sse_parse
            messages.value[msgIndex] = { ...assistantMsg }
          }
        }
      }
    }

    if (!assistantMsg.content.trim() && !assistantMsg.clarification) {
      console.error('Empty response received from stream')
      assistantMsg.error = ERROR_MESSAGES.empty_response
      messages.value[msgIndex] = { ...assistantMsg }
    }
  } catch (err) {
    if (!assistantMsg.content) {
      console.error('Connection error:', err)
      assistantMsg.error = ERROR_MESSAGES.connection
    } else {
      console.warn('Stream interrupted after %d chars', assistantMsg.content.length)
      assistantMsg.error = ERROR_MESSAGES.stream_interrupted
    }
    messages.value[msgIndex] = { ...assistantMsg }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function applySuggestion(msg, type, value) {
  msg.clarification.resolved = true
  messages.value[messages.value.indexOf(msg)] = { ...msg }
  const lastUserMsg = [...messages.value].reverse().find(m => m.role === 'user')
  const originalQuery = lastUserMsg ? lastUserMsg.content : ''
  const prefixByType = { country: '', date: '', theme: '' }
  const prefix = prefixByType[type] || ''
  input.value = originalQuery + ' ' + prefix + value
  sendMessage()
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  scroll-behavior: smooth;
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

.message-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  max-width: 80%;
}

@media (max-width: 640px) {
  .message-row {
    max-width: 92%;
    gap: var(--space-2);
  }
}

.message.user .message-row {
  flex-direction: row-reverse;
}

.assistant-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background-color: var(--color-accent-container);
  color: var(--color-on-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: var(--space-1);
}

.message-bubble {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  line-height: 1.6;
}

@media (max-width: 640px) {
  .message-bubble {
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-lg);
  }
}

.message.user .message-bubble {
  background-color: var(--color-tertiary);
  color: var(--color-on-tertiary);
  border-radius: var(--radius-xl) var(--radius-sm) var(--radius-xl) var(--radius-xl);
  box-shadow: none;
}

.message.assistant .message-bubble {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm) var(--radius-xl) var(--radius-xl) var(--radius-xl);
}

.message-content {
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.6;
}

.message-content :deep(p) {
  margin: 0 0 0.6em 0;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(strong) {
  font-weight: 700;
}

.message-content :deep(em) {
  font-style: italic;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.message-content :deep(li) {
  margin-bottom: 0.35em;
}

.message-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.9em;
  background-color: var(--color-code-bg);
  padding: 0.15em 0.35em;
  border-radius: var(--radius-sm);
}

.message-content :deep(pre) {
  background-color: var(--color-code-bg);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  overflow-x: auto;
  margin: 0.75em 0;
}

.message-content :deep(pre code) {
  background: none;
  padding: 0;
}

.message-content :deep(blockquote) {
  border-left: 3px solid var(--color-accent);
  padding-left: var(--space-4);
  margin: 0.75em 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.message-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75em 0;
  font-size: var(--text-sm);
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: var(--space-2) var(--space-3);
  text-align: left;
}

.message-content :deep(th) {
  background-color: var(--color-bg);
  font-weight: 600;
}

.message-content :deep(tr:nth-child(even)) {
  background-color: var(--color-bg);
}

.error-banner {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--color-error);
  background-color: var(--color-error-bg);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-error);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.error-icon {
  flex-shrink: 0;
}

.typing-indicator {
  display: flex;
  gap: 0.4rem;
  padding: var(--space-2) 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: var(--color-accent-container);
  border-radius: 50%;
  opacity: 0.4;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.input-area {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.chat-input {
  flex: 1;
  padding: var(--space-4) var(--space-5);
  font-family: var(--font-body);
  font-size: var(--text-base);
  border: 1px solid var(--color-outline);
  border-radius: var(--radius-full);
  background-color: var(--color-surface);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(97, 0, 0, 0.08);
}

.chat-input::placeholder {
  color: var(--color-muted);
  font-style: italic;
}

.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  background-color: var(--color-accent-container);
  color: var(--color-on-accent);
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background-color 0.2s, transform 0.15s;
}

.send-btn:hover:not(:disabled) {
  background-color: var(--color-accent);
  transform: translateY(-1px);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.clarification-card {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-primary-fixed);
  border: 1px solid var(--color-primary-fixed);
  border-radius: var(--radius-md);
}

.clarification-message {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--color-accent);
  font-weight: 600;
}

.suggestion-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.suggestion-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}

.suggestion-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-muted);
  margin-right: var(--space-1);
}

.suggestion-chip {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-family: var(--font-body);
  background-color: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.suggestion-chip:hover {
  background-color: var(--color-surface-container-low);
  border-color: var(--color-accent);
}

.suggestion-chip:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
</style>
