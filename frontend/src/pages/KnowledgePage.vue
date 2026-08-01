<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { uploadDocument, deleteDocument, getKnowledgeStats } from '../api'
import FileUpload from '../components/FileUpload.vue'

interface DocFile {
  id: string
  name: string
  type: string
  format_size: string
  uploaded_at: string
}

const docs = ref<DocFile[]>([])
const stats = ref({ document_count: 0, chunk_count: 0 })
const deleting = ref<string | null>(null)

// 上传任务队列 — 每个文件独立一条进度
interface UploadTask {
  id: number
  fileName: string
  progress: number
  status: 'uploading' | 'done' | 'error'
}
const uploadTasks = ref<UploadTask[]>([])
let uploadIdCounter = 0

// ─── Toast ──────────────────────────────
const toast = ref<{ show: boolean; type: 'success' | 'error'; message: string }>({
  show: false, type: 'success', message: '',
})
function showToast(type: 'success' | 'error', message: string) {
  toast.value = { show: true, type, message }
  setTimeout(() => { toast.value.show = false }, 3000)
}

// ─── 确认弹窗 ───────────────────────────
const confirmModal = ref<{
  show: boolean
  title: string
  message: string
  doc: DocFile | null
  resolve: ((v: boolean) => void) | null
}>({ show: false, title: '', message: '', doc: null, resolve: null })

function showConfirm(title: string, message: string, doc: DocFile): Promise<boolean> {
  return new Promise((resolve) => {
    confirmModal.value = { show: true, title, message, doc, resolve }
  })
}
function onConfirm(result: boolean) {
  confirmModal.value.resolve?.(result)
  confirmModal.value = { show: false, title: '', message: '', doc: null, resolve: null }
}

// ─── 数据加载（stats 接口已含文档列表，一次请求搞定） ──
async function loadDocs() {
  try {
    const s = await getKnowledgeStats()
    docs.value = s.data.documents
    stats.value = s.data
  } catch (e) {
    console.error('加载文档失败:', e)
  }
}

// ─── 上传（定时器驱动进度条 0→90% + API 完成跳 100%） ──
async function handleUpload(file: File) {
  const id = ++uploadIdCounter
  uploadTasks.value.push({
    id,
    fileName: file.name,
    progress: 0,
    status: 'uploading',
  })
  // 从响应式数组中取出引用，后续通过它修改才能触发 Vue 更新
  const task = uploadTasks.value.find(t => t.id === id)!

  // 定时器：每 150ms 涨 3~7%，到 90% 停止等待 API
  const timer = setInterval(() => {
    if (task.status !== 'uploading') return
    const step = 3 + Math.floor(Math.random() * 5)
    task.progress = Math.min(90, task.progress + step)
  }, 150)

  try {
    const uploadRes = await uploadDocument(file)  // 后端已处理索引，返回含 stats

    clearInterval(timer)
    uploadTasks.value = uploadTasks.value.filter(t => t.id !== id)

    // 本地插入当前文件 + 用服务端 stats（只反映已完成的文件）
    const d = uploadRes.data
    docs.value.unshift({
      id: d.id,
      name: d.name,
      type: file.name.includes('.') ? '.' + file.name.split('.').pop()! : '',
      format_size: formatSize(d.size),
      uploaded_at: d.uploaded_at,
    })
    stats.value = uploadRes.data

    showToast('success', `"${file.name}" 上传成功，知识库已更新`)
  } catch (e: any) {
    clearInterval(timer)
    task.status = 'error'
    await new Promise(r => setTimeout(r, 800))
    uploadTasks.value = uploadTasks.value.filter(t => t.id !== id)
    showToast('error', '上传失败: ' + (e.response?.data?.detail || e.message))
  }
}

