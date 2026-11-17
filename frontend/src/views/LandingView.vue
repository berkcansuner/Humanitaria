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
              Humanitaria answers questions from ReliefWeb's reports. Each claim carries a numbered
              citation that opens the original, so you can check it before you quote it.
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
            <h2>Built for people who need the source as much as the answer.</h2>
            <p>
              There's no query syntax to learn. You ask, and the answer comes back with its sources
              attached.
            </p>
          </div>
          <dl class="features">
            <div class="feature">
              <dt>Ask in plain language</dt>
              <dd>
                Ask the way you'd ask a colleague. Humanitaria picks out the country, sector and
                dates you mean, and if the question is too broad it asks you to narrow it down.
              </dd>
            </div>
            <div class="feature">
              <dt>Cited, source-grounded answers</dt>
              <dd>
                Answers are written only from the reports Humanitaria retrieves, and each statement
                points to the one it came from. If no report matches, it tells you instead of
                guessing.
              </dd>
            </div>
            <div class="feature">
              <dt>Situation reports in one step</dt>
              <dd>
                Pick a country, sector, period and language. Humanitaria reads the matching reports
                and writes a structured M&amp;E brief with the same numbered citations. Briefs are
                saved to your account, and you can export them as PDF.
              </dd>
            </div>
            <div class="feature">
              <dt>Updated every day</dt>
              <dd>
                The index holds the last twelve months of ReliefWeb and adds new reports daily. Ask
                about something older and Humanitaria will tell you it's outside that window.
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
                Each number opens the source document, with its publisher and date, so you can check
                it and cite it in your own brief.
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
                  One click from a claim to the published report
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
                  If no report matches, Humanitaria says so
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
      <section class="section" style="padding-top: 8px">
        <div class="wrap">
          <div class="cta">
            <h2>Spend your time on the evidence.</h2>
            <p>
              Ask your first question free, or generate a situation report for the country you're
              tracking.
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
