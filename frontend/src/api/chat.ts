/** 对话流式 API（SSE） */

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export function sendMessage(
  message: string,
  onChunk: (chunk: any) => void,
  onDone: () => void,
  onError: (err: string) => void,
  options?: { temperature?: number; max_tokens?: number; kb_id?: string | null; history?: ChatHistoryItem[] }
) {
  const controller = new AbortController()

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.max_tokens ?? 2048,
      kb_id: options?.kb_id ?? null,          // null = 全局检索
      history: options?.history ?? [],        // 历史对话（多轮上下文）
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
