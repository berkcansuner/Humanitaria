<template>
  <header class="nav">
    <div class="wrap nav-in">
      <router-link class="brand" to="/">
        <HandMark :size="34" :radius="11" />
        <span class="name">Humanitaria</span>
      </router-link>
      <nav class="nav-links">
        <router-link :to="{ path: '/', hash: '#workflows' }">Chat</router-link>
        <router-link :to="{ path: '/', hash: '#workflows' }">Reports</router-link>
        <router-link :to="{ path: '/', hash: '#dashboards' }">Dashboards</router-link>
        <router-link :to="{ path: '/', hash: '#coverage' }">Coverage</router-link>
      </nav>
      <div class="nav-right">
        <template v-if="isAuthenticated()">
          <router-link class="btn btn-text" to="/app">Open app</router-link>
          <button class="btn btn-solid" type="button" @click="logout">Log out</button>
        </template>
        <template v-else>
          <router-link class="btn btn-text" to="/login">Log in</router-link>
          <router-link class="btn btn-solid" to="/signup">Start free</router-link>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import HandMark from './HandMark.vue'
import { isAuthenticated, doLogout } from '../utils/authStore.js'

const router = useRouter()

async function logout() {
  await doLogout()
  router.push('/')
}
</script>
