<script setup lang="ts">
import { ref } from 'vue'
import AppLayout from './components/layout/AppLayout.vue'
import SplashScreen from './components/layout/SplashScreen.vue'

const serverReady = ref(false)

function onServerReady() {
  serverReady.value = true
}
</script>

<template>
  <SplashScreen v-if="!serverReady" @ready="onServerReady" />
  <AppLayout v-else />
</template>
