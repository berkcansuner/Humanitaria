# PASS 18 — Cross-Module Contracts & Emergent Risks

| Boundary | Both sides visible? | Verdict |
|----------|---------------------|---------|
| chat route ↔ query_processor ↔ retriever | yes | OK — filters flow one way; read-only |
| backend citations ↔ frontend renumber/render | yes | OK — cooperative (see below) |
| SSE producer ↔ `parseSSE.js` | yes | OK — consistent event set |
| ingest pipeline ↔ store (upsert/delete) | yes | OK — ordering deliberate (PASS 13) |
| runner/scheduler ↔ analytics rebuild | yes | OK — shared lock pattern |
| Cloudflare Worker ↔ `/admin/ingest/cron` | yes | OK — const-time token |
| User file upload lifecycle | — | **N/A** — no user-upload endpoint exists |

## Emergent / cross-cutting checks
- **Citation contract:** the backend numbers only displayable sources
  (`_build_context_and_sources` / `_filter_cited_sources` / `normalize_citations`) and the
  frontend independently expands groups + drops dangling `[n]` and renumbers. Both sides
  defensively handle the other's edge cases (dangling markers, grouped citations) — no gap
  where each assumes the other cleans up.
- **Rate-limit coverage:** chat + auth + report-stream are limited; conversations are
  intentionally not (cheap, polled). **Gap:** the PDF export path is not limited (P18-01).
- **Security headers / CSP / clickjacking:** absent → tracked as **P14-02**.
- **Request-size / body limits:** absent → tracked as **P14-03**.

## Findings

### [P18-01] PDF export endpoint is not rate-limited (CPU amplification)
**Severity:** LOW · `GET /reports/{id}/pdf` runs `render_report_pdf` (xhtml2pdf/reportlab —
CPU-heavy) with no rate limit. An authenticated user can loop it to burn CPU on the single
worker. Auth-gated + own-report, so low, but apply the chat limiter (or a lighter one).

## Pass 18 verdict
Module boundaries have clean, cooperative contracts (notably the citation handshake). The
cross-cutting gaps are already captured (security headers P14-02, body size P14-03) plus
one new LOW (PDF export rate-limit, P18-01). File-upload lifecycle = N/A.
