<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getWikiTree, getCategoryArticles, getTopicArticles, getArticle, getWikiStats, searchWiki } from '../api/wiki'
import type { WikiTree, WikiArticle, WikiCategory, WikiTopic, WikiStats } from '../api/types'

const { t } = useI18n()

const tree = ref<WikiTree | null>(null)
const stats = ref<WikiStats | null>(null)
const loading = ref(true)
const error = ref('')

const selectedCategory = ref<string | null>(null)
const selectedTopic = ref<string | null>(null)
const articles = ref<WikiArticle[]>([])
const loadingArticles = ref(false)

const selectedArticle = ref<WikiArticle | null>(null)
const loadingArticle = ref(false)

const searchQuery = ref('')

onMounted(async () => {
  try {
    const [t, s] = await Promise.all([getWikiTree(), getWikiStats()])
    tree.value = t
    stats.value = s
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function selectCategory(cat: WikiCategory) {
  selectedCategory.value = cat.id
  selectedTopic.value = null
  selectedArticle.value = null
  loadingArticles.value = true
  try {
    articles.value = await getCategoryArticles(cat.id, { limit: 50 })
  } catch {
    articles.value = []
  } finally {
    loadingArticles.value = false
  }
}

async function selectTopic(topic: WikiTopic) {
  selectedTopic.value = topic.id
  selectedCategory.value = null
  selectedArticle.value = null
  loadingArticles.value = true
  try {
    articles.value = await getTopicArticles(topic.id, { limit: 50 })
  } catch {
    articles.value = []
  } finally {
    loadingArticles.value = false
  }
}

async function openArticle(articleId: string) {
  loadingArticle.value = true
  try {
    selectedArticle.value = await getArticle(articleId)
  } catch {
    selectedArticle.value = null
  } finally {
    loadingArticle.value = false
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  loadingArticles.value = true
  selectedCategory.value = null
  selectedTopic.value = null
  selectedArticle.value = null
  try {
    const results = await searchWiki({ query: searchQuery.value, limit: 20 })
    articles.value = results as unknown as WikiArticle[]
  } catch {
    articles.value = []
  } finally {
    loadingArticles.value = false
  }
}
</script>

<template>
  <div class="wiki-layout">
    <!-- Left: tree navigation -->
    <aside class="wiki-nav">
      <div class="nav-search">
        <input v-model="searchQuery" :placeholder="t('common.search') + '...'" class="nav-search-input" @keydown.enter="doSearch" />
      </div>

      <div v-if="loading" class="loading-small">{{ t('common.loading') }}</div>
      <template v-else-if="tree">
        <div v-if="stats" class="wiki-stats">
          <span>{{ stats.total_articles }} 文章</span>
          <span>{{ stats.total_categories }} 分类</span>
          <span>{{ stats.total_entities }} 实体</span>
        </div>

        <div class="nav-section">
          <div class="nav-section-title">分类</div>
          <button
            v-for="cat in tree.categories"
            :key="cat.id"
            class="nav-item"
            :class="{ active: selectedCategory === cat.id }"
            @click="selectCategory(cat)"
          >
            <span class="nav-item-name">{{ cat.name }}</span>
            <span class="nav-item-count">{{ cat.article_count }}</span>
          </button>
        </div>

        <div v-if="tree.topics.length" class="nav-section">
          <div class="nav-section-title">主题</div>
          <button
            v-for="topic in tree.topics"
            :key="topic.id"
            class="nav-item"
            :class="{ active: selectedTopic === topic.id }"
            @click="selectTopic(topic)"
          >
            <span class="nav-item-name">{{ topic.name }}</span>
            <span class="nav-item-count">{{ topic.article_count }}</span>
          </button>
        </div>
      </template>
    </aside>

    <!-- Middle: article list -->
    <div class="wiki-list">
      <div v-if="loadingArticles" class="loading-small">{{ t('common.loading') }}</div>
      <div v-else-if="articles.length === 0 && (selectedCategory || selectedTopic)" class="empty-small">{{ t('common.noData') }}</div>
      <div v-else-if="articles.length === 0" class="empty-small">选择分类或主题查看文章</div>
      <button
        v-for="article in articles"
        :key="article.id"
        class="article-item"
        :class="{ active: selectedArticle?.id === article.id }"
        @click="openArticle(article.id)"
      >
        {{ article.title }}
      </button>
    </div>

    <!-- Right: article content -->
    <div class="wiki-content">
      <div v-if="loadingArticle" class="loading-small">{{ t('common.loading') }}</div>
      <div v-else-if="!selectedArticle" class="empty-small">选择文章查看内容</div>
      <template v-else>
        <h2 class="article-title">{{ selectedArticle.title }}</h2>
        <div v-if="selectedArticle.entities?.length" class="article-entities">
          <span v-for="entity in selectedArticle.entities" :key="entity.id" class="entity-chip">
            <span class="entity-type">{{ entity.type }}</span>
            {{ entity.name }}
          </span>
        </div>
        <div class="article-body" v-text="selectedArticle.content" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.wiki-layout {
  display: flex;
  height: calc(100vh - 68px);
  margin: -24px;
}

.wiki-nav {
  width: 220px;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 12px;
}
@media (prefers-color-scheme: dark) { .wiki-nav { border-right-color: var(--color-border-dark); } }

.nav-search { margin-bottom: 12px; }
.nav-search-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-family: var(--font-sans);
  background: transparent;
  color: var(--color-text-primary);
  outline: none;
}
@media (prefers-color-scheme: dark) { .nav-search-input { border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }
.nav-search-input:focus { border-color: var(--color-primary); }

.wiki-stats { display: flex; gap: 8px; font-size: 11px; color: var(--color-text-secondary); margin-bottom: 12px; flex-wrap: wrap; }

.nav-section { margin-bottom: 16px; }
.nav-section-title { font-size: 11px; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.nav-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 6px 8px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  text-align: left;
}
@media (prefers-color-scheme: dark) { .nav-item { color: var(--color-text-primary-dark); } }
.nav-item:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .nav-item:hover { background: rgba(255, 255, 255, 0.06); } }
.nav-item.active { background: var(--color-primary); color: white; }
.nav-item-count { font-size: 10px; opacity: 0.6; }

.wiki-list {
  width: 260px;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 8px;
}
@media (prefers-color-scheme: dark) { .wiki-list { border-right-color: var(--color-border-dark); } }

.article-item {
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  text-align: left;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}
@media (prefers-color-scheme: dark) { .article-item { color: var(--color-text-primary-dark); } }
.article-item:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .article-item:hover { background: rgba(255, 255, 255, 0.06); } }
.article-item.active { background: var(--color-primary); color: white; }

.wiki-content { flex: 1; overflow-y: auto; padding: 24px; }

.article-title { font-size: 22px; font-weight: 700; margin-bottom: 12px; }
.article-entities { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.entity-chip {
  font-size: 11px;
  padding: 3px 10px;
  background: var(--color-surface);
  border-radius: 99px;
  box-shadow: var(--shadow-card);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
@media (prefers-color-scheme: dark) { .entity-chip { background: var(--color-surface-dark); } }
.entity-type { font-size: 9px; padding: 1px 4px; background: var(--color-primary-light); color: var(--color-primary); border-radius: var(--radius-sm); text-transform: uppercase; }
@media (prefers-color-scheme: dark) { .entity-type { background: rgba(0, 122, 255, 0.2); } }

.article-body { font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-wrap: break-word; }

.loading-small, .empty-small { padding: 24px; text-align: center; font-size: 13px; color: var(--color-text-secondary); }
</style>