// ─── 删除 ─────────────────────────────
async function handleDelete(doc: DocFile) {
  const ok = await showConfirm(
    '确认删除',
    `将删除 "${doc.name}"，删除后知识库将重建。`,
    doc,
  )
  if (!ok) return

  deleting.value = doc.id
  try {
    await deleteDocument(doc.id)
    const s = await getKnowledgeStats()
    stats.value = s.data
    docs.value = docs.value.filter(d => d.id !== doc.id)
    showToast('success', `"${doc.name}" 已删除，知识库已重建`)
  } catch (e: any) {
    showToast('error', '删除失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    deleting.value = null
  }
}

function formatSize(bytes: number): string {
  for (const unit of ['B', 'KB', 'MB']) {
    if (bytes < 1024) return `${bytes.toFixed(1)} ${unit}`
    bytes /= 1024
  }
  return `${bytes.toFixed(1)} GB`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

onMounted(loadDocs)
</script>

<template>
  <div class="flex flex-col h-full overflow-y-auto p-6">
    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100 mb-6">知识库管理</h2>

    <!-- ═══ Toast ═══ -->
    <Transition name="toast">
      <div
        v-if="toast.show"
        class="fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2"
        :class="toast.type === 'success'
          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
          : 'bg-red-50 text-red-700 border border-red-200'"
      >
        <svg v-if="toast.type==='success'" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
        <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        {{ toast.message }}
      </div>
    </Transition>

    <!-- ═══ 确认弹窗 ═══ -->
    <Transition name="modal">
      <div v-if="confirmModal.show" class="fixed inset-0 z-40 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/30" @click="onConfirm(false)" />
        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-[380px] max-w-[90vw]">
          <h3 class="text-base font-semibold text-gray-800 dark:text-gray-100 mb-2">{{ confirmModal.title }}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">{{ confirmModal.message }}</p>
          <div class="flex justify-end gap-3">
            <button @click="onConfirm(false)" class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">取消</button>
            <button @click="onConfirm(true)" class="px-4 py-2 text-sm text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors">确认删除</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ═══ 统计卡片 ═══ -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <p class="text-2xl font-bold text-indigo-600">{{ stats.document_count }}</p>
        <p class="text-sm text-gray-500">文档数量</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <p class="text-2xl font-bold text-indigo-600">{{ stats.chunk_count }}</p>
        <p class="text-sm text-gray-500">向量片段</p>
      </div>
    </div>

    <!-- ═══ 上传区 ═══ -->
    <div class="mb-6">
      <FileUpload @upload="handleUpload" />

      <!-- 上传进度条（每文件独立一条） -->
      <TransitionGroup name="progress" tag="div">
        <div
          v-for="task in uploadTasks"
          :key="task.id"
          class="mt-3 bg-white dark:bg-gray-800 border rounded-lg px-4 py-3 transition-colors"
          :class="task.status === 'error' ? 'border-red-200' : task.status === 'done' ? 'border-emerald-200' : 'border-gray-200'"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm truncate mr-2" :class="task.status === 'error' ? 'text-red-600' : 'text-gray-600'">
              {{ task.fileName }}
            </span>
            <span class="text-xs font-medium shrink-0" :class="task.status === 'error' ? 'text-red-500' : task.status === 'done' ? 'text-emerald-500' : 'text-indigo-600'">
              {{ task.status === 'error' ? '失败' : task.progress + '%' }}
            </span>
          </div>
          <div class="w-full h-2 rounded-full overflow-hidden" :class="task.status === 'error' ? 'bg-red-100' : 'bg-gray-100'">
            <div
              class="h-full rounded-full transition-[width] duration-100 ease-linear"
              :class="task.status === 'error' ? 'bg-red-400' : task.status === 'done' ? 'bg-emerald-400' : 'bg-indigo-500'"
              :style="{ width: (task.status === 'error' ? 100 : task.progress) + '%' }"
            />
          </div>
          <p class="text-xs mt-1.5" :class="task.status === 'error' ? 'text-red-400' : 'text-gray-400'">
            {{ task.status === 'error' ? '上传失败'
              : task.status === 'done' ? '完成'
              : task.progress < 60 ? '正在上传并向量化...'
              : '正在重建知识库...' }}
          </p>
        </div>
      </TransitionGroup>
    </div>

    <!-- ═══ 文档列表 ═══ -->
    <div class="flex-1">
      <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">已上传文档</h3>
      <div v-if="docs.length === 0" class="text-sm text-gray-400 dark:text-gray-500 text-center py-8">
        暂无文档，请上传
      </div>
      <TransitionGroup v-else name="doc-list" tag="div" class="space-y-2">
        <div
          v-for="doc in docs"
          :key="doc.id"
          class="flex items-center justify-between bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 transition-all duration-300"
          :class="deleting === doc.id ? 'opacity-60 scale-[0.98] border-red-200 bg-red-50/30' : ''"
        >
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-lg" :class="deleting === doc.id ? 'opacity-30' : ''">
              {{ doc.type === '.pdf' ? '📄' : '📝' }}
            </span>
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{{ doc.name }}</p>
              <p class="text-xs text-gray-400 dark:text-gray-500">{{ doc.format_size }} · {{ formatDate(doc.uploaded_at) }}</p>
            </div>
          </div>

          <!-- 删除按钮 -->
          <div class="shrink-0 ml-4 w-[72px] flex justify-end">
            <button
              v-if="deleting === doc.id"
              disabled
              class="flex items-center gap-1.5 text-xs text-red-400"
            >
              <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              删除中
            </button>
            <button
              v-else
              @click="handleDelete(doc)"
              :disabled="deleting !== null"
              class="text-xs text-red-500 hover:text-red-700 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              删除
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
/* Toast */
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-12px); }
.toast-leave-to { opacity: 0; transform: translateY(-12px); }

/* 确认弹窗 */
.modal-enter-active { transition: all 0.2s ease; }
.modal-leave-active { transition: all 0.15s ease; }
.modal-enter-from { opacity: 0; }
.modal-enter-from > div:last-child { transform: scale(0.95); }
.modal-leave-to { opacity: 0; }

/* 进度条列表 */
.progress-enter-active { transition: all 0.3s ease; }
.progress-leave-active { transition: all 0.3s ease; }
.progress-enter-from { opacity: 0; transform: translateY(-8px); }
.progress-leave-to { opacity: 0; transform: translateY(-8px); }

/* 文档列表 */
.doc-list-enter-active,
.doc-list-leave-active { transition: all 0.4s ease; }
.doc-list-enter-from { opacity: 0; transform: translateY(-10px); }
.doc-list-leave-to { opacity: 0; transform: translateX(20px) scale(0.95); }
.doc-list-move { transition: transform 0.3s ease; }
</style>
