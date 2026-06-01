<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const { t } = useI18n()
const route = useRoute()

const emit = defineEmits<{
  openSearch: []
}>()

const pageTitle = computed(() => {
  const name = route.name as string
  if (!name) return ''
  const map: Record<string, string> = {
    dashboard: 'nav.dashboard',
    items: route.params.type ? `nav.${route.params.type}` : 'items.title',
    'item-detail': 'items.title',
    tags: 'nav.tags',
    graph: 'nav.graph',
    topics: 'nav.topics',
    timeline: 'nav.timeline',
    recommendations: 'nav.recommendations',
    wiki: 'nav.wiki',
    rag: 'nav.rag',
    backup: 'nav.backup',
    settings: 'nav.settings',
  }
  return t(map[name] || name)
})
</script>

<template>
  <header class="toolbar">
    <div class="toolbar-title">{{ pageTitle }}</div>
    <div class="toolbar-actions">
      <button class="search-trigger" @click="emit('openSearch')">
        <span class="search-icon">⌘K</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.toolbar {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  -webkit-app-region: drag;
}

@media (prefers-color-scheme: dark) {
  .toolbar {
    border-bottom-color: var(--color-border-dark);
  }
}

.toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  -webkit-app-region: no-drag;
}

@media (prefers-color-scheme: dark) {
  .toolbar-title {
    color: var(--color-text-primary-dark);
  }
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-app-region: no-drag;
}

.search-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.search-trigger:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

@media (prefers-color-scheme: dark) {
  .search-trigger {
    border-color: var(--color-border-dark);
  }
}

.search-icon {
  font-family: var(--font-mono);
  font-size: 11px;
}
</style>
