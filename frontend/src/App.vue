<template>
  <router-view v-slot="{ Component }">
    <KeepAlive :include="kept">
      <component :is="Component" />
    </KeepAlive>
  </router-view>
</template>

<script setup>
// App is now just the router outlet. The chat shell lives in
// views/ChatView.vue; the marketing landing page lives in views/LandingView.vue.
import { computed } from 'vue'
import { auth } from './utils/authStore.js'

// The chat screen stays alive while another screen is open, so a streaming
// answer and the open conversation are still there on the way back. Signing
// out empties the list, which drops the kept screen with its messages.
const kept = computed(() => (auth.user ? ['ChatView', 'ReportsView'] : []))
</script>
