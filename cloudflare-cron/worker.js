// Daily cron Worker: triggers the app's ingest + rolling-retention pass.
//
// Render free tier sleeps after 15 min idle, so an in-process scheduler is
// unreliable. This Worker fires on a Cloudflare cron schedule and POSTs the
// token-gated endpoint, which runs synchronously (keeping the instance awake
// until the small daily job finishes).
//
// Config: APP_URL (var) + INGEST_TRIGGER_TOKEN (secret) — see README.md.
export default {
  async scheduled(event, env, ctx) {
    const url = `${env.APP_URL}/admin/ingest/cron`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "X-Cron-Token": env.INGEST_TRIGGER_TOKEN || "" },
    });
    const body = await res.text();
    console.log(`daily-cron -> ${res.status} ${body}`);
    if (!res.ok) {
      throw new Error(`cron trigger failed: ${res.status} ${body}`);
    }
  },
};
