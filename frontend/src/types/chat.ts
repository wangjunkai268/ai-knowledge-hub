/** 工具调用记录 */
export interface ToolCall {
  name: string
  status: 'calling' | 'done'
}

/** 单条消息 */
export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  isStreaming?: boolean
  toolCalls?: ToolCall[]
}

/** 一个对话会话 */
export interface Session {
  id: string              // 时间戳生成，如 "20260802_001"
  title: string           // 第一条用户消息截取
  messages: Message[]
  createdAt: string       // ISO
  updatedAt: string       // ISO
}
