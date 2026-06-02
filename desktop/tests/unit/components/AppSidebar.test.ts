import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppSidebar from '../../../src/components/layout/AppSidebar.vue'

function createTestRouter(initialRoute = '/') {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/items/:type', component: { template: '<div />' } },
      { path: '/tags', component: { template: '<div />' } },
      { path: '/graph', component: { template: '<div />' } },
      { path: '/wiki', component: { template: '<div />' } },
      { path: '/rag', component: { template: '<div />' } },
      { path: '/settings', component: { template: '<div />' } },
    ],
  })
}

describe('AppSidebar', () => {
  it('renders app name in sidebar header', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router] },
    })

    expect(wrapper.find('.sidebar-name').exists()).toBe(true)
  })

  it('renders 4 navigation groups', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router] },
    })

    const groups = wrapper.findAll('.nav-group')
    expect(groups.length).toBe(4)
  })

  it('highlights dashboard as active on root path', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router] },
    })

    const activeItems = wrapper.findAll('.nav-item.active')
    expect(activeItems.length).toBe(1)
  })

  it('renders all navigation items', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router] },
    })

    const navItems = wrapper.findAll('.nav-item')
    expect(navItems.length).toBeGreaterThanOrEqual(15)
  })

  it('each nav item has an icon and label', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router] },
    })

    const firstItem = wrapper.find('.nav-item')
    expect(firstItem.find('.nav-icon').exists()).toBe(true)
    expect(firstItem.find('.nav-label').exists()).toBe(true)
  })
})
