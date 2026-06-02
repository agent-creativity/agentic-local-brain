import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppStore } from '../../../src/stores/app'

describe('App Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with default state', () => {
    const store = useAppStore()
    expect(store.locale).toBe('zh')
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.serverStatus).toBe('starting')
    expect(store.serverPort).toBe(11201)
  })

  it('computes apiBaseUrl from serverPort', () => {
    const store = useAppStore()
    expect(store.apiBaseUrl).toBe('http://localhost:11201/api')
  })

  it('toggleSidebar flips collapsed state', () => {
    const store = useAppStore()
    expect(store.sidebarCollapsed).toBe(false)

    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(true)

    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(false)
  })

  it('setLocale changes locale', () => {
    const store = useAppStore()
    expect(store.locale).toBe('zh')

    store.setLocale('en')
    expect(store.locale).toBe('en')

    store.setLocale('zh')
    expect(store.locale).toBe('zh')
  })

  it('setServerStatus updates status', () => {
    const store = useAppStore()

    store.setServerStatus('running')
    expect(store.serverStatus).toBe('running')

    store.setServerStatus('error')
    expect(store.serverStatus).toBe('error')

    store.setServerStatus('stopped')
    expect(store.serverStatus).toBe('stopped')
  })

  it('apiBaseUrl updates when serverPort changes', () => {
    const store = useAppStore()
    store.serverPort = 9000
    expect(store.apiBaseUrl).toBe('http://localhost:9000/api')
  })
})
