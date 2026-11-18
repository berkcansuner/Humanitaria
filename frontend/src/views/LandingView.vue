<template>
  <div class="mkt-scope">
    <MarketingNav />

    <main id="top">
      <!-- HERO -->
      <section ref="hero" class="hero">
        <div class="wrap hero-grid">
          <div class="hero-copy">
            <p class="hero-status">
              <span class="status-dot" aria-hidden="true"></span>{{ reportsLabel }} ReliefWeb
              reports · updated daily
            </p>
            <h1>The humanitarian record, <span class="h1-accent">answered and cited.</span></h1>
            <p class="hero-lede">
              Ask about any crisis, generate M&amp;E situation and technical reports, and see the
              indicators behind them. Every claim links to the report it came from.
            </p>
            <form class="ask" role="search" @submit.prevent="ask">
              <label class="sr-only" for="ask-input">Ask about any crisis</label>
              <input
                id="ask-input"
                v-model="question"
                class="ask-input"
                type="text"
                maxlength="4000"
                autocomplete="off"
                enterkeyhint="send"
                placeholder="How many people are displaced in Sudan?"
              />
              <button class="btn btn-solid ask-btn" type="submit">Ask</button>
            </form>
            <div class="hero-cta">
              <router-link class="btn btn-solid btn-lg" to="/signup"
                >Start free<svg
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
                See how it works
              </router-link>
            </div>
            <ul class="hero-proof">
              <li>
                <b>{{ coverage.countries }}</b> countries
              </li>
              <li><b>12</b> months of reports</li>
              <li><b>4</b> report types</li>
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
            <h2>For people who have to cite what they write.</h2>
          </div>
          <div class="uses">
            <div class="use">
              <h3>Monitoring &amp; evaluation teams</h3>
              <p>
                Track a country or sector over time, pull the evidence behind each finding, and turn
                it into a cited situation brief for your next report.
              </p>
            </div>
            <div class="use">
              <h3>Humanitarian organizations</h3>
              <p>
                Get a sourced picture of a crisis before the coordination meeting, without opening
                every PDF first.
              </p>
            </div>
            <div class="use">
              <h3>Researchers &amp; analysts</h3>
              <p>
                Trace trends across countries and time, with citations ready to drop into your own
                analysis.
              </p>
            </div>
            <div class="use">
              <h3>Journalists</h3>
              <p>
                Check what agencies on the ground actually reported, and open the original report in
                one click.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="section closing">
        <div class="wrap">
          <div class="cta">
            <h2>Spend your time on the evidence.</h2>
            <p>
              Ask your first question free, or generate a situation report for the country you're
              tracking.
            </p>
            <div class="cta-btns">
              <router-link class="btn btn-onink" to="/signup">Start free</router-link>
              <router-link class="btn btn-onink ghost" to="/login">Log in</router-link>
            </div>
          </div>
        </div>
      </section>
    </main>

    <MarketingFooter />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { askTarget } from '../utils/askQuestion.js'
import { gsap } from 'gsap'
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import HeroComposite from '../marketing/HeroComposite.vue'
import FlowCards from '../marketing/FlowCards.vue'
import DashboardPreview from '../marketing/DashboardPreview.vue'
import CoverageStats from '../marketing/CoverageStats.vue'
import coverage from '../marketing/data/coverage.json'

const reportsLabel = coverage.reports.toLocaleString('en-US')

const router = useRouter()
const question = ref('')

function ask() {
  const target = askTarget(question.value)
  if (target) router.push(target)
}

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
