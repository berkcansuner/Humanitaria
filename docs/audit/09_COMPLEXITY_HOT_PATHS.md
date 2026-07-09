# PASS 9 — Algorithmic Complexity & Hot Paths

Hot path = the chat/report request (retrieve → rerank → stream). Load model: a small
M&E team → low concurrency; the dominant cost is upstream LLM/embedding latency, not
local CPU.

## Inspected — no harmful complexity

- Retrieval post-processing (`dedupe_by_document` O(n) set; `rerank_by_recency` O(n log n)
  sort; `apply_date_filter` O(n)) all operate on a **small** candidate pool (~20–40 docs).
- Report citation normalization (`rag/citations.py`, `report_service`) runs over
  `REPORT_TOP_K=12` docs with memoized `langdetect` (TIER-3 fix: 1× per doc). Bounded.
- No nested iteration over large collections, no linear scans inside per-request loops,
  no repeated re-parsing in the hot path.

## Minor note
- The admin reports scan is O(N) over the whole namespace (~25–30K docs, ~20–30s) but is
  background + cached + off the request path (see PASS 8). Acceptable.

## Pass 9 verdict
No algorithmic hot-spot reaches harmful scale for this app's load model. No findings
above NIT.
