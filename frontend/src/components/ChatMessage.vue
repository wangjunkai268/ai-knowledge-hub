<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import SourceCard from './SourceCard.vue'
import type { ToolCall } from '../types/chat'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
  toolCalls?: ToolCall[]
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
    </div>

    <!-- 用户头像 -->
    <div v-if="role === 'user'" class="shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-sm">
      U
    </div>
  </div>
</template>
