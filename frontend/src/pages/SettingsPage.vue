<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { healthCheck } from '../api'
import { useThemeStore } from '../stores/theme'

const theme = useThemeStore()

interface Settings {
  apiKey: string
  baseUrl: string
  model: string
  temperature: number
  maxTokens: number
}

const settings = ref<Settings>({
  apiKey: '',
  baseUrl: 'https://api.deepseek.com',
  model: 'deepseek-chat',
  temperature: 0.7,
  maxTokens: 2048,
})

const saved = ref(false)
const backendStatus = ref<'checking' | 'online' | 'offline'>('checking')

function loadSettings() {
  const raw = localStorage.getItem('ai-settings')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      settings.value = { ...settings.value, ...parsed }
    } catch { /* ignore */ }
  }
}

function saveSettings() {
  localStorage.setItem('ai-settings', JSON.stringify(settings.value))
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}

async function checkBackend() {
  try {
    const res = await healthCheck()
    backendStatus.value = res.data?.agent_ready ? 'online' : 'online'
  } catch {
    backendStatus.value = 'offline'
  }
}

onMounted(() => {
  loadSettings()
  checkBackend()
})
</script>

<template>
  <div class="flex flex-col h-full overflow-y-auto p-6">
    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100 mb-6">设置</h2>

    <!-- 外观 -->
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-6">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-gray-700 dark:text-gray-200">暗色模式</span>
        <button
          @click="theme.toggle()"
          class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
          :class="theme.isDark ? 'bg-indigo-600' : 'bg-gray-300'"
        >
          <span class="text-xs absolute left-1">{{ theme.isDark ? '🌙' : '☀️' }}</span>
          <span
            class="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform"
            :class="theme.isDark ? 'translate-x-6' : 'translate-x-0.5'"
          />
        </button>
      </div>
    </div>

    <!-- 后端状态 -->
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-6">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-gray-700 dark:text-gray-200">后端服务状态</span>
        <span class="flex items-center gap-1.5 text-sm" :class="{
          'text-green-600 dark:text-green-400': backendStatus === 'online',
          'text-red-500 dark:text-red-400': backendStatus === 'offline',
          'text-yellow-500': backendStatus === 'checking',
        }">
          <span class="w-2 h-2 rounded-full" :class="{
            'bg-green-500': backendStatus === 'online',
            'bg-red-500': backendStatus === 'offline',
            'bg-yellow-500 animate-pulse': backendStatus === 'checking',
          }" />
          {{ { online: '运行中', offline: '未连接', checking: '检查中' }[backendStatus] }}
        </span>
      </div>
    </div>

    <!-- 设置表单 -->
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 space-y-5">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">API Key</label>
        <input v-model="settings.apiKey" type="password" placeholder="sk-xxxxxxxx"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">在平台获取 API Key 后在 .env 文件中配置</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">API Base URL</label>
        <input v-model="settings.baseUrl" type="text"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">模型</label>
        <select v-model="settings.model"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
          <option value="deepseek-chat">DeepSeek-Chat</option>
          <option value="deepseek-reasoner">DeepSeek-Reasoner</option>
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
          温度 ({{ settings.temperature }})
        </label>
        <input v-model.number="settings.temperature" type="range" min="0" max="2" step="0.1"
          class="w-full accent-indigo-600" />
        <div class="flex justify-between text-xs text-gray-400 dark:text-gray-500">
          <span>精确 (0)</span><span>平衡 (1)</span><span>创意 (2)</span>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
          最大 Token 数 ({{ settings.maxTokens }})
        </label>
        <input v-model.number="settings.maxTokens" type="range" min="256" max="8192" step="256"
          class="w-full accent-indigo-600" />
      </div>

      <button @click="saveSettings"
        class="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
        {{ saved ? '已保存！' : '保存设置' }}
      </button>
    </div>
  </div>
</template>
