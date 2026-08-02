import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ─── Chat ────────────────────────────────────────────

export function sendMessage(
  message: string,
  onChunk: (chunk: any) => void,
  onDone: () => void,
  onError: (err: string) => void,
  options?: { temperature?: number; max_tokens?: number; kb_id?: string | null }
) {
  const controller = new AbortController()

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.max_tokens ?? 2048,
      kb_id: options?.kb_id ?? null,   // null = 全局检索
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error('请求失败')
      const reader = response.body?.getReader()
      if (!reader) throw new Error('不支持流式读取')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'done') {
                onDone()
              } else if (data.type === 'error') {
                onError(data.content)
              } else {
                onChunk(data)
              }
            } catch { /* 解析失败跳过 */ }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err.message)
    })

  return controller
}

// ─── Knowledge Bases ─────────────────────────────────

export interface KnowledgeBase {
  id: string
  name: string
  document_count: number
  documents: any[]
}

export function getKbs() {
  return api.get('/kbs')
}

export function createKb(name: string) {
  return api.post('/kbs', { name })
}

export function deleteKb(id: string) {
  return api.delete(`/kbs/${id}`)
}

// ─── Documents ───────────────────────────────────────

export function getDocuments(kbId?: string | null) {
  return api.get('/documents', { params: { kb_id: kbId ?? undefined } })
}

export function uploadDocument(file: File, kbId?: string | null) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    params: { kb_id: kbId ?? undefined },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id: string, kbId?: string | null) {
  return api.delete(`/documents/${id}`, { params: { kb_id: kbId ?? undefined } })
}

// ─── Knowledge ───────────────────────────────────────

export function getKnowledgeStats(kbId?: string | null) {
  return api.get('/knowledge/stats', { params: { kb_id: kbId ?? undefined } })
}

export function reloadKnowledge() {
  return api.post('/knowledge/reload')
}

// ─── Health ──────────────────────────────────────────

export function healthCheck() {
  return api.get('/health')
}
