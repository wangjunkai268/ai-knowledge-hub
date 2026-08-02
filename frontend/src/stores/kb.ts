import { defineStore } from 'pinia'
import { getKbs, createKb, deleteKb, type KnowledgeBase } from '../api'

export const useKbStore = defineStore('kb', {
  state: () => ({
    kbs: [] as KnowledgeBase[],
    currentKbId: null as string | null,   // null = 全部知识库（全局检索）
  }),

  getters: {
    currentKb(state): KnowledgeBase | null {
      if (!state.currentKbId) return null
      return state.kbs.find(k => k.id === state.currentKbId) ?? null
    },
  },

  actions: {
    async load() {
      const res = await getKbs()
      this.kbs = res.data.kbs
      // 当前库被删则回到全部
      if (this.currentKbId && !this.kbs.find(k => k.id === this.currentKbId)) {
        this.currentKbId = null
      }
    },

    async create(name: string) {
      await createKb(name)
      await this.load()
    },

    async remove(id: string) {
      await deleteKb(id)
      if (this.currentKbId === id) this.currentKbId = null
      await this.load()
    },

    switch(id: string | null) {
      this.currentKbId = id
    },
  },

  persist: {
    key: 'kb-store',
    storage: localStorage,
  },
})
