<template>
  <div class="mkt-scope">
    <a class="skip-link" href="#main" @click.prevent="skipToMain">{{ t('landing.skip') }}</a>
    <MarketingNav />

    <main id="main" ref="main" tabindex="-1">
      <!-- HERO -->
      <section ref="hero" class="hero">
        <div class="wrap hero-grid">
          <div class="hero-copy">
            <h1>
              {{ t('landing.hero.titleLead') }}
              <span class="h1-accent">{{ t('landing.hero.titleAccent') }}</span>
            </h1>
            <p class="hero-lede">{{ t('landing.hero.lede') }}</p>
            <form class="ask" role="search" @submit.prevent="ask">
              <label class="sr-only" for="ask-input">{{ t('landing.hero.askLabel') }}</label>
              <input
                id="ask-input"
                v-model="question"
                class="ask-input"
                type="text"
                maxlength="4000"
                autocomplete="off"
                enterkeyhint="send"
                :placeholder="t('landing.hero.askPlaceholder')"
              />
              <button class="btn btn-solid ask-btn" type="submit">
                {{ t('landing.hero.ask') }}
              </button>
            </form>
            <!-- A signed-in visitor (back on the landing from the app) is sent into the
                 app, not to sign-up. -->
            <div class="hero-cta">
              <router-link class="btn btn-solid btn-lg" :to="signedIn ? '/app' : '/signup'"
                >{{ signedIn ? t('nav.openApp') : t('landing.hero.startFree')
                }}<svg
                  class="btn-arrow"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M5 12h14M13 6l6 6-6 6" /></svg
              ></router-link>
              <router-link class="btn btn-ghost" :to="{ path: '/', hash: '#workflows' }">
                {{ t('landing.hero.howItWorks') }}
              </router-link>
            </div>
            <ul class="hero-proof">
              <li>
                <b>{{ formatNumber(coverage.countries, locale) }}</b>
                {{ t('landing.hero.countries') }}
              </li>
              <li>
                <b>{{ formatNumber(coverage.reports, locale) }}</b> {{ t('landing.hero.reports') }}
              </li>
              <li>
                <b>{{ formatNumber(monthsLabel, locale) }}</b> {{ t('landing.hero.months') }}
              </li>
            </ul>
          </div>
          <HeroComposite ref="composite" />
        </div>
      </section>

      <FlowCards />
      <DashboardPreview />

      <CoverageStats />

      <!-- USE CASES -->
      <section id="audiences" class="section audiences">
        <div class="wrap">
          <div class="section-head">
            <h2>{{ t('landing.audiences.title') }}</h2>
          </div>
          <div class="uses">
            <div class="use">
              <h3>{{ t('landing.audiences.me.title') }}</h3>
              <p>{{ t('landing.audiences.me.body') }}</p>
            </div>
            <div class="use">
              <h3>{{ t('landing.audiences.orgs.title') }}</h3>
              <p>{{ t('landing.audiences.orgs.body') }}</p>
            </div>
            <div class="use">
              <h3>{{ t('landing.audiences.research.title') }}</h3>
              <p>{{ t('landing.audiences.research.body') }}</p>
            </div>
            <div class="use">
              <h3>{{ t('landing.audiences.press.title') }}</h3>
              <p>{{ t('landing.audiences.press.body') }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="section closing">
        <div class="wrap">
          <div class="cta">
            <h2>{{ t('landing.closing.title') }}</h2>
            <p>{{ t('landing.closing.body') }}</p>
            <div class="cta-btns">
              <router-link v-if="signedIn" class="btn btn-onink" to="/app">{{
                t('nav.openApp')
              }}</router-link>
              <template v-else>
                <router-link class="btn btn-onink" to="/signup">{{
                  t('landing.closing.startFree')
                }}</router-link>
                <router-link class="btn btn-onink ghost" to="/login">{{
                  t('landing.closing.logIn')
                }}</router-link>
              </template>
            </div>
          </div>
        </div>
      </section>
    </main>

    <MarketingFooter />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { askTarget, stashQuestion } from '../utils/askQuestion.js'
import { isAuthenticated } from '../utils/authStore.js'
import { gsap } from 'gsap'
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import HeroComposite from '../marketing/HeroComposite.vue'
import FlowCards from '../marketing/FlowCards.vue'
import DashboardPreview from '../marketing/DashboardPreview.vue'
import CoverageStats from '../marketing/CoverageStats.vue'
import coverage from '../marketing/data/coverage.json'
import { formatNumber, monthsSpan } from '../marketing/landingKit.js'

const { t, locale } = useI18n()

const monthsLabel = monthsSpan(coverage.since, coverage.generated)

const router = useRouter()
const question = ref('')
const signedIn = computed(() => isAuthenticated())

// An empty field asks the sample question it shows, so the button always does something.
function ask() {
  const text = question.value.trim() || t('landing.hero.askPlaceholder')
  const target = askTarget(text)
  if (!target) return
  stashQuestion(text)
  router.push(target)
}

// The router owns the URL, so the skip link moves focus itself.
const main = useTemplateRef('main')
const skipToMain = () => main.value.focus()

const hero = useTemplateRef('hero')
const composite = useTemplateRef('composite')

// One hero sequence: copy in, cards in, the answer streams, the trend line draws.
// Reduced motion never runs it, so everything stays in its final state. The
// sequence pauses while the hero is off screen.
let mm = null
onMounted(() => {
  mm = gsap.matchMedia()
  mm.add(
    '(prefers-reduced-motion: no-preference)',
    () => {
      const tl = gsap
        .timeline({ defaults: { ease: 'expo.out', duration: 0.9 } })
        .from('.hero-copy > *', { y: 18, autoAlpha: 0, stagger: 0.07 })
        .add(composite.value.intro(), 0.2)
      const observer = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting) tl.resume()
        else if (tl.progress() < 1) tl.pause()
      })
      observer.observe(hero.value)
      return () => {
        observer.disconnect()
        composite.value?.finish()
      }
    },
    hero.value,
  )
})

onBeforeUnmount(() => mm?.revert())
</script>
