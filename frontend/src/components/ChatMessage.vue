<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import SourceCard from './SourceCard.vue'
import type { ToolCall, StructuredMeta } from '../types/chat'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
  toolCalls?: ToolCall[]
  structured?: StructuredMeta
}>()

const htmlContent = computed(() => {
  if (props.role === 'user') return ''
  if (props.isStreaming) return '' // 流式时不用 markdown，用纯文本
  return marked.parse(props.content) as string
})

// 工具名 → 中文显示名
const TOOL_NAMES: Record<string, string> = {
  search_kb: '检索知识库',
  search_web: '联网搜索',
}
function toolName(name: string): string {
  return TOOL_NAMES[name] ?? name
}

// 意图 → 中文
const INTENT_LABELS: Record<string, string> = {
  kb_query: '知识库查询',
  web_query: '联网搜索',
  chat: '通用对话',
  mixed: '综合检索',
}
function intentLabel(intent?: string): string {
  if (!intent) return '未知'
  return INTENT_LABELS[intent] ?? intent
}

// 置信度颜色
function confidenceColor(c?: number): string {
  if (c == null) return 'text-gray-400'
  if (c >= 0.8) return 'text-emerald-600 dark:text-emerald-400'
  if (c >= 0.5) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-500'
}
</script>

<template>
  <div class="flex gap-3" :class="role === 'user' ? 'justify-end' : ''">
    <!-- AI 头像 -->
    <div v-if="role === 'assistant'" class="shrink-0 w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm">
      AI
    </div>

    <div class="max-w-[75%]">
      <!-- 消息气泡 -->
      <div
        :class="role === 'user'
          ? 'bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-2.5'
          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-bl-md px-4 py-2.5'"
      >
        <!-- 工具调用过程（AI 消息） -->
        <div v-if="role === 'assistant' && toolCalls?.length" class="mb-2 flex flex-col gap-1">
          <span
            v-for="tc in toolCalls"
            :key="tc.name"
            class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400"
          >
            <svg
              v-if="tc.status === 'calling'"
              class="w-3.5 h-3.5 animate-spin"
              fill="none" viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <svg v-else class="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            {{ tc.status === 'calling' ? '正在' : '已' }}{{ toolName(tc.name) }}
          </span>
        </div>

        <!-- 用户消息 -->
        <p v-if="role === 'user'" class="text-sm whitespace-pre-wrap">{{ content }}</p>

        <!-- AI 消息 - 流式：纯文本 -->
        <p v-else-if="isStreaming" class="text-sm whitespace-pre-wrap">
          {{ content }}
          <span v-if="!content" class="inline-flex gap-1 align-middle">
            <span class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 0ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 150ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 300ms" />
          </span>
          <span v-if="content" class="inline-block w-0.5 h-4 bg-indigo-500 animate-pulse align-middle ml-0.5" />
        </p>

        <!-- AI 消息 - 完成：Markdown 渲染 -->
        <div v-else class="markdown-body text-sm" v-html="htmlContent" />
      </div>

      <!-- 来源引用 -->
      <SourceCard v-if="sources && sources.length && !isStreaming" :sources="sources" />

      <!-- 智能分析卡片（Structured Output） -->
      <div
        v-if="structured && !isStreaming"
        class="mt-2 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 bg-gray-50/70 dark:bg-gray-800/50"
      >
        <p class="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">智能分析</p>
        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div class="flex justify-between">
            <span class="text-gray-400 dark:text-gray-500">意图</span>
            <span class="font-medium text-gray-700 dark:text-gray-200">{{ intentLabel(structured.intent) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-400 dark:text-gray-500">置信度</span>
            <span class="font-medium" :class="confidenceColor(structured.confidence)">
              {{ structured.confidence != null ? Math.round(structured.confidence * 100) + '%' : '—' }}
            </span>
          </div>
          <div v-if="structured.kb_id" class="flex justify-between">
            <span class="text-gray-400 dark:text-gray-500">来源库</span>
            <span class="font-medium text-gray-700 dark:text-gray-200 truncate ml-2">{{ structured.kb_id }}</span>
          </div>
          <div v-if="structured.tools?.length" class="flex justify-between">
            <span class="text-gray-400 dark:text-gray-500">工具</span>
            <span class="font-medium text-indigo-600 dark:text-indigo-400">
              {{ structured.tools.map(toolName).join('、') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 用户头像 -->
    <div v-if="role === 'user'" class="shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-sm">
      U
    </div>
  </div>
</template>
