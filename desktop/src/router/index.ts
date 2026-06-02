import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/items/:type',
      name: 'items',
      component: () => import('../views/ItemsView.vue'),
      props: true,
    },
    {
      path: '/items/detail/:id',
      name: 'item-detail',
      component: () => import('../views/ItemDetailView.vue'),
      props: true,
    },
    {
      path: '/items',
      name: 'items-all',
      component: () => import('../views/ItemsView.vue'),
      props: { type: '' },
    },
    {
      path: '/tags',
      name: 'tags',
      component: () => import('../views/TagsView.vue'),
    },
    {
      path: '/mining',
      name: 'mining',
      component: () => import('../views/MiningView.vue'),
    },
    {
      path: '/graph',
      name: 'graph',
      component: () => import('../views/GraphView.vue'),
    },
    {
      path: '/topics',
      name: 'topics',
      component: () => import('../views/TopicsView.vue'),
    },
    {
      path: '/timeline',
      name: 'timeline',
      component: () => import('../views/TimelineView.vue'),
    },
    {
      path: '/recommendations',
      name: 'recommendations',
      component: () => import('../views/RecommendationsView.vue'),
    },
    {
      path: '/wiki',
      name: 'wiki',
      component: () => import('../views/WikiView.vue'),
    },
    {
      path: '/rag',
      name: 'rag',
      component: () => import('../views/RagView.vue'),
    },
    {
      path: '/backup',
      name: 'backup',
      component: () => import('../views/BackupView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
  ],
})

export default router
