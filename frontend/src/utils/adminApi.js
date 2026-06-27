/**
 * Admin-only ingestion endpoints. Reuses the shared request() wrapper from
 * api.js (credentials + JSON + 401 → session-expired handling). A 403 surfaces
 * as an error with `.status === 403` for the view to handle.
 */
import { request } from './api.js'

export function getIngestStatus() {
  return request('/admin/ingest/status', { method: 'GET' })
}

export function triggerIngest() {
  return request('/admin/ingest/trigger', { method: 'POST' })
}
