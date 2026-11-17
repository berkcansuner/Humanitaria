<template>
  <div class="mkt-scope">
    <MarketingNav />

    <main id="top" class="section">
      <article class="wrap policy">
        <h1>Privacy policy</h1>
        <p class="updated">Last updated: 17 November 2026</p>

        <p>
          Humanitaria answers questions about humanitarian crises using public reports from
          ReliefWeb. This page explains what we store about you when you use it, who else handles
          that data, and how to delete it.
        </p>

        <h2>What we store</h2>
        <ul>
          <li>
            <strong>Your account.</strong> Your email address and name. If you sign up with a
            password, we store a bcrypt hash of it, never the password itself. If you sign in with
            Google, we store your Google account ID instead.
          </li>
          <li>
            <strong>Your conversations.</strong> The questions you ask, the answers, and the list of
            sources shown with each answer, so you can come back to them.
          </li>
          <li>
            <strong>Your reports.</strong> The situation reports you generate, with the country,
            sector, period and language you chose.
          </li>
          <li>
            <strong>A sign-in cookie.</strong> One cookie (<code>rw_session</code>) keeps you signed
            in for up to 24 hours. It holds a random token, and we store only a hash of that token.
          </li>
        </ul>
        <p>
          We do not use analytics, advertising or tracking cookies, and we do not sell or rent your
          data to anyone.
        </p>

        <h2>Signing in with Google</h2>
        <p>
          If you choose Google sign-in, Google shares your name, email address and Google account ID
          with us. We use them only to create your account and sign you in. We do not request access
          to your Gmail, Drive, contacts or any other Google data. Our use of information received
          from Google APIs follows the
          <a
            href="https://developers.google.com/terms/api-services-user-data-policy"
            target="_blank"
            rel="noopener"
            >Google API Services User Data Policy</a
          >, including its Limited Use requirements.
        </p>

        <h2>Services that process your data</h2>
        <ul>
          <li>
            <strong>Render</strong> hosts the application. Like any web host, it handles your IP
            address and request logs.
          </li>
          <li>
            <strong>Supabase</strong> hosts the database that holds your account, conversations and
            reports.
          </li>
          <li>
            <strong>Google Gemini API</strong> writes the answers and reports. Your question and the
            report excerpts we retrieve for it are sent to Gemini. We use the paid tier, under which
            Google does not use this content to improve its products.
          </li>
          <li>
            <strong>Pinecone</strong> ranks the retrieved report excerpts by relevance. Your
            question and those excerpts are sent to its ranking service; we keep no data there.
          </li>
        </ul>
        <p>
          The application also writes short technical logs (for example, sign-in events with your
          user ID) to help us find and fix errors.
        </p>

        <h2>How long we keep it</h2>
        <p>
          We keep your data until you delete it. You can delete a conversation or a report at any
          time. Deleting your account under <strong>Settings → Delete account</strong> removes your
          account, all your conversations and all your reports from our database straight away.
          Copies can remain in our hosting providers' logs or backups for a limited time before they
          expire.
        </p>

        <h2>Your choices</h2>
        <p>
          You can change your name and password in Settings, and delete your account there. For any
          other request about your data, such as a copy of what we hold, email
          <a href="mailto:berkcansuner@gmail.com">berkcansuner@gmail.com</a>.
        </p>

        <h2>Children</h2>
        <p>Humanitaria is not meant for children under 16, and we do not knowingly serve them.</p>

        <h2>Changes</h2>
        <p>
          If we change how we handle your data, we will update this page and the date at the top.
        </p>
      </article>
    </main>

    <MarketingFooter />
  </div>
</template>

<script setup>
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
</script>

<style scoped>
.policy {
  max-width: 760px;
}
.policy h1 {
  font-family: var(--font-display);
  font-size: clamp(32px, 3.6vw, 44px);
  line-height: 1.05;
  letter-spacing: -0.025em;
  font-weight: 700;
}
.updated {
  margin-top: 10px;
  color: var(--color-text-secondary);
  font-size: 15px;
}
.policy h2 {
  font-family: var(--font-display);
  font-size: 22px;
  line-height: 1.2;
  font-weight: 700;
  margin-top: 40px;
}
.policy p,
.policy li {
  font-size: 16px;
  line-height: 1.65;
}
.policy p {
  margin-top: 14px;
}
.policy ul {
  margin-top: 14px;
  padding-left: 20px;
}
.policy li + li {
  margin-top: 10px;
}
.policy a {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.policy code {
  font-family: var(--font-mono);
  font-size: 0.92em;
}
</style>
