# Daily cron Worker (Cloudflare)

Fires once a day and POSTs the app's token-gated `POST /admin/ingest/cron`, which
runs one **ingest + rolling-retention** pass (add new reports, drop docs older than
`RETENTION_DAYS`, trim each country to `RETENTION_PER_COUNTRY_CAP`). Used because the
Render free tier sleeps after 15 min idle, so an in-process scheduler is unreliable.

## Deploy (do this at cutover, once the app token is set)

1. Pick a strong shared secret and set it on the **app** (Render env):
   `INGEST_TRIGGER_TOKEN=<secret>`  (plus `RETENTION_DAYS=365`, `RETENTION_PER_COUNTRY_CAP=200`).
2. Set the same secret on the **Worker**:
   ```
   cd cloudflare-cron
   wrangler secret put INGEST_TRIGGER_TOKEN     # paste the same value
   ```
3. Update `APP_URL` in `wrangler.toml` if using a custom domain.
4. Deploy: `wrangler deploy`
5. Test once: Cloudflare dashboard → Worker → Triggers → "Run" (or wait for 03:00 UTC).
   Expect `200 {"status":"ok",...}`. A `403` means the token doesn't match.

## Notes
- The endpoint is **synchronous**: the request stays open until the (small) daily job
  finishes, keeping the free-tier instance awake.
- Until `INGEST_TRIGGER_TOKEN` is set on the app, the endpoint returns `403` (inert).
- The large initial backfill is run manually, NOT via this cron.
