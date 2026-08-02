<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useThemeStore } from '../stores/theme'
import { useKbStore } from '../stores/kb'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const theme = useThemeStore()
const kbStore = useKbStore()

const creatingKb = ref(false)
const newKbName = ref('')

// 新对话是否高亮：当前是空白会话且在聊天页
const isNewActive = computed(() => chatStore.isNewSession && route.name === 'chat')

function handleNewChat() {
  chatStore.newSession()
  router.push('/')
}

function handleSelectSession(id: string) {
  chatStore.switchSession(id)
  if (route.name !== 'chat') {
    router.push('/')
  }
}

function handleDeleteSession(id: string, e: Event) {
  e.stopPropagation()
  chatStore.deleteSession(id)
}

function isCurrent(id: string): boolean {
  return chatStore.currentId === id && route.name === 'chat'
}

// ─── 知识库 ─────────────────────────────
async function handleCreateKb() {
  const name = newKbName.value.trim()
  if (!name) return
  await kbStore.create(name)
  newKbName.value = ''
  creatingKb.value = false
}

function handleSelectKb(id: string | null) {
  kbStore.switch(id)
}

async function handleDeleteKb(id: string, e: Event) {
  e.stopPropagation()
  if (!confirm('确定删除该知识库？其所有文档和索引将被移除。')) return
  await kbStore.remove(id)
}

onMounted(() => {
  kbStore.load()
})
</script>

<template>
  <aside class="w-56 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col shrink-0 transition-colors">
    <!-- Logo -->
    <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
      <h1 class="text-base font-bold text-indigo-600 dark:text-indigo-400">AI Knowledge Hub</h1>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">智能知识库管理平台</p>
    </div>

    <!-- 新对话 — 导航项样式 -->
    <div class="px-3 py-2">
      <button
        @click="handleNewChat"
        class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="isNewActive
          ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
      >
        <span class="text-base">💬</span>
        新对话
      </button>
    </div>

    <!-- 导航 -->
    <div class="px-3 py-1">
      <router-link
        to="/knowledge"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="route.name === 'knowledge'
          ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
      >
        <span class="text-base">📚</span>
        知识库
      </router-link>

      <!-- 知识库列表 -->
      <div class="mt-1 space-y-0.5">
        <button
          @click="handleSelectKb(null)"
          class="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-colors"
          :class="kbStore.currentKbId === null
            ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
            : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <span>🌐</span>
          <span class="truncate">全部知识库</span>
        </button>

        <div
          v-for="kb in kbStore.kbs"
          :key="kb.id"
          class="group flex items-center justify-between px-3 py-1.5 rounded-lg cursor-pointer text-xs transition-colors"
          :class="kbStore.currentKbId === kb.id
            ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
          @click="handleSelectKb(kb.id)"
        >
          <span class="flex items-center gap-2 min-w-0">
            <span>🗂</span>
            <span class="truncate">{{ kb.name }}</span>
            <span class="text-[10px] text-gray-400 shrink-0">{{ kb.document_count }}</span>
          </span>
          <button
            v-if="kb.id !== 'kb_default'"
            @click="(e) => handleDeleteKb(kb.id, e)"
            class="shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-400 hover:text-red-500"
            title="删除知识库"
          >
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- 新建知识库 -->
        <div v-if="creatingKb" class="px-1 pt-1">
          <div class="flex gap-1">
            <input
              v-model="newKbName"
              @keydown.enter="handleCreateKb"
              placeholder="知识库名称"
              class="flex-1 min-w-0 px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-indigo-400"
            />
            <button
              @click="handleCreateKb"
              class="px-2 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >确定</button>
          </div>
        </div>
        <button
          v-else
          @click="creatingKb = true"
          class="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-indigo-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span>＋</span>
          新建知识库
        </button>
      </div>
    </div>

    <!-- 历史对话 -->
    <div class="flex-1 flex flex-col min-h-0 mt-2">
      <p class="px-5 py-2 text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">
        历史对话
      </p>
      <div class="flex-1 overflow-y-auto px-2 space-y-0.5">
        <div
          v-for="s in chatStore.historySessions"
          :key="s.id"
          @click="handleSelectSession(s.id)"
          class="group flex items-center justify-between px-3 py-1.5 rounded-lg cursor-pointer text-sm transition-colors"
          :class="isCurrent(s.id)
            ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <span class="truncate flex-1">{{ s.title }}</span>
          <button
            @click="(e) => handleDeleteSession(s.id, e)"
            class="shrink-0 ml-1 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-400 hover:text-red-500 transition-all"
            title="删除对话"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- 空状态 -->
        <div v-if="chatStore.historySessions.length === 0" class="text-xs text-gray-400 dark:text-gray-500 text-center py-6 px-3">
          暂无对话记录
        </div>
      </div>
    </div>

    <!-- 底部固定：暗色 + 设置 -->
    <div class="border-t border-gray-200 dark:border-gray-700 px-3 py-3 space-y-1">
      <!-- 暗色模式 -->
      <button
        @click="theme.toggle()"
        class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <span class="flex items-center gap-2">
          <span class="text-base">{{ theme.isDark ? '🌙' : '☀️' }}</span>
          暗色模式
        </span>
        <!-- 开关 -->
        <span
          class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors"
          :class="theme.isDark ? 'bg-indigo-600' : 'bg-gray-300'"
        >
          <span
            class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform"
            :class="theme.isDark ? 'translate-x-4' : 'translate-x-0.5'"
          />
        </span>
      </button>

      <!-- 设置 -->
      <router-link
        to="/settings"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="route.name === 'settings'
          ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
      >
        <span class="text-base">⚙️</span>
        设置
      </router-link>
    </div>

    <!-- Footer -->
    <div class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400 dark:text-gray-500 text-center">
      Powered by DeepSeek + RAG
    </div>
  </aside>
</template>
