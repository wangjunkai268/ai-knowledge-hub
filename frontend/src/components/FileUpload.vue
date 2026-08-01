<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  upload: [file: File]
}>()

const dragging = ref(false)
const inputRef = ref<HTMLInputElement>()

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragging.value = true
}

function onDragLeave() {
  dragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) emit('upload', file)
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) emit('upload', file)
}

function triggerInput() {
  inputRef.value?.click()
}
</script>

<template>
  <div
    class="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors"
    :class="dragging ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="triggerInput"
  >
    <input
      ref="inputRef"
      type="file"
      accept=".txt,.md,.pdf"
      class="hidden"
      @change="onFileChange"
    />
    <div class="text-3xl mb-2">📎</div>
    <p class="text-sm text-gray-600 dark:text-gray-300 font-medium">拖拽文件到此处或点击上传</p>
    <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">支持 TXT / Markdown / PDF</p>
  </div>
</template>
