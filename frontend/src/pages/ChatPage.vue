<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { sendMessage } from '../api'
import { useChatStore } from '../stores/chat'
import { useKbStore } from '../stores/kb'
import type { Message } from '../types/chat'
import ChatMessage from '../components/ChatMessage.vue'

const chatStore = useChatStore()
const kbStore = useKbStore()
const input = ref('')
const loading = ref(false)
const chatRef = ref<HTMLDivElement>()

let msgId = 0

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function handleSend() {
  const text = input.value.trim()
  if (!text || loading.value) return

  chatStore.ensureSession()
  const msgs = chatStore.currentSession!.messages

  // 用户消息
  const userMsg: Message = { id: ++msgId, role: 'user', content: text }
  msgs.push(userMsg)
  input.value = ''
  scrollToBottom()

  // AI 消息占位
  const aiMsg: Message = { id: ++msgId, role: 'assistant', content: '', isStreaming: true }
  msgs.push(aiMsg)
  const aiIndex = msgs.length - 1
  loading.value = true
  scrollToBottom()

  // 第一条用户消息 → 进入历史
  chatStore.onUserMessage(text)

  let buffer = ''
  let cancelled = false

  const tempSettings = JSON.parse(localStorage.getItem('ai-settings') || '{}')

  sendMessage(
    text,
    (chunk) => {
      if (chunk.type === 'text') {
        buffer += chunk.content
      } else if (chunk.type === 'sources') {
        msgs[aiIndex].sources = chunk.sources
      } else if (chunk.type === 'tool') {
        // 工具调用过程：calling → 记录进行中；done → 标记完成
        if (!msgs[aiIndex].toolCalls) msgs[aiIndex].toolCalls = []
        if (chunk.status === 'calling') {
          msgs[aiIndex].toolCalls.push({ name: chunk.name, status: 'calling' })
          scrollToBottom()
        } else {
          const tc = msgs[aiIndex].toolCalls!.find(t => t.name === chunk.name)
          if (tc) tc.status = 'done'
        }
      } else if (chunk.type === 'structured') {
        // 结构化意图元数据
        msgs[aiIndex].structured = chunk.data
      }
    },
    () => { loading.value = false },
    (err) => {
      cancelled = true
      msgs[aiIndex].content = buffer + `\n\n出错了: ${err}`
      msgs[aiIndex].isStreaming = false
      loading.value = false
      buffer = ''
    },
    {
      temperature: tempSettings.temperature,
      max_tokens: tempSettings.max_tokens,
      kb_id: kbStore.currentKbId,   // null = 全局检索
    }
  )

  // 打字机循环
  while (!cancelled) {
    if (buffer.length > 0) {
      const take = buffer.charCodeAt(0) > 127 ? 1 : Math.min(3, buffer.length)
      msgs[aiIndex].content += buffer.slice(0, take)
      buffer = buffer.slice(take)
      scrollToBottom()
    }
    if (buffer.length === 0 && !loading.value) break
    await sleep(30)
  }

  msgs[aiIndex].content += buffer
  msgs[aiIndex].isStreaming = false
  scrollToBottom()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

onMounted(() => {
  chatStore.ensureSession()
  kbStore.load()
})

watch(() => chatStore.currentId, () => {
  scrollToBottom()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 顶部当前知识库 -->
    <div class="shrink-0 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 text-xs text-gray-500 dark:text-gray-400">
      检索范围：
      <span class="font-medium text-indigo-600 dark:text-indigo-400">
        {{ kbStore.currentKb?.name ?? '全部知识库' }}
      </span>
    </div>

    <!-- 消息列表 -->
    <div ref="chatRef" class="chat-scroll-container flex-1 overflow-y-auto px-4 py-4 space-y-4">
      <ChatMessage
        v-for="msg in chatStore.messages"
        :key="msg.id"
        :role="msg.role"
        :content="msg.content"
        :sources="msg.sources"
        :tool-calls="msg.toolCalls"
        :structured="msg.structured"
        :is-streaming="msg.isStreaming"
      />
    </div>

    <!-- 输入区 -->
    <div class="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 transition-colors">
      <div class="flex gap-3 max-w-3xl mx-auto">
        <textarea
          v-model="input"
          @keydown="handleKeydown"
          placeholder="输入你的问题... (Enter 发送，Shift+Enter 换行)"
          rows="1"
          class="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-colors"
          :disabled="loading"
        />
        <button
          @click="handleSend"
          :disabled="!input.trim() || loading"
          class="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>
