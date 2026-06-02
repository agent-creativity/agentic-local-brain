<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { healthCheck } from '../../api/client'

const { t } = useI18n()

const emit = defineEmits<{ ready: [] }>()
const dots = ref('')

let pollTimer: ReturnType<typeof setInterval>
let dotTimer: ReturnType<typeof setInterval>

onMounted(() => {
  dotTimer = setInterval(() => {
    dots.value = dots.value.length >= 3 ? '' : dots.value + '.'
  }, 500)

  pollTimer = setInterval(async () => {
    const ok = await healthCheck()
    if (ok) {
      clearInterval(pollTimer)
      clearInterval(dotTimer)
      emit('ready')
    }
  }, 1000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(dotTimer)
})
</script>

<template>
  <div class="splash">
    <div class="splash-content">
      <div class="splash-logo">⚛️</div>
      <h1 class="splash-title">Agentic Local Brain</h1>
      <p class="splash-status">{{ t('common.loading') }}{{ dots }}</p>
    </div>
  </div>
</template>

<style scoped>
.splash {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: 100vh;
  background: var(--color-background);
  -webkit-app-region: drag;
}

@media (prefers-color-scheme: dark) {
  .splash {
    background: var(--color-background-dark);
  }
}

.splash-content {
  text-align: center;
  -webkit-app-region: no-drag;
}

.splash-logo {
  font-size: 64px;
  margin-bottom: 16px;
}

.splash-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

@media (prefers-color-scheme: dark) {
  .splash-title {
    color: var(--color-text-primary-dark);
  }
}

.splash-status {
  font-size: 14px;
  color: var(--color-text-secondary);
  min-width: 120px;
}
</style>
