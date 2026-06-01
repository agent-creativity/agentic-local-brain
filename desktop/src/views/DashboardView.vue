<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('dashboard.title') }}</h1>
    <p class="page-subtitle">{{ t('dashboard.subtitle') }}</p>
    <div class="placeholder-grid">
      <div class="placeholder-card">
        <div class="placeholder-label">{{ t('dashboard.totalItems') }}</div>
        <div class="placeholder-value">--</div>
      </div>
      <div class="placeholder-card">
        <div class="placeholder-label">{{ t('dashboard.totalTags') }}</div>
        <div class="placeholder-value">--</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.placeholder-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

@media (prefers-color-scheme: dark) {
  .placeholder-card {
    background: var(--color-surface-dark);
  }
}

.placeholder-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.placeholder-value {
  font-size: 28px;
  font-weight: 700;
}
</style>
