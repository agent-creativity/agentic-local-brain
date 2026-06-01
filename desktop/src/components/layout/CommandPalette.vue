<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const router = useRouter()
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement>()

interface CommandItem {
  id: string
  label: string
  icon: string
  action: () => void
}

const commands: CommandItem[] = [
  { id: 'dashboard', label: 'nav.dashboard', icon: '🏠', action: () => navigate('/') },
  { id: 'note', label: 'nav.note', icon: '📝', action: () => navigate('/items/note') },
  { id: 'bookmark', label: 'nav.bookmark', icon: '🔖', action: () => navigate('/items/bookmark') },
  { id: 'webpage', label: 'nav.webpage', icon: '🌐', action: () => navigate('/items/webpage') },
  { id: 'paper', label: 'nav.paper', icon: '📄', action: () => navigate('/items/paper') },
  { id: 'email', label: 'nav.email', icon: '✉️', action: () => navigate('/items/email') },
  { id: 'file', label: 'nav.file', icon: '📁', action: () => navigate('/items/file') },
  { id: 'tags', label: 'nav.tags', icon: '🏷️', action: () => navigate('/tags') },
  { id: 'graph', label: 'nav.graph', icon: '🕸️', action: () => navigate('/graph') },
  { id: 'topics', label: 'nav.topics', icon: '📊', action: () => navigate('/topics') },
  { id: 'timeline', label: 'nav.timeline', icon: '📅', action: () => navigate('/timeline') },
  { id: 'recommendations', label: 'nav.recommendations', icon: '💡', action: () => navigate('/recommendations') },
  { id: 'wiki', label: 'nav.wiki', icon: '📚', action: () => navigate('/wiki') },
  { id: 'rag', label: 'nav.rag', icon: '🤖', action: () => navigate('/rag') },
  { id: 'backup', label: 'nav.backup', icon: '💾', action: () => navigate('/backup') },
  { id: 'settings', label: 'nav.settings', icon: '⚙️', action: () => navigate('/settings') },
]

const filteredCommands = ref<CommandItem[]>(commands)

function navigate(path: string) {
  router.push(path)
  emit('close')
}

watch(query, (q) => {
  const lower = q.toLowerCase()
  filteredCommands.value = commands.filter(
    (c) => c.id.includes(lower) || t(c.label).toLowerCase().includes(lower)
  )
  selectedIndex.value = 0
})

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    query.value = ''
    selectedIndex.value = 0
    filteredCommands.value = commands
    requestAnimationFrame(() => inputRef.value?.focus())
  }
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCommands.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    filteredCommands.value[selectedIndex.value]?.action()
  } else if (e.key === 'Escape') {
    emit('close')
  }
}

</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="palette-overlay" @click.self="emit('close')">
      <div class="palette" @keydown="onKeydown">
        <div class="palette-input-wrap">
          <span class="palette-search-icon">🔍</span>
          <input
            ref="inputRef"
            v-model="query"
            class="palette-input"
            :placeholder="t('common.search') + '...'"
            autocomplete="off"
            spellcheck="false"
          />
        </div>
        <div class="palette-list">
          <button
            v-for="(cmd, i) in filteredCommands"
            :key="cmd.id"
            class="palette-item"
            :class="{ selected: i === selectedIndex }"
            @click="cmd.action()"
            @mouseenter="selectedIndex = i"
          >
            <span class="palette-item-icon">{{ cmd.icon }}</span>
            <span class="palette-item-label">{{ t(cmd.label) }}</span>
          </button>
          <div v-if="filteredCommands.length === 0" class="palette-empty">
            {{ t('items.noItemsFound') }}
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: center;
  padding-top: 120px;
}

@media (prefers-color-scheme: dark) {
  .palette-overlay {
    background: rgba(0, 0, 0, 0.5);
  }
}

.palette {
  width: 520px;
  max-height: 420px;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (prefers-color-scheme: dark) {
  .palette {
    background: var(--color-surface-dark);
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  }
}

.palette-input-wrap {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  gap: 10px;
}

@media (prefers-color-scheme: dark) {
  .palette-input-wrap {
    border-bottom-color: var(--color-border-dark);
  }
}

.palette-search-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.palette-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

@media (prefers-color-scheme: dark) {
  .palette-input {
    color: var(--color-text-primary-dark);
  }
}

.palette-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-primary);
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  font-family: var(--font-sans);
}

@media (prefers-color-scheme: dark) {
  .palette-item {
    color: var(--color-text-primary-dark);
  }
}

.palette-item.selected {
  background: var(--color-primary);
  color: white;
}

.palette-item-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.palette-empty {
  padding: 24px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
}
</style>
