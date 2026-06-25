<template>
  <div class="chat">
    <div class="messages" ref="messagesContainer" role="log" aria-live="polite" @click="onCiteClick" @keydown="onCiteKeydown">
      <EmptyState v-if="messages.length === 0" @select="sendMessage({ text: $event })" />
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
        role="article"
        :aria-label="msg.role === 'user' ? 'Your message' : 'Assistant message'"
      >
        <div class="message-row">
          <div class="message-bubble">
            <template v-if="msg.role === 'assistant' && !msg.content && !msg.error && !msg.clarification">
              <div class="typing-indicator" role="status">
                <span></span>
                <span></span>
                <span></span>
                <span class="sr-only">Generating response…</span>
              </div>
            </template>
            <template v-else>
              <div v-if="editingIndex === idx" class="edit-box">
                <textarea
                  ref="editTextarea"
                  v-model="editText"
                  class="edit-textarea"
                  rows="3"
                  aria-label="Edit your message"
                  @keydown.esc="cancelEdit"
                  @keydown.enter.exact.prevent="saveEdit"
                ></textarea>
                <div class="edit-actions">
                  <button type="button" class="edit-cancel" @click="cancelEdit">Cancel</button>
                  <button type="button" class="edit-save" @click="saveEdit">Save & send</button>
                </div>
              </div>
              <template v-else>
                <div class="message-content" v-html="renderMarkdown(msg.content, msg.sources)"></div>
                <div v-if="msg.error" class="error-banner">
                  <AlertCircle :size="16" class="error-icon" />
                  {{ msg.error }}
                </div>
                <SuggestionCardIsland
                  v-if="msg.clarification && !msg.clarification.resolved"
                  :clarification="msg.clarification"
                  @apply="onSuggestionApply(msg, $event)"
                  @dismiss="onSuggestionDismiss(msg)"
                />
                <SourceList v-if="msg.sources" :sources="msg.sources" />
                <MessageActions
                  v-if="msg.content && !msg.error && !(loading && idx === messages.length - 1)"
                  :role="msg.role"
                  :content="msg.content"
                  :can-regenerate="idx === messages.length - 1"
                  @regenerate="regenerate"
                  @edit="startEdit(idx)"
                />
              </template>
            </template>
          </div>
        </div>
      </div>
    </div>
    <form class="input-area" @submit.prevent="sendMessage">
      <textarea
        ref="chatInput"
        v-model="input"
        rows="1"
        placeholder="Ask about humanitarian documents…"
        class="chat-input"
        aria-label="Chat message input"
        enterkeyhint="send"
        @input="autoGrow"
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <button
        v-if="loading"
        type="button"
        class="send-btn stop-btn"
        @click="stopGenerating"
        aria-label="Stop generating"
      >
        <Square :size="18" />
      </button>
      <button v-else type="submit" class="send-btn" :disabled="!input.trim()" aria-label="Send message">
        <Send :size="20" />
      </button>
    </form>
    <p class="composer-hint">Responses are generated from real humanitarian reports.</p>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, defineAsyncComponent } from 'vue'
import { Send, Loader2, AlertCircle, Square } from 'lucide-vue-next'
import SourceList from './SourceList.vue'
import EmptyState from './EmptyState.vue'
import MessageActions from './MessageActions.vue'
// The one intentional React island in this otherwise-Vue app: the clarification
// card (React + react-dom + lucide-react). Lazy-loaded so its runtime stays out
// of the initial bundle (only needed when a clarification is shown). Its CSS
// (react/SuggestionCard.css) is the reference for our focus-ring + reduced-motion
// conventions. A future Vue port would remove the second runtime.
const SuggestionCardIsland = defineAsyncComponent(() => import('./SuggestionCardIsland.vue'))
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { parseSSE } from '../utils/parseSSE.js'
import { renumberCitations } from '../utils/renumberCitations.js'
import { decorateCodeBlocks } from '../utils/codeCopy.js'
import { findLastUserIndex, lastServerIdBefore, planResend } from '../utils/conversationOps.js'
import { getMessages, truncateConversation } from '../utils/api.js'
import { handleSessionExpired } from '../utils/authStore.js'

const ERROR_MESSAGES = {
  connection: 'Connection lost. Please try again.',
  stream_interrupted: 'Response interrupted. Some content may be missing.',
  empty_response: 'No response received. Please try again.',
  sse_parse: 'Something went wrong. Please try again.',
}

const props = defineProps({
  conversationId: { type: String, default: null },
})
const emit = defineEmits(['session'])

const messages = ref([])
const input = ref('')
const loading = ref(false)
const sessionId = ref(null)
const messagesContainer = ref(null)
const chatInput = ref(null)
const controller = ref(null)
const editingIndex = ref(null)
const editText = ref('')
const editTextarea = ref(null)



