<template>
  <div class="mkt-scope" ref="root">
    <MarketingNav />

    <main id="top">
      <!-- HERO -->
      <section class="hero">
        <div class="wrap hero-grid">
          <div>
            <h1>Ask the humanitarian record. Get answers you can <em>cite.</em></h1>
            <p class="lead">Humanitaria turns thousands of humanitarian reports into clear, source-grounded answers so your team can read a crisis in seconds, with every claim traced back to the original report.</p>
            <div class="hero-cta">
              <router-link class="btn btn-solid btn-lg" to="/app">Start asking →</router-link>
              <button class="btn btn-ghost" type="button" @click="sampleOpen = true">See a sample answer</button>
            </div>
          </div>
        </div>
      </section>

      <!-- FEATURES -->
      <section class="section" id="features">
        <div class="wrap">
          <div class="section-head">
            <span class="eyebrow">Why Humanitaria</span>
            <h2>Built for people who need the answer — and the source.</h2>
            <p>No query syntax, no dashboards to configure. Just ask, and get a grounded answer you can act on and quote.</p>
          </div>
          <div class="features">
            <div class="fcard">
              <div class="ic">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a7.5 7.5 0 0 1-7.5 7.5H8l-4 3v-4.2A7.5 7.5 0 1 1 21 11.5z" /><path d="M8.5 11.5h7M8.5 8.5h4" /></svg>
              </div>
              <h3>Ask in plain language</h3>
              <p>Pose a question the way you'd ask a colleague. Humanitaria understands country, theme, and timeframe — and asks to clarify when it helps.</p>
            </div>
            <div class="fcard">
              <div class="ic">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></svg>
              </div>
              <h3>Cited, source-grounded answers</h3>
              <p>Every response is assembled from published reports and footnoted — so you can verify each claim and quote it with confidence.</p>
            </div>
            <div class="fcard">
              <div class="ic">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z" /></svg>
              </div>
              <h3>Current and comprehensive</h3>
              <p>Continuously indexed across countries and clusters — from displacement and food security to health and protection.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- SOURCES STRIP -->
      <section class="strip" id="sources">
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
      <section class="cit" id="citations">
        <div class="wrap section">
          <div class="cit-grid">
            <div>
              <span class="eyebrow">Traceable by design</span>
              <h2>Every claim links back to a real report.</h2>
              <p>Numbered citations point straight to the source document — open the original, check the date and publisher, and carry it into your own brief.</p>
              <ul class="cit-list">
                <li><span class="tick"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg></span> One click from claim to the published source</li>
                <li><span class="tick"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg></span> Publisher and date on every reference</li>
                <li><span class="tick"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg></span> Nothing asserted without a citation behind it</li>
              </ul>
            </div>
            <div class="srccard">
              <div class="src-h">Sources (3)</div>
              <div class="row hot">
                <span class="n">[1]</span>
                <div>
                  <div class="t">Sudan Situation Report
                    <svg class="ext" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></svg>
                  </div>
                  <div class="m">OCHA · 12 Mar 2025</div>
                </div>
              </div>
              <div class="row">
                <span class="n">[2]</span>
                <div>
                  <div class="t">Acute Food Insecurity Snapshot</div>
                  <div class="m">IPC · 20 Dec 2024</div>
                </div>
              </div>
              <div class="row">
                <span class="n">[3]</span>
                <div>
                  <div class="t">Sudan Health Cluster Bulletin</div>
                  <div class="m">WHO · 28 Feb 2025</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- USE CASES -->
      <section class="section" id="uses">
        <div class="wrap">
          <div class="section-head">
            <span class="eyebrow">Who it's for</span>
            <h2>From the field office to the newsroom.</h2>
          </div>
          <div class="uses">
            <div class="ucard">
              <div class="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18" /><path d="M5 21V7l8-4v18" /><path d="M19 21V11l-6-4" /><path d="M9 9v.01M9 12v.01M9 15v.01" /></svg></div>
              <div>
                <h3>Humanitarian organizations</h3>
                <p>Brief faster, align teams, and ground decisions in the latest field reporting — without combing through PDFs.</p>
              </div>
            </div>
            <div class="ucard">
              <div class="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18" /><path d="m7 14 3-3 3 3 5-6" /></svg></div>
              <div>
                <h3>Researchers &amp; analysts</h3>
                <p>Trace trends across countries and time, with citations ready to drop into your own analysis.</p>
              </div>
            </div>
            <div class="ucard">
              <div class="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22V4a1 1 0 0 1 1-1h11l4 4v15a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" /><path d="M8 7h6M8 11h8M8 15h8" /></svg></div>
              <div>
                <h3>Journalists</h3>
                <p>Find and verify what the response actually reported — with the original source one click away.</p>
              </div>
            </div>
            <div class="ucard">
              <div class="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-5.5 7-11a7 7 0 0 0-14 0c0 5.5 7 11 7 11z" /><circle cx="12" cy="10" r="2.4" /></svg></div>
              <div>
                <h3>Responders in the field</h3>
                <p>Get oriented on a new context in minutes — clear, cited, and light enough for a slow connection.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="section" style="padding-top:8px;">
        <div class="wrap">
          <div class="cta">
            <h2>Understand any crisis in seconds.</h2>
            <p>Join the teams using Humanitaria to turn the humanitarian record into answers they can trust and cite.</p>
            <div class="cta-btns">
              <router-link class="btn btn-onink" to="/signup">Sign up free</router-link>
              <router-link class="btn btn-onink ghost" to="/login">Log in</router-link>
            </div>
          </div>
        </div>
      </section>
    </main>

    <MarketingFooter />
    <SampleAnswerModal :open="sampleOpen" @close="sampleOpen = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import SampleAnswerModal from '../marketing/SampleAnswerModal.vue'
import { useReveal } from '../marketing/useReveal.js'

const root = ref(null)
const sampleOpen = ref(false)
const marqueeSources = ['OCHA', 'ReliefWeb', 'WHO', 'UNHCR', 'IOM', 'WFP', 'UNICEF', 'IPC', 'OCHA', 'ReliefWeb', 'WHO', 'UNHCR', 'IOM', 'WFP', 'UNICEF', 'IPC', 'OCHA', 'ReliefWeb', 'WHO', 'UNHCR', 'IOM', 'WFP', 'UNICEF', 'IPC']

useReveal(root)
</script>
