<template>
  <footer class="footer">
    <div class="wrap">
      <div class="foot-grid">
        <div class="foot-brand">
          <router-link class="brand" to="/" style="margin-bottom: 0">
            <HandMark :size="30" :radius="9" />
            <span class="name">Humanitaria</span>
          </router-link>
          <p>Answers from the humanitarian record, with the source attached.</p>
        </div>
        <div class="foot-col">
          <h5>Product</h5>
          <router-link :to="{ path: '/', hash: '#features' }">Features</router-link>
          <router-link :to="{ path: '/', hash: '#citations' }">Citations</router-link>
          <router-link :to="{ path: '/', hash: '#sources' }">Sources</router-link>
        </div>
        <div class="foot-col">
          <h5>Use cases</h5>
          <router-link :to="{ path: '/', hash: '#uses' }">M&amp;E teams</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Organizations</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Researchers</router-link>
          <router-link :to="{ path: '/', hash: '#uses' }">Journalists</router-link>
        </div>
        <div class="foot-col">
          <h5>Account</h5>
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
