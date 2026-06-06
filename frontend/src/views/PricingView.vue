<template>
  <div class="mkt-scope" ref="root">
    <MarketingNav />

    <main id="top">
      <section class="section" id="pricing">
        <div class="wrap">
          <div class="section-head" style="text-align:center;margin-left:auto;margin-right:auto;">
            <span class="eyebrow">Pricing</span>
            <h2>Start free. Scale when you're ready.</h2>
            <p>Every plan includes cited answers grounded in real reports — the sources are never behind a paywall.</p>
          </div>
          <div class="plans">
            <div v-for="plan in plans" :key="plan.name" class="plan" :class="{ featured: plan.featured }">
              <span v-if="plan.badge" class="badge">{{ plan.badge }}</span>
              <div class="pname">{{ plan.name }}</div>
              <div class="pdesc">{{ plan.desc }}</div>
              <div class="price"><span class="amt">{{ plan.price }}</span><span class="per">{{ plan.per }}</span></div>
              <div class="pcta">
                <router-link v-if="plan.ctaTo" class="btn" :class="plan.ctaClass" :to="plan.ctaTo">{{ plan.cta }}</router-link>
                <a v-else class="btn" :class="plan.ctaClass" href="#">{{ plan.cta }}</a>
              </div>
              <ul>
                <li v-for="(feat, i) in plan.features" :key="i" :class="{ muted: feat.muted }">
                  <span class="tick">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                  </span>
                  <strong v-if="feat.strong" style="color:var(--text);font-weight:600;">{{ feat.text }}</strong>
                  <template v-else>{{ feat.text }}</template>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </main>

    <MarketingFooter />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import { useReveal } from '../marketing/useReveal.js'

const root = ref(null)

const plans = [
  {
    name: 'Free',
    desc: 'Try Humanitaria and see how cited answers work.',
    price: '$0',
    per: '/ forever',
    cta: 'Start free',
    ctaClass: 'btn-ghost',
    ctaTo: '/app',
    features: [
      { text: '5 questions per month', strong: true },
      { text: 'Cited, source-grounded answers' },
      { text: 'Single user' },
      { text: 'History & export', muted: true },
    ],
  },
  {
    name: 'Pro',
    desc: 'For everyday research and briefing.',
    price: '$19',
    per: '/ month',
    cta: 'Start Pro',
    ctaClass: 'btn-solid',
    ctaTo: '/app',
    featured: true,
    badge: 'Most popular',
    features: [
      { text: 'Unlimited questions', strong: true },
      { text: 'Full source list on every answer' },
      { text: 'Conversation history & export' },
      { text: 'Priority response speed' },
    ],
  },
  {
    name: 'Organization',
    desc: 'For teams and field offices.',
    price: 'Custom',
    per: "/ let's talk",
    cta: 'Contact sales',
    ctaClass: 'btn-ghost',
    features: [
      { text: 'Everything in Pro' },
      { text: 'Shared team workspaces' },
      { text: 'SSO & admin controls' },
      { text: 'Dedicated support' },
    ],
  },
]

useReveal(root)
</script>
