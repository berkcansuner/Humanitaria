<template>
  <footer class="footer">
    <div class="wrap">
      <div class="foot-grid">
        <div class="foot-brand">
          <router-link class="brand" to="/" style="margin-bottom: 0">
            <HandMark :size="30" :radius="9" solid />
            <span class="name">Humanitaria</span>
          </router-link>
          <p>Answers from the humanitarian record, with the source attached.</p>
        </div>
        <div class="foot-col">
          <h3>Product</h3>
          <router-link :to="{ path: '/', hash: '#workflows' }">Chat and reports</router-link>
          <router-link :to="{ path: '/', hash: '#dashboards' }">Dashboards</router-link>
          <router-link :to="{ path: '/', hash: '#coverage' }">Coverage</router-link>
        </div>
        <div class="foot-col">
          <h3>Use cases</h3>
          <router-link :to="{ path: '/', hash: '#audiences' }">M&amp;E teams</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">Organizations</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">Researchers</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">Journalists</router-link>
        </div>
        <div class="foot-col">
          <h3>Account</h3>
          <router-link to="/app">Open app</router-link>
          <router-link to="/login">Log in</router-link>
          <router-link to="/signup">Sign up</router-link>
        </div>
      </div>
      <div class="foot-base">
        <span>© 2026 Humanitaria. Content from ReliefWeb.</span>
        <router-link to="/privacy">Privacy policy</router-link>
      </div>
    </div>
  </footer>
</template>

<script setup>
import HandMark from './HandMark.vue'
</script>
