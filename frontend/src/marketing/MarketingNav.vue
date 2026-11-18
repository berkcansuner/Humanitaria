<template>
  <header class="nav">
    <div class="wrap nav-in">
      <router-link class="brand" to="/">
        <HandMark :size="34" :radius="11" solid />
        <span class="name">Humanitaria</span>
      </router-link>
      <nav class="nav-links">
        <router-link :to="{ path: '/', hash: '#workflows' }">{{ t('nav.chat') }}</router-link>
        <router-link :to="{ path: '/', hash: '#workflows' }">{{ t('nav.reports') }}</router-link>
        <router-link :to="{ path: '/', hash: '#dashboards' }">{{
          t('nav.dashboards')
        }}</router-link>
        <router-link :to="{ path: '/', hash: '#coverage' }">{{ t('nav.coverage') }}</router-link>
      </nav>
      <div class="nav-right">
        <LanguageSwitcher variant="marketing" />
        <template v-if="isAuthenticated()">
          <router-link class="btn btn-text" to="/app">{{ t('nav.openApp') }}</router-link>
          <button class="btn btn-solid" type="button" @click="logout">
            {{ t('nav.logOut') }}
          </button>
        </template>
        <template v-else>
          <router-link class="btn btn-text" to="/login">{{ t('nav.logIn') }}</router-link>
          <router-link class="btn btn-solid" to="/signup">{{ t('nav.startFree') }}</router-link>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HandMark from './HandMark.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { isAuthenticated, doLogout } from '../utils/authStore.js'

const router = useRouter()
const { t } = useI18n()

async function logout() {
  await doLogout()
  router.push('/')
}
</script>
