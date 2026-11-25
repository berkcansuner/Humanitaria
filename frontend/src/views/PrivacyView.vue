<!--
  Privacy policy. The English text (locales/en.json, privacy.*) is the original and
  the legally binding version; the Turkish text (locales/tr.json, privacy.*) is a
  translation of it. Keep the structure of both identical: same sections, same lists,
  same links. /privacy is the URL used for Google OAuth brand verification.
-->
<template>
  <div class="mkt-scope">
    <MarketingNav />

    <main id="top" class="section">
      <article class="wrap policy">
        <h1>{{ t('privacy.title') }}</h1>
        <p class="updated">{{ t('privacy.updated') }}</p>
        <p v-if="locale === 'tr'" class="translation-note">{{ t('privacy.translationNote') }}</p>

        <p>{{ t('privacy.intro') }}</p>

        <h2>{{ t('privacy.s1.title') }}</h2>
        <ul>
          <li>
            <strong>{{ t('privacy.s1.l1.lead') }}</strong> {{ t('privacy.s1.l1.text') }}
          </li>
          <li>
            <strong>{{ t('privacy.s1.l2.lead') }}</strong> {{ t('privacy.s1.l2.text') }}
          </li>
          <li>
            <strong>{{ t('privacy.s1.l3.lead') }}</strong> {{ t('privacy.s1.l3.text') }}
          </li>
          <li>
            <!-- i18n-t renders bare text, so the space after the bold lead is explicit -->
            <strong>{{ t('privacy.s1.l4.lead') }}</strong
            >{{ ' ' }}
            <i18n-t keypath="privacy.s1.l4.text" scope="global">
              <template #cookie><code>rw_session</code></template>
            </i18n-t>
          </li>
        </ul>
        <p>{{ t('privacy.s1.after') }}</p>

        <h2>{{ t('privacy.s2.title') }}</h2>
        <i18n-t keypath="privacy.s2.p1" tag="p" scope="global">
          <template #policy>
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener"
              >{{ t('privacy.s2.policyLink') }}</a
            >
          </template>
        </i18n-t>

        <h2>{{ t('privacy.s3.title') }}</h2>
        <ul>
          <li>
            <strong>{{ t('privacy.s3.l1.lead') }}</strong> {{ t('privacy.s3.l1.text') }}
          </li>
          <li>
            <strong>{{ t('privacy.s3.l2.lead') }}</strong> {{ t('privacy.s3.l2.text') }}
          </li>
          <li>
            <strong>{{ t('privacy.s3.l3.lead') }}</strong> {{ t('privacy.s3.l3.text') }}
          </li>
          <li>
            <strong>{{ t('privacy.s3.l4.lead') }}</strong> {{ t('privacy.s3.l4.text') }}
          </li>
        </ul>
        <p>{{ t('privacy.s3.after') }}</p>

        <h2>{{ t('privacy.s4.title') }}</h2>
        <i18n-t keypath="privacy.s4.p1" tag="p" scope="global">
          <template #path
            ><strong>{{ t('privacy.s4.path') }}</strong></template
          >
        </i18n-t>

        <h2>{{ t('privacy.s5.title') }}</h2>
        <i18n-t keypath="privacy.s5.p1" tag="p" scope="global">
          <template #email>
            <a :href="'mailto:' + PRIVACY_EMAIL">{{ PRIVACY_EMAIL }}</a>
          </template>
        </i18n-t>

        <h2>{{ t('privacy.s6.title') }}</h2>
        <p>{{ t('privacy.s6.p1') }}</p>

        <h2>{{ t('privacy.s7.title') }}</h2>
        <p>{{ t('privacy.s7.p1') }}</p>
      </article>
    </main>

    <MarketingFooter />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import { PRIVACY_EMAIL } from '../contact.js'

const { t, locale } = useI18n()
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
.policy .translation-note {
  margin-top: 6px;
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
