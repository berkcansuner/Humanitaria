# PASS 13 — Transaction & Consistency Boundaries

Multi-thing writes in the system: (a) ingestion = Pinecone upsert + Pinecone
orphan-delete + watermark file + reports-cache file; (b) chat = create conversation +
append user msg + append assistant msg; (c) report = create_report (single row).

## Inspected — ordering is deliberate

- **Ingestion** orders **upsert → prune-surplus → advance watermark → rebuild cache** so
  no step can leave a document with zero vectors (PASS 5). These span different systems
  (Pinecone + files) so no single transaction is possible; the ordering + idempotency
  (PASS 12) is the consistency strategy, and it is self-healing on re-run.
- **`append_message`** does the message INSERT and the `conversations.updated_at` UPDATE
  in **one** connection/transaction (atomic).

## Findings

### [P13-01] (= P5-01) Watermark advances past failed docs
**Severity:** LOW — see PASS 5. Ingestion "success" is recorded even when some docs in a
batch failed, so those docs are not retried. Consistency gap between "watermark says
done through date D" and "index actually contains all docs through D".

### [P13-02] Non-atomic state-file writes
**Severity:** LOW · **Confidence:** CONFIRMED

`scheduler._save_watermark` and `analytics._save_cache` use `path.write_text(...)` (no
temp-file + atomic rename). A crash mid-write corrupts the file; both readers catch the
parse error and degrade (watermark→None→full re-ingest; cache→empty→lazy rebuild), so
it is self-healing, but a `tmp+os.replace` write would be safer.

### [P13-03] Chat persistence spans multiple independent transactions
**Severity:** LOW · **Confidence:** CONFIRMED

`_ensure_conversation_and_seed` (create conversation) and the two `append_message` calls
(user, then assistant) in `_persist_exchange` are **separate** SQLite connections/
transactions. A crash between them can leave an empty conversation or a user message
without its assistant reply. Low impact (user-visible, re-sendable), but wrapping the
user+assistant append in one transaction would remove the window.

## Pass 13 verdict
Cross-system consistency is handled pragmatically (ordering + idempotency + self-healing
readers). No high-severity inconsistency; three LOW robustness notes.
