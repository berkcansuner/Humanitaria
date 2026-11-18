/**
 * Thin client for the conversation endpoints. Centralises JSON handling and
 * error surfacing so components don't repeat fetch boilerplate.
 */
import { handleSessionExpired } from './authStore.js'
import { errorFromResponse } from './errorMessage.js'
import { t } from '../i18n/index.js'

export async function request(url, options = {}) {
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    // 401 mid-session means the cookie expired/was revoked → bounce to login.
    if (res.status === 401) handleSessionExpired()
    throw await errorFromResponse(res, url)
  }
  // 204 No Content (delete) has no body to parse.
  if (res.status === 204) return null
  return res.json()
}

export function listConversations() {
  return request('/conversations', { method: 'GET' })
}

export function getMessages(id) {
  return request(`/conversations/${id}/messages`, { method: 'GET' })
}

// The default title is stored on the server as data, so it is translated here,
// once, in the language active when the conversation is created.
export function createConversation(title = t('chat.newChat')) {
  return request('/conversations', { method: 'POST', body: JSON.stringify({ title }) })
}

export function renameConversation(id, title) {
  return request(`/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) })
}

export function deleteConversation(id) {
  return request(`/conversations/${id}`, { method: 'DELETE' })
}

export function truncateConversation(id, keepThroughMessageId) {
  return request(`/conversations/${id}/truncate`, {
    method: 'POST',
    body: JSON.stringify({ keep_through_message_id: keepThroughMessageId }),
  })
}
