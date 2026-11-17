<template>
  <div class="mkt-scope">
    <MarketingNav />

    <main id="top">
      <!-- HERO -->
      <section class="hero">
        <div class="wrap hero-grid">
          <div>
            <h1>Ask the humanitarian record. Get answers you can <em>cite.</em></h1>
            <p class="lead">
              Humanitaria turns thousands of humanitarian reports into clear, source-grounded
              answers so your team can read a crisis in seconds, with every claim traced back to the
              original report.
            </p>
            <div class="hero-cta">
              <router-link class="btn btn-solid btn-lg" to="/app"
                >Start asking<svg
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
              <router-link class="btn btn-ghost" :to="{ path: '/', hash: '#citations' }">
                See a sample answer
              </router-link>
            </div>
          </div>
        </div>
      </section>

      <!-- FEATURES -->
      <section id="features" class="section">
        <div class="wrap">
          <div class="section-head">
            <h2>Built for people who need the answer — and the source.</h2>
            <p>
              No query syntax, no dashboards to configure. Just ask, and get a grounded answer you
              can act on and quote.
            </p>
          </div>
          <dl class="features">
            <div class="feature">
              <dt>Ask in plain language</dt>
              <dd>
                Pose a question the way you'd ask a colleague. Humanitaria understands country,
                theme, and timeframe — and asks to clarify when it helps.
              </dd>
            </div>
            <div class="feature">
              <dt>Cited, source-grounded answers</dt>
              <dd>
                Every response is assembled from published reports and footnoted — so you can verify
                each claim and quote it with confidence.
              </dd>
            </div>
            <div class="feature">
              <dt>Situation reports in one step</dt>
              <dd>
                Pick a country, sector, period and language. Humanitaria synthesizes the matching
                reports into a structured M&amp;E brief, cited like every answer, saved to your
                account and exportable as PDF.
              </dd>
            </div>
            <div class="feature">
              <dt>Current and comprehensive</dt>
              <dd>
                Continuously indexed across countries and clusters — from displacement and food
                security to health and protection.
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <!-- SOURCES STRIP -->
      <section id="sources" class="strip">
        <div class="marquee">
          <div class="marquee-track">
            <div class="marquee-group">
              <span v-for="(s, i) in marqueeSources" :key="'a' + i">{{ s }}</span>
            </div>
            <div class="marquee-group" aria-hidden="true">
              <span v-for="(s, i) in marqueeSources" :key="'b' + i">{{ s }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- CITATIONS HIGHLIGHT -->
      <section id="citations" class="cit section">
        <div class="wrap">
          <div class="cit-grid">
            <div class="cit-copy">
              <h2>Every claim links back to a real report.</h2>
              <p>
                Numbered citations point straight to the source document — open the original, check
                the date and publisher, and carry it into your own brief.
              </p>
              <ul class="cit-list">
                <li>
                  <span class="tick"
                    ><svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.4"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M20 6 9 17l-5-5" /></svg
                  ></span>
                  One click from claim to the published source
                </li>
                <li>
                  <span class="tick"
                    ><svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.4"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M20 6 9 17l-5-5" /></svg
                  ></span>
                  Publisher and date on every reference
                </li>
                <li>
                  <span class="tick"
                    ><svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.4"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M20 6 9 17l-5-5" /></svg
                  ></span>
                  Nothing asserted without a citation behind it
                </li>
              </ul>
            </div>
            <SampleAnswer />
          </div>
        </div>
      </section>

      <!-- USE CASES -->
      <section id="uses" class="section">
        <div class="wrap">
          <div class="section-head">
            <h2>From the field office to the newsroom.</h2>
          </div>
          <div class="uses">
            <div class="use">
              <h3>Humanitarian organizations</h3>
              <p>
                Brief faster, align teams, and ground decisions in the latest field reporting —
                without combing through PDFs.
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
                Find and verify what the response actually reported — with the original source one
                click away.
              </p>
            </div>
            <div class="use">
              <h3>Responders in the field</h3>
              <p>
                Get oriented on a new context in minutes — clear, cited, and light enough for a slow
                connection.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="section" style="padding-top: 8px">
        <div class="wrap">
          <div class="cta">
            <h2>Understand any crisis in seconds.</h2>
            <p>
              Join the teams using Humanitaria to turn the humanitarian record into answers they can
              trust and cite.
            </p>
            <div class="cta-btns">
              <router-link class="btn btn-onink" to="/signup">Sign up free</router-link>
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
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import SampleAnswer from '../marketing/SampleAnswer.vue'

const marqueeSources = [
  'OCHA',
  'ReliefWeb',
  'WHO',
  'UNHCR',
  'IOM',
  'WFP',
  'UNICEF',
  'IPC',
  'OCHA',
  'ReliefWeb',
  'WHO',
  'UNHCR',
  'IOM',
  'WFP',
  'UNICEF',
  'IPC',
  'OCHA',
  'ReliefWeb',
  'WHO',
  'UNHCR',
  'IOM',
  'WFP',
  'UNICEF',
  'IPC',
]
</script>
