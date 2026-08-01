<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  sources: string[]
}>()

const expanded = ref(false)
const displaySources = computed(() => props.sources.slice(0, 5))
</script>

<template>
  <div class="mt-2">
    <button
      @click="expanded = !expanded"
      class="text-xs text-gray-400 hover:text-indigo-500 transition-colors flex items-center gap-1"
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      参考来源 ({{ sources.length }})
    </button>
    <div v-if="expanded" class="mt-2 flex flex-wrap gap-1.5">
      <span
        v-for="(src, i) in displaySources"
        :key="i"
        class="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-md truncate max-w-[200px]"
        :title="src"
      >
        {{ src.includes('/') ? src.split('/').pop() : src }}
      </span>
    </div>
  </div>
</template>
