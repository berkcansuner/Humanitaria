/**
 * Thin client for the conversation endpoints. Centralises JSON handling and
 * error surfacing so components don't repeat fetch boilerplate.
 */

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${url}`)
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

export function createConversation(title = 'Yeni sohbet') {
  return request('/conversations', { method: 'POST', body: JSON.stringify({ title }) })
}

export function renameConversation(id, title) {
  return request(`/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) })
}

export function deleteConversation(id) {
  return request(`/conversations/${id}`, { method: 'DELETE' })
}