async function sendMessage(opts = {}) {
  // opts.text  -> send this query instead of the composer's value
  // opts.silent -> don't add a visible user bubble (used for refined queries
  //                applied from the suggestion card)
  const text = (opts.text != null ? opts.text : input.value).trim()
  if (!text || loading.value) return

  if (!opts.silent) {
    messages.value.push({ role: 'user', content: text, error: null, serverId: null })
  }
  if (opts.text == null) {
    input.value = ''
    nextTick(autoGrow)
  }
  loading.value = true

  const assistantMsg = { role: 'assistant', content: '', sources: null, error: null, clarification: null, serverId: null }
  messages.value.push(assistantMsg)
  const msgIndex = messages.value.length - 1
  scrollToBottom()

  controller.value = new AbortController()
  try {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content })),
        session_id: sessionId.value,
      }),
      signal: controller.value.signal,
    })
    if (!res.ok) {
      console.error(`API error: ${res.status} ${res.statusText} — POST /chat/stream`)
      // Session expired mid-conversation → bounce to login instead of showing a
      // generic connection error the user can't act on.
      if (res.status === 401) {
        handleSessionExpired()
        return
      }
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
            // The answer is fully streamed by the time sources arrive, so we can
            // renumber the cited [n] markers and the source list to a contiguous
            // 1..M sequence (the backend keeps original retrieval positions).
            const { content, sources } = renumberCitations(assistantMsg.content, data.sources)
            assistantMsg.content = content
            assistantMsg.sources = sources
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
            // Set our own id BEFORE notifying the parent so the conversationId
            // watcher sees newId === sessionId and skips a redundant reload.
            sessionId.value = data.session_id
            emit('session', data.session_id)
          } catch (e) {
            console.error('SSE session parse error:', e, sse.data)
          }
        } else if (sse.event === 'persisted') {
          try {
            const data = JSON.parse(sse.data)
            // Tag the just-saved messages with their server ids so Edit/
            // Regenerate can target a precise truncate cut point.
            const lastUser = findLastUserIndex(messages.value)
            if (lastUser !== -1) messages.value[lastUser].serverId = data.user_id
            assistantMsg.serverId = data.assistant_id
            messages.value[msgIndex] = { ...assistantMsg }
          } catch (e) {
            console.error('SSE persisted parse error:', e, sse.data)
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
    if (err?.name === 'AbortError') {
      // User pressed Stop — keep whatever streamed so far with no error banner.
      // If nothing streamed yet, drop the empty assistant bubble.
      if (!assistantMsg.content.trim()) {
        messages.value.splice(msgIndex, 1)
      } else {
        messages.value[msgIndex] = { ...assistantMsg }
      }
      return
    }
    if (!assistantMsg.content) {
      console.error('Connection error:', err)
      assistantMsg.error = ERROR_MESSAGES.connection
    } else {
      console.warn('Stream interrupted after %d chars', assistantMsg.content.length)
      assistantMsg.error = ERROR_MESSAGES.stream_interrupted
    }
    messages.value[msgIndex] = { ...assistantMsg }
  } finally {
    controller.value = null
    loading.value = false
    scrollToBottom()
    // Add copy buttons to any code blocks now that the message is fully rendered
    // (decorateCodeBlocks is idempotent, so re-decorating the container is safe).
    nextTick(() => {
      decorateCodeBlocks(messagesContainer.value)
      chatInput.value?.focus()
    })
  }
}

function stopGenerating() {
  controller.value?.abort()
}

// Scroll to a citation chip's source within the same message and briefly
// highlight it. The chips are <a> elements injected by renderMarkdown().
function scrollToCitedSource(cite) {
  const id = cite.getAttribute('data-cite')
  const message = cite.closest('.message')
  const item = message?.querySelector(`.source-item[data-srcid="${id}"]`)
  if (!item) return
  // Persistent active marker (one per message) + a brief flash pulse.
  message.querySelectorAll('.source-item.active').forEach((el) => el.classList.remove('active'))
  item.classList.add('active')
  item.scrollIntoView({ behavior: 'smooth', block: 'center' })
  item.classList.add('flash')
  setTimeout(() => item.classList.remove('flash'), 1500)
}

function onCiteClick(e) {
  const cite = e.target.closest('.cite')
  if (!cite) return
  e.preventDefault()
  scrollToCitedSource(cite)
}

// Keyboard parity: the chips are focusable <a>s, but the scroll + highlight only
// ran on mouse click before — Enter/Space now triggers the same behavior.
function onCiteKeydown(e) {
  if (e.key !== 'Enter' && e.key !== ' ') return
  const cite = e.target.closest?.('.cite')
  if (!cite) return
  e.preventDefault()
  scrollToCitedSource(cite)
}

