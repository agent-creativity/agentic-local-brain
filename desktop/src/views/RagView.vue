<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ragChat, listConversations, getConversation, deleteConversation, deleteAllConversations } from '../api/search'
import type { RagConversation, RagChatResponse, RagTurn, RagSource } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const conversations = ref<RagConversation[]>([])
const currentSessionId = ref<string | null>(null)
const turns = ref<RagTurn[]>([])
const query = ref('')
const sending = ref(false)
const loading = ref(true)
const chatContainerRef = ref<HTMLElement>()

onMounted(async () => {
  try {
    conversations.value = await listConversations()
  } catch {
    // ok
  } finally {
    loading.value = false
  }
})

async function sendMessage() {
  const q = query.value.trim()
  if (!q || sending.value) return
  query.value = ''
  sending.value = true

  turns.value.push({ turn_number: turns.value.length + 1, query: q, answer: '', sources: [], created_at: new Date().toISOString() })
  await nextTick()
  scrollToBottom()

  try {
    const resp: RagChatResponse = await ragChat({
      query: q,
      session_id: currentSessionId.value || undefined,
    })
    currentSessionId.value = resp.session_id
    turns.value[turns.value.length - 1].answer = resp.answer
    turns.value[turns.value.length - 1].sources = resp.sources
    conversations.value = await listConversations()
  } catch (e: unknown) {
    turns.value[turns.value.length - 1].answer = `Error: ${e instanceof Error ? e.message : String(e)}`
  } finally {
    sending.value = false
    await nextTick()
    scrollToBottom()
  }
}

async function loadConversation(sessionId: string) {
  currentSessionId.value = sessionId
  try {
    const detail = await getConversation(sessionId)
    turns.value = detail.turns
  } catch {
    turns.value = []
  }
  await nextTick()
  scrollToBottom()
}

function newConversation() {
  currentSessionId.value = null
  turns.value = []
}

