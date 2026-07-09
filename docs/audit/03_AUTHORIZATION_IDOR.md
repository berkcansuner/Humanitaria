# PASS 3 — Authorization & IDOR (sensitive-domain, elevated depth)

Assumes authentication works (PASS 2). Focus: WHO may do WHAT to WHICH resource.

## Authorization surface matrix

| Endpoint | Method | AuthN | AuthZ | Ownership/tenant check | Verdict |
|----------|--------|-------|-------|------------------------|---------|
| `/health` | GET | none | none | n/a (liveness) | OK (deep probe = P2-02) |
| `/auth/signup` `/login` | POST | public | n/a | n/a | OK (rate-limited) |
| `/auth/logout` `/me` | POST/GET | optional cookie | n/a | self | OK |
| `/auth/google/*` | GET | OAuth state | n/a | n/a | OK |
| `/chat`, `/chat/stream` | POST | required (401) | n/a | `_verify_session_owner` on client `session_id` → 404 | OK |
| `/conversations` (list) | GET | required | n/a | query scoped to `user["id"]` | OK |
| `/conversations` (create) | POST | required | n/a | server-generated id, bound to user | OK |
| `/conversations/{id}/messages` | GET | required | `_require_owner`→404 | ✅ | OK |
| `/conversations/{id}` (rename) | PATCH | required | `_require_owner`→404 | ✅ | OK |
| `/conversations/{id}` (delete) | DELETE | required | `_require_owner`→404 | ✅ | OK |
| `/conversations/{id}/truncate` | POST | required | `_require_owner`→404 | ✅ (delete scoped to conv) | OK |
| `/reports/options` `/list` | GET | required | n/a | lists / scoped to user | OK |
| `/reports/stream` | POST | required | n/a | created report bound to user | OK |
| `/reports/{id}` (get/delete/pdf) | GET/DELETE | required | `report_store.is_owner`→404 | ✅ | OK |
| `/admin/ingest/status,trigger,documents` | GET/POST | required | `get_admin_user` (ADMIN_EMAILS)→403 | n/a | OK |
| `/admin/ingest/cron` | POST | token | `secrets.compare_digest` (const-time)→403 | n/a | OK |
| `/{full_path}` (SPA) | GET | none | n/a | contained to `frontend/dist` (P1-01 fixed) | OK |

## Verdict — CLEAN (no IDOR/BOLA found)

Every per-user resource (conversations, messages, reports) is **server-side
ownership-checked** and returns **404** on a non-owner (does not leak existence).
Verified specifics:

- **No existence leak:** `_require_owner` / `is_owner` return 404 (not 403) for a
  foreign id → an attacker cannot distinguish "not yours" from "doesn't exist".
- **Client-supplied ids are gated:** chat `session_id` (only path where the client
  supplies an id) → `_verify_session_owner`: brand-new id allowed, existing-but-foreign
  → 404. `truncate_after(conv_id, id)` deletes only within the owned conversation
  (`WHERE conversation_id = ? AND id > ?`) → no cross-conversation effect.
- **Admin:** every `/admin/*` route depends on `get_admin_user`; `is_admin` is
  computed server-side from `ADMIN_EMAILS` (never trusted from the client body). Cron
  uses a constant-time token compare and is disabled when the token is empty.
- **No mass-assignment / over-posting:** all request bodies are explicit Pydantic
  models with fixed fields; `user_id` always comes from the session and `is_admin` is
  server-computed — neither is bindable from the body.
- **Store functions are owner-agnostic by design** (`get_report(id)`,
  `delete_conversation(id)` don't filter by user) but every ROUTE gates them with an
  ownership check first. Functionally correct; a belt-and-suspenders improvement would
  fold `user_id` into the store query too (defense in depth), but no reachable IDOR
  exists today.

**Sensitive-domain note:** cross-user conversation/report access — the primary risk
for this humanitarian app — is consistently prevented. The only cross-user data
exposure found in the whole audit was via P1-01 (arbitrary file read of
`conversations.db`), now fixed.

No findings.
