# PASS 19 — Test Gap & Assertion Quality

Baseline: **491** backend (incl. the 3 traversal tests added this audit) + **81**
frontend, all green. Coverage is genuinely broad — auth (`test_auth`), IDOR
(`test_conversation_access_control`), admin gating (`test_api_admin`), SSE
(`test_api_chat_stream`, `test_stream_retry`), ingestion (client/parser/chunker/runner/
scheduler/retention), citations/report_service/rag_context. Assertions are behavioral,
not implementation-coupled (verified by reading conftest + a sample).

## Top missing tests that would prevent the most damage

1. **Path-traversal on SPA fallback** *(P1-01)* — **ADDED** this audit
   (`tests/test_spa_fallback_security.py`; raw `../` + encoded `..%2f` + legit-route control).
2. **Rate-limiter keys on real client IP, not the proxy** *(P2-01)* — integration test:
   two distinct `X-Forwarded-For` → independent buckets; an untrusted peer cannot spoof.
   (Layer: integration.)
3. **Query-embedding timeout** *(P11-01)* — a slow/blocking embed raises within the bound
   instead of hanging ~600s (mock a slow client). (Unit.)
4. **xhtml2pdf does not fetch remote/local resources** *(P1-02)* — render a report whose
   body contains `<img src="http://127.0.0.1:PORT/probe">` and assert no outbound
   connection is made (local listener). (Integration/security.)
5. **Ingest partial-failure watermark** *(P5-01)* — a batch with a failing doc must not
   advance the watermark past that doc's date (or must re-enqueue it). (Unit/integration.)
6. **Security headers present** *(P14-02)* — assert CSP / X-Frame-Options / nosniff / HSTS
   on responses once added. (Integration.)
7. **Chat persistence atomicity** *(P13-03)* — a failure between user + assistant append
   does not leave a half-written exchange (or both are in one txn). (Unit.)
8. **Report ownership matrix** — extend the conversation IDOR tests to `/reports/{id}`
   (get/delete/pdf) with a non-owner → 404. (Integration.)
9. **Request-body size limit** *(P14-03)* — an oversized body is rejected before buffering
   the whole payload. (Integration.)
10. **Double-submit idempotency** *(P12-01)* — two concurrent `/chat/stream` for one
    session don't create duplicate/interleaved exchanges. (Concurrency/integration.)

## Pass 19 verdict
Strong existing suite. The gaps map directly to this audit's findings; #1 is already
closed. Prioritize #2–#5 (they back the MEDIUM findings).