async function removeConversation(sessionId: string) {
  try {
    await deleteConversation(sessionId)
    conversations.value = conversations.value.filter((c) => c.session_id !== sessionId)
    if (currentSessionId.value === sessionId) newConversation()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

async function clearAll() {
  if (!confirm('清除所有对话？')) return
  try {
    await deleteAllConversations()
    conversations.value = []
    newConversation()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

function scrollToBottom() {
  if (chatContainerRef.value) {
    chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
  }
}

function viewSource(source: RagSource) {
  if (source.id) router.push(`/items/detail/${source.id}`)
}
</script>

<template>
  <div class="rag-layout">
    <!-- Sidebar: conversation list -->
    <aside class="conv-sidebar">
      <div class="conv-header">
        <button class="new-btn" @click="newConversation">+ 新对话</button>
        <button v-if="conversations.length" class="clear-btn" @click="clearAll">清除</button>
      </div>
      <div class="conv-list">
        <button
          v-for="conv in conversations"
          :key="conv.session_id"
          class="conv-item"
          :class="{ active: currentSessionId === conv.session_id }"
          @click="loadConversation(conv.session_id)"
        >
          <span class="conv-title">{{ conv.title || '对话 ' + conv.session_id.slice(0, 6) }}</span>
          <span class="conv-meta">{{ conv.turn_count }} 轮</span>
          <button class="conv-delete" @click.stop="removeConversation(conv.session_id)">×</button>
        </button>
      </div>
    </aside>

    <!-- Main chat area -->
    <div class="chat-area">
      <div ref="chatContainerRef" class="chat-messages">
        <div v-if="turns.length === 0" class="chat-empty">
          <div class="empty-icon">🤖</div>
          <div class="empty-text">{{ t('nav.rag') }}</div>
          <div class="empty-hint">输入问题，基于你的知识库进行增强检索</div>
        </div>

        <div v-for="turn in turns" :key="turn.turn_number" class="turn">
          <div class="msg msg-user">
            <div class="msg-content">{{ turn.query }}</div>
          </div>
          <div class="msg msg-assistant">
            <div v-if="!turn.answer && sending" class="msg-loading">思考中...</div>
            <div v-else class="msg-content">{{ turn.answer }}</div>
            <div v-if="turn.sources.length" class="msg-sources">
              <span class="sources-label">来源：</span>
              <button
                v-for="src in turn.sources"
                :key="src.id"
                class="source-chip"
                @click="viewSource(src)"
              >{{ src.title || src.id }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input-area">
        <input
          v-model="query"
          class="chat-input"
          placeholder="输入问题..."
          :disabled="sending"
          @keydown.enter="sendMessage"
        />
        <button class="send-btn" :disabled="sending || !query.trim()" @click="sendMessage">发送</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rag-layout {
  display: flex;
  height: calc(100vh - 68px);
  margin: -24px;
}

.conv-sidebar {
  width: 240px;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
@media (prefers-color-scheme: dark) { .conv-sidebar { border-right-color: var(--color-border-dark); } }

.conv-header { display: flex; gap: 8px; padding: 12px; }
.new-btn { flex: 1; padding: 6px; background: var(--color-primary); color: white; border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
.clear-btn { padding: 6px 10px; background: transparent; border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: 11px; cursor: pointer; color: var(--color-text-secondary); font-family: var(--font-sans); }
@media (prefers-color-scheme: dark) { .clear-btn { border-color: var(--color-border-dark); } }

.conv-list { flex: 1; overflow-y: auto; padding: 0 8px; }
.conv-item {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 8px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  text-align: left;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}
@media (prefers-color-scheme: dark) { .conv-item { color: var(--color-text-primary-dark); } }
.conv-item:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .conv-item:hover { background: rgba(255, 255, 255, 0.06); } }
.conv-item.active { background: var(--color-primary); color: white; }
.conv-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-meta { font-size: 10px; opacity: 0.6; flex-shrink: 0; }
.conv-delete { border: none; background: transparent; color: inherit; cursor: pointer; font-size: 14px; padding: 0 2px; opacity: 0; font-family: var(--font-sans); }
.conv-item:hover .conv-delete { opacity: 0.6; }

.chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-messages { flex: 1; overflow-y: auto; padding: 24px; }

.chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 8px; }
.empty-icon { font-size: 48px; }
.empty-text { font-size: 18px; font-weight: 600; }
.empty-hint { font-size: 13px; color: var(--color-text-secondary); }

.turn { margin-bottom: 24px; }
.msg { max-width: 80%; margin-bottom: 8px; }
.msg-user { margin-left: auto; }
.msg-assistant { margin-right: auto; }

.msg-user .msg-content {
  padding: 10px 14px;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
  font-size: 14px;
  line-height: 1.5;
}

.msg-assistant .msg-content {
  padding: 10px 14px;
  background: var(--color-surface);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  box-shadow: var(--shadow-card);
}
@media (prefers-color-scheme: dark) { .msg-assistant .msg-content { background: var(--color-surface-dark); } }

.msg-loading { padding: 10px 14px; font-size: 13px; color: var(--color-text-secondary); }

.msg-sources { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; align-items: center; }
.sources-label { font-size: 11px; color: var(--color-text-secondary); }
.source-chip {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border: none;
  border-radius: 99px;
  cursor: pointer;
  font-family: var(--font-sans);
}
@media (prefers-color-scheme: dark) { .source-chip { background: rgba(0, 122, 255, 0.2); } }
.source-chip:hover { text-decoration: underline; }

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border);
}
@media (prefers-color-scheme: dark) { .chat-input-area { border-top-color: var(--color-border-dark); } }

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-family: var(--font-sans);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
}
@media (prefers-color-scheme: dark) { .chat-input { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }
.chat-input:focus { border-color: var(--color-primary); }

.send-btn {
  padding: 10px 20px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: 14px;
  cursor: pointer;
  font-family: var(--font-sans);
}
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
