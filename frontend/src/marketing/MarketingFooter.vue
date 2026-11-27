<template>
  <footer class="footer">
    <div class="wrap">
      <div class="foot-grid">
        <div class="foot-brand">
          <router-link class="brand" to="/" style="margin-bottom: 0">
            <HandMark :size="30" :radius="9" solid />
            <span class="name">Humanitaria</span>
          </router-link>
          <p>{{ t('footer.tagline') }}</p>
        </div>
        <div class="foot-col">
          <h3>{{ t('footer.product') }}</h3>
          <router-link :to="{ path: '/', hash: '#workflows' }">{{
            t('footer.chatReports')
          }}</router-link>
          <router-link :to="{ path: '/', hash: '#coverage' }">{{
            t('footer.coverage')
          }}</router-link>
        </div>
        <div class="foot-col">
          <h3>{{ t('footer.useCases') }}</h3>
          <router-link :to="{ path: '/', hash: '#audiences' }">{{
            t('footer.meTeams')
          }}</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">{{
            t('footer.organizations')
          }}</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">{{
            t('footer.reporting')
          }}</router-link>
          <router-link :to="{ path: '/', hash: '#audiences' }">{{
            t('footer.researchers')
          }}</router-link>
        </div>
        <div class="foot-col">
          <h3>{{ t('footer.account') }}</h3>
          <router-link to="/app">{{ t('footer.openApp') }}</router-link>
          <router-link to="/login">{{ t('footer.logIn') }}</router-link>
          <router-link to="/signup">{{ t('footer.signUp') }}</router-link>
        </div>
      </div>
      <div class="foot-base">
        <span>{{ t('footer.rights') }}</span>
        <router-link to="/privacy">{{ t('footer.privacy') }}</router-link>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import HandMark from './HandMark.vue'

const { t } = useI18n()
</script>