async function resendFrom(targetIndex, text) {
  // Shared by Regenerate and Edit: drop the target user turn (and everything
  // after) on both the server and the client, then re-ask. The server truncate
  // keeps the conversation + window consistent so the re-sent turn isn't a
  // duplicate. keep_through is the last persisted message before the target.
  if (loading.value || targetIndex < 0) return
  let truncateOk = true
  if (sessionId.value) {
    try {
      await truncateConversation(sessionId.value, lastServerIdBefore(messages.value, targetIndex))
    } catch (e) {
      // A swallowed truncate failure would leave the server holding the old
      // turns while the client drops them — re-sending then duplicates the
      // turn on reload. Abort the resend and surface the error instead.
      console.error('Truncate failed:', e)
      truncateOk = false
    }
  }
  const plan = planResend(messages.value, targetIndex, truncateOk, ERROR_MESSAGES.connection)
  messages.value = plan.messages
  if (plan.resend) sendMessage({ text })
}

function regenerate() {
  const u = findLastUserIndex(messages.value)
  if (u === -1) return
  resendFrom(u, messages.value[u].content)
}

function startEdit(idx) {
  if (loading.value) return
  editingIndex.value = idx
  editText.value = messages.value[idx].content
  nextTick(() => {
    const el = Array.isArray(editTextarea.value) ? editTextarea.value[0] : editTextarea.value
    el?.focus()
  })
}

function cancelEdit() {
  editingIndex.value = null
}

function saveEdit() {
  const idx = editingIndex.value
  const text = editText.value.trim()
  editingIndex.value = null
  if (idx == null || !text) return
  resendFrom(idx, text)
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Grow the composer textarea with its content up to a few lines, then scroll
// internally. Reset to one line when the field is cleared after sending.
function autoGrow() {
  const el = chatInput.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function onSuggestionApply(msg, values) {
  msg.clarification.resolved = true
  messages.value[messages.value.indexOf(msg)] = { ...msg }
  const lastUserMsg = [...messages.value].reverse().find(m => m.role === 'user')
  const originalQuery = lastUserMsg ? lastUserMsg.content : ''
  const enriched = (originalQuery + ' ' + values.join(' ')).trim()
  // Refine the search silently — no second user bubble with the raw query.
  sendMessage({ text: enriched, silent: true })
}

function onSuggestionDismiss(msg) {
  msg.clarification.resolved = true
  messages.value[messages.value.indexOf(msg)] = { ...msg }
  nextTick(() => chatInput.value?.focus())
}

// React to conversation switches driven by the sidebar (via the conversationId
// prop). A null id means "new chat"; an id we already show is a no-op (this is
// also what keeps the freshly-created-conversation echo from reloading).
watch(() => props.conversationId, async (newId) => {
  if (newId === sessionId.value) return
  if (loading.value) controller.value?.abort()
  if (!newId) {
    messages.value = []
    sessionId.value = null
    return
  }
  try {
    const rows = await getMessages(newId)
    messages.value = rows.map(m => ({
      role: m.role,
      content: m.content,
      sources: m.sources || null,
      error: null,
      clarification: null,
      serverId: m.id,
    }))
    sessionId.value = newId
    nextTick(() => decorateCodeBlocks(messagesContainer.value))
  } catch (e) {
    console.error('Failed to load conversation:', e)
  }
})
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

/* Cap answer line length at a comfortable reading measure on wide screens. */
.message.assistant .message-content {
  max-width: 70ch;
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

.edit-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 280px;
}

.edit-textarea {
  width: 100%;
  padding: var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  outline: none;
  resize: vertical;
  line-height: 1.5;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.edit-cancel,
.edit-save {
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
  cursor: pointer;
  border: 1px solid var(--color-border);
}

.edit-cancel {
  background-color: var(--color-surface);
  color: var(--color-text-secondary);
}

.edit-save {
  background-color: var(--color-accent-container);
  color: var(--color-on-accent);
  border-color: var(--color-accent-container);
  font-weight: 600;
}

.edit-save:hover {
  background-color: var(--color-accent);
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
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.chat-input {
  flex: 1;
  display: block;
  padding: var(--space-3) var(--space-5);
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.5;
  border: 1px solid var(--color-outline);
  border-radius: var(--radius-lg);
  background-color: var(--color-surface);
  color: var(--color-text);
  outline: none;
  resize: none;
  max-height: 160px;
  overflow-y: auto;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 18%, transparent);
}

.chat-input::placeholder {
  color: var(--color-muted);
  font-style: italic;
}

.composer-hint {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-muted);
  margin-top: var(--space-2);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
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
  transform: scale(0.94);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stop-btn {
  background-color: var(--color-tertiary);
  color: var(--color-on-tertiary);
}

.stop-btn:hover {
  background-color: var(--color-text-secondary);
  transform: translateY(-1px);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

</style>
