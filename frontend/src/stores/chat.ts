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

    /** 是否为空白新会话（无用户消息） */
    isNewSession(): boolean {
      const s = this.currentSession
      if (!s) return true
      return !s.messages.some(m => m.role === 'user')
    },

    /** 仅有用户消息的会话（历史对话列表用） */
    historySessions(state): Session[] {
      return [...state.sessions]
        .filter(s => s.messages.some(m => m.role === 'user'))
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    },
  },

  actions: {
    ensureSession() {
      if (!this.currentId || !this.sessions.find(s => s.id === this.currentId)) {
        this.newSession()
      }
    },

    newSession() {
      // 如果已有空白新会话，不重复创建
      const blank = this.sessions.find(
        s => !s.messages.some(m => m.role === 'user')
      )
      if (blank) {
        this.currentId = blank.id
        return
      }

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

      // 第一条用户消息 → 改标题（进入历史）
      if (session.title === '新对话' && msg.role === 'user') {
        session.title = makeTitle(msg.content)
      }
    },

    /** ChatPage 发消息后调用，确保标题更新 + 时间戳 + 触发响应式 */
    onUserMessage(text: string) {
      const session = this.sessions.find(s => s.id === this.currentId)
      if (!session) return
      const wasNew = session.title === '新对话'
      this.$patch((state) => {
        const s = state.sessions.find(x => x.id === this.currentId)
        if (!s) return
        s.updatedAt = new Date().toISOString()
        if (wasNew) s.title = makeTitle(text)
      })
    },
  },

  persist: {
    key: 'chat-store',
    storage: localStorage,
  },
})
