<template>
  <footer class="footer">
    <div class="wrap">
      <div class="foot-grid">
        <div class="foot-brand">
          <router-link class="brand" to="/" style="margin-bottom:0;">
            <HandMark :size="30" :radius="9" />
            <span class="name">Humanitaria</span>
          </router-link>
          <p>Answers from the humanitarian record — clear, current, and grounded in real reporting.</p>
        </div>
        <div class="foot-col">
          <h5>Product</h5>
          <router-link :to="{ path: '/', hash: '#features' }">Features</router-link>
          <router-link :to="{ path: '/', hash: '#citations' }">Citations</router-link>
          <router-link :to="{ path: '/', hash: '#sources' }">Sources</router-link>
        </div>
        <div class="foot-col">
          <h5>Use cases</h5>
          <router-link :to="{ path: '/', hash: '#uses' }">Organizations</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Researchers</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Journalists</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Responders</router-link>
        </div>
        <div class="foot-col">
          <h5>Company</h5>
          <router-link to="/app">Open app</router-link>
          <router-link to="/login">Log in</router-link>
          <router-link to="/signup">Sign up</router-link>
        </div>
      </div>
      <div class="foot-base">
        <span>© 2026 Humanitaria. Grounded in real humanitarian reporting.</span>
        <span>Built for the humanitarian community.</span>
      </div>
    </div>
  </footer>
</template>

<script setup>
import HandMark from './HandMark.vue'
</script>
