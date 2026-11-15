<template>
  <!-- Inline sample answer in the citations section (replaces the old modal and the
       separate sources card). Example content, labelled as such in the card header. -->
  <figure class="sample" aria-label="Sample answer">
    <div class="sample-head">
      <HandMark :size="26" :radius="7" :stroke="1.7" solid />
      <span class="sample-title">Humanitaria</span>
      <span class="sample-tag" aria-hidden="true">Sample answer</span>
    </div>
    <div class="sample-body">
      <div class="q">What's the latest humanitarian situation in Sudan?</div>
      <div class="a">
        <h3>Sudan — current situation</h3>
        <p>
          Sudan is facing one of the world's largest displacement crises, with
          <strong>millions forced from their homes</strong> since April 2023 — most displaced inside
          the country, and many seeking refuge across borders<span class="cite">1</span>.
        </p>
        <p>
          Food insecurity has deteriorated sharply. Market collapse and disrupted farming have
          pushed several regions to <strong>critical levels of acute food insecurity</strong>, with
          famine conditions confirmed in some areas<span class="cite">2</span>.
        </p>
        <p>The health system is under severe strain:</p>
        <ul>
          <li>
            A large share of health facilities are partly or fully out of service<span class="cite"
              >3</span
            >
          </li>
          <li>Outbreaks of cholera and malaria are on the rise<span class="cite">3</span></li>
          <li>Supplies of medicine and essentials are limited<span class="cite">2</span></li>
        </ul>
        <p>
          Humanitarian access remains difficult in many areas due to insecurity and bureaucratic
          constraints<span class="cite">1</span>.
        </p>
        <div class="src">
          <div class="src-h">Sources (3)</div>
          <div class="src-item">
            <span class="n">[1]</span
            ><span
              ><span class="t">Sudan Situation Report</span>
              <span class="m">· OCHA · 12 Mar 2025</span></span
            >
          </div>
          <div class="src-item">
            <span class="n">[2]</span
            ><span
              ><span class="t">Acute Food Insecurity Snapshot</span>
              <span class="m">· IPC · 20 Dec 2024</span></span
            >
          </div>
          <div class="src-item">
            <span class="n">[3]</span
            ><span
              ><span class="t">Sudan Health Cluster Bulletin</span>
              <span class="m">· WHO · 28 Feb 2025</span></span
            >
          </div>
        </div>
      </div>
    </div>
  </figure>
</template>

<script setup>
import HandMark from './HandMark.vue'
</script>
