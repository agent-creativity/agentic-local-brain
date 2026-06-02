<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()

interface NavItem {
  label: string
  icon: string
  to: string
  match?: (path: string) => boolean
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    label: '',
    items: [
      { label: 'nav.dashboard', icon: '🏠', to: '/', match: (p) => p === '/' },
    ],
  },
  {
    label: 'nav.knowledge',
    items: [
      { label: 'nav.allItems', icon: '📋', to: '/items', match: (p) => p === '/items' },
      { label: 'nav.note', icon: '📝', to: '/items/note' },
      { label: 'nav.bookmark', icon: '🔖', to: '/items/bookmark' },
      { label: 'nav.webpage', icon: '🌐', to: '/items/webpage' },
      { label: 'nav.paper', icon: '📄', to: '/items/paper' },
      { label: 'nav.email', icon: '✉️', to: '/items/email' },
      { label: 'nav.file', icon: '📁', to: '/items/file' },
    ],
  },
  {
    label: 'nav.discover',
    items: [
      { label: 'nav.tags', icon: '🏷️', to: '/tags' },
      { label: 'nav.mining', icon: '⛏️', to: '/mining' },
      { label: 'nav.graph', icon: '🕸️', to: '/graph' },
      { label: 'nav.topics', icon: '📊', to: '/topics' },
      { label: 'nav.timeline', icon: '📅', to: '/timeline' },
      { label: 'nav.recommendations', icon: '💡', to: '/recommendations' },
    ],
  },
  {
    label: 'nav.tools',
    items: [
      { label: 'nav.wiki', icon: '📚', to: '/wiki' },
      { label: 'nav.rag', icon: '🤖', to: '/rag' },
      { label: 'nav.backup', icon: '💾', to: '/backup' },
      { label: 'nav.settings', icon: '⚙️', to: '/settings' },
    ],
  },
]

function isActive(item: NavItem): boolean {
  if (item.match) return item.match(route.path)
  return route.path.startsWith(item.to)
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header titlebar-drag-region">
      <div class="sidebar-title titlebar-no-drag">
        <span class="sidebar-logo">⚛️</span>
        <span class="sidebar-name">{{ t('app.name') }}</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div v-for="(group, gi) in navGroups" :key="gi" class="nav-group">
        <div v-if="group.label" class="nav-group-label">{{ t(group.label) }}</div>
        <router-link
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ t(item.label) }}</span>
        </router-link>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  height: 100vh;
  background: var(--color-sidebar-bg);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  user-select: none;
  overflow-y: auto;
  flex-shrink: 0;
}

@media (prefers-color-scheme: dark) {
  .sidebar {
    background: var(--color-sidebar-bg-dark);
    border-right-color: var(--color-border-dark);
  }
}

.sidebar-header {
  padding: 12px 16px 8px;
  padding-top: 40px; /* space for macOS traffic lights */
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar-logo {
  font-size: 20px;
}

.sidebar-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

@media (prefers-color-scheme: dark) {
  .sidebar-name {
    color: var(--color-text-primary-dark);
  }
}

.sidebar-nav {
  flex: 1;
  padding: 4px 8px;
}

.nav-group {
  margin-bottom: 4px;
}

.nav-group-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 8px 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-text-primary);
  text-decoration: none;
  transition: background 0.15s;
  cursor: pointer;
}

@media (prefers-color-scheme: dark) {
  .nav-item {
    color: var(--color-text-primary-dark);
  }
}

.nav-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

@media (prefers-color-scheme: dark) {
  .nav-item:hover {
    background: rgba(255, 255, 255, 0.08);
  }
}

.nav-item.active {
  background: var(--color-primary);
  color: white;
}

.nav-icon {
  font-size: 15px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
