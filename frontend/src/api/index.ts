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
  options?: { temperature?: number; max_tokens?: number }
) {
  const controller = new AbortController()

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.max_tokens ?? 2048,
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

// ─── Documents ───────────────────────────────────────

export function getDocuments() {
  return api.get('/documents')
}

export function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id: string) {
  return api.delete(`/documents/${id}`)
}

// ─── Knowledge ───────────────────────────────────────

export function getKnowledgeStats() {
  return api.get('/knowledge/stats')
}

export function reloadKnowledge() {
  return api.post('/knowledge/reload')
}

// ─── Health ──────────────────────────────────────────

export function healthCheck() {
  return api.get('/health')
}
