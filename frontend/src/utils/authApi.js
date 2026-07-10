/**
 * Auth endpoints (email/password + httpOnly session cookie). Every call sends
 * `credentials: 'include'` so the session cookie travels with the request.
 */

async function request(url, options = {}) {
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = new Error(`Request failed: ${res.status} ${url}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

export function signup(email, password, name) {
  return request('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  })
}

export function login(email, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function logout() {
  return request('/auth/logout', { method: 'POST' })
}

export function me() {
  return request('/auth/me', { method: 'GET' })
}

export function updateProfile(name) {
  return request('/auth/me', { method: 'PATCH', body: JSON.stringify({ name }) })
}

export function changePassword(currentPassword, newPassword) {
  return request('/auth/me/password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

// body: { password } for password accounts, { confirm_email } for Google-only.
export function deleteAccount(body) {
  return request('/auth/me', { method: 'DELETE', body: JSON.stringify(body) })
}
