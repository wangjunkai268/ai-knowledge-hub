import { defineStore } from 'pinia'
import type { Message, Session } from '../types/chat'

const MAX_SESSIONS = 50

function generateId(): string {
  const now = new Date()
  const ts = now.toISOString().replace(/[-:T]/g, '').slice(0, 15)
  return ts + '_' + Math.random().toString(36).slice(2, 6)
}

function makeTitle(text: string): string {
  return text.slice(0, 30).replace(/\n/g, ' ')
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [] as Session[],
    currentId: null as string | null,
  }),

  getters: {
    currentSession(state): Session | undefined {
      return state.sessions.find(s => s.id === state.currentId)
    },

    messages(state): Message[] {
      const s = state.sessions.find(s => s.id === state.currentId)
      return s?.messages ?? []
    },

    sortedSessions(state): Session[] {
      return [...state.sessions].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      )
    },
  },

  actions: {
    ensureSession() {
      if (!this.currentId || !this.sessions.find(s => s.id === this.currentId)) {
        this.newSession()
      }
    },

    newSession() {
      const id = generateId()
      this.sessions.push({
        id,
        title: '新对话',
        messages: [{
          id: Date.now(),
          role: 'assistant' as const,
          content: '你好！我是基于知识库的智能助手。请在知识库页面先上传文档，然后向我提问。\n\n支持的文档格式：**TXT / Markdown / PDF**',
        }],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
      this.currentId = id

      // 上限保护
      if (this.sessions.length > MAX_SESSIONS) {
        this.sessions.sort(
          (a, b) => new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
        )
        this.sessions.shift()
      }
    },

    switchSession(id: string) {
      if (this.sessions.find(s => s.id === id)) {
        this.currentId = id
      }
    },

    deleteSession(id: string) {
      const idx = this.sessions.findIndex(s => s.id === id)
      if (idx === -1) return
      this.sessions.splice(idx, 1)

      // 如果删的是当前会话，切到相邻
      if (this.currentId === id) {
        if (this.sessions.length > 0) {
          this.currentId = this.sessions[Math.min(idx, this.sessions.length - 1)].id
        } else {
          this.newSession()
        }
      }
    },

    addMessage(msg: Message) {
      this.ensureSession()
      const session = this.sessions.find(s => s.id === this.currentId)
      if (!session) return

      session.messages.push(msg)
      session.updatedAt = new Date().toISOString()

      // 用第一条用户消息做标题
      if (session.title === '新对话' && msg.role === 'user') {
        session.title = makeTitle(msg.content)
      }
    },
  },

  persist: {
    key: 'chat-store',
    storage: localStorage,
  },
})
