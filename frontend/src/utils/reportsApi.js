/**
 * M&E report endpoints. Reuses the shared request() wrapper (credentials + JSON
 * + 401 → session-expired). Streaming generation is done with a raw fetch in the
 * view (like the chat composer), so it is not wrapped here.
 */
import { request } from './api.js'

export function getReportOptions() {
  return request('/reports/options', { method: 'GET' })
}

export function listReports() {
  return request('/reports/list', { method: 'GET' })
}

export function getReport(id) {
  return request(`/reports/${id}`, { method: 'GET' })
}

export function deleteReport(id) {
  return request(`/reports/${id}`, { method: 'DELETE' })
}
