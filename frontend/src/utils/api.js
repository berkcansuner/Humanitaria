/**
 * Thin client for the conversation endpoints. Centralises JSON handling and
 * error surfacing so components don't repeat fetch boilerplate.
 */
import { handleSessionExpired } from './authStore.js'

export async function request(url, options = {}) {
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    // 401 mid-session means the cookie expired/was revoked → bounce to login.
    if (res.status === 401) handleSessionExpired()
    const err = new Error(`Request failed: ${res.status} ${url}`)
    err.status = res.status
    throw err
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

export function createConversation(title = 'New chat') {
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
