<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { getGraph, getGraphStats, searchGraph } from '../api/graph'
import type { GraphData, GraphStats } from '../api/types'

use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer])

const { t } = useI18n()

const graphData = ref<GraphData | null>(null)
const graphStats = ref<GraphStats | null>(null)
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')

const typeColors: Record<string, string> = {
  person: '#FF6B6B',
  organization: '#4ECDC4',
  location: '#45B7D1',
  concept: '#96CEB4',
  technology: '#FFEAA7',
  event: '#DDA0DD',
  default: '#86868B',
}

onMounted(async () => {
  try {
    const [g, s] = await Promise.all([getGraph({ limit: 200 }), getGraphStats()])
    graphData.value = g
    graphStats.value = s
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function doSearch() {
  if (!searchQuery.value.trim()) {
    loading.value = true
    try {
      graphData.value = await getGraph({ limit: 200 })
    } finally {
      loading.value = false
    }
    return
  }
  loading.value = true
  try {
    graphData.value = await searchGraph({ query: searchQuery.value, limit: 100 })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

const chartOption = computed(() => {
  if (!graphData.value) return {}
  const categories = [...new Set(graphData.value.nodes.map((n) => n.type))]
  return {
    tooltip: { trigger: 'item', formatter: (p: any) => p.data?.name || '' },
    legend: { data: categories, top: 10, textStyle: { fontSize: 11 } },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      categories: categories.map((c) => ({ name: c })),
      data: graphData.value.nodes.map((n) => ({
        name: n.name,
        id: n.id,
        category: categories.indexOf(n.type),
        symbolSize: 20,
        itemStyle: { color: typeColors[n.type.toLowerCase()] || typeColors.default },
      })),
      links: graphData.value.links.map((l) => ({
        source: l.source,
        target: l.target,
        value: l.relation,
      })),
      label: { show: true, position: 'right', fontSize: 10 },
      lineStyle: { color: 'source', curveness: 0.1, opacity: 0.5 },
      force: { repulsion: 200, edgeLength: 120, gravity: 0.1 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    }],
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">{{ t('nav.graph') }}</h1>
      <div v-if="graphStats" class="graph-stats">
        <span>{{ graphStats.total_entities }} 实体</span>
        <span>{{ graphStats.total_relations }} 关系</span>
      </div>
    </div>

    <div class="search-bar">
      <input v-model="searchQuery" placeholder="搜索实体..." class="search-input" @keydown.enter="doSearch" />
      <button class="search-btn" @click="doSearch">{{ t('common.search') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="!graphData || graphData.nodes.length === 0" class="empty">{{ t('common.noData') }}</div>
    <div v-else class="graph-container">
      <VChart :option="chartOption" autoresize class="graph-chart" />
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 100%; height: calc(100vh - 68px); display: flex; flex-direction: column; margin: -24px; padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.page-title { font-size: 24px; font-weight: 700; }
.graph-stats { display: flex; gap: 12px; font-size: 12px; color: var(--color-text-secondary); }

.search-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  outline: none;
}
@media (prefers-color-scheme: dark) { .search-input { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }
.search-input:focus { border-color: var(--color-primary); }
.search-btn { padding: 8px 16px; background: var(--color-primary); color: white; border: none; border-radius: var(--radius-md); font-size: 13px; cursor: pointer; font-family: var(--font-sans); }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.graph-container { flex: 1; min-height: 0; background: var(--color-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); overflow: hidden; }
@media (prefers-color-scheme: dark) { .graph-container { background: var(--color-surface-dark); } }
.graph-chart { width: 100%; height: 100%; }
</style>
