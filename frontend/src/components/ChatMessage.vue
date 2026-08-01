<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import SourceCard from './SourceCard.vue'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
}>()

const htmlContent = computed(() => {
  if (props.role === 'user') return ''
  if (props.isStreaming) return '' // 流式时不用 markdown，用纯文本
  return marked.parse(props.content) as string
})
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
