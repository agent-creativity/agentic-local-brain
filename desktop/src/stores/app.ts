import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const locale = ref<'en' | 'zh'>('zh')
  const sidebarCollapsed = ref(false)
  const serverStatus = ref<'starting' | 'running' | 'stopped' | 'error'>('starting')
  const serverPort = ref(8765)

  const apiBaseUrl = computed(() => `http://localhost:${serverPort.value}/api`)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setLocale(l: 'en' | 'zh') {
    locale.value = l
  }

  function setServerStatus(status: 'starting' | 'running' | 'stopped' | 'error') {
    serverStatus.value = status
  }

  return {
    locale,
    sidebarCollapsed,
    serverStatus,
    serverPort,
    apiBaseUrl,
    toggleSidebar,
    setLocale,
    setServerStatus,
  }
})
