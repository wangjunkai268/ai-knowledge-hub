/** 单条消息 */
export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
}

/** 一个对话会话 */
export interface Session {
  id: string              // 时间戳生成，如 "20260802_001"
  title: string           // 第一条用户消息截取
  messages: Message[]
  createdAt: string       // ISO
  updatedAt: string       // ISO
}
