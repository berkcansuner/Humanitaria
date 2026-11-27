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
        <router-link :to="{ path: '/', hash: '#coverage' }">{{ t('nav.coverage') }}</router-link>
      </nav>
      <div class="nav-right">
        <LanguageSwitcher variant="marketing" />
        <!-- Signed in: the app is the primary action, in Start free's place; Log out
             takes Log in's quiet slot (hidden on phones, as Log in is; the app's
             account menu has it too). -->
        <template v-if="isAuthenticated()">
          <button class="btn btn-text" type="button" @click="logout">
            {{ t('nav.logOut') }}
          </button>
          <router-link class="btn btn-solid" to="/app">{{ t('nav.openApp') }}</router-link>
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
