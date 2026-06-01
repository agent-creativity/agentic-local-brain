<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppToolbar from './AppToolbar.vue'
import CommandPalette from './CommandPalette.vue'

const showCommandPalette = ref(false)

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showCommandPalette.value = !showCommandPalette.value
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-main">
      <AppToolbar @open-search="showCommandPalette = true" />
      <div class="app-content">
        <router-view />
      </div>
    </main>
    <CommandPalette :open="showCommandPalette" @close="showCommandPalette = false" />
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
