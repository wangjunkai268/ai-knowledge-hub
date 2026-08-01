import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    isDark: false,
  }),

  actions: {
    init() {
      document.documentElement.classList.toggle('dark', this.isDark)
    },

    toggle() {
      this.isDark = !this.isDark
      document.documentElement.classList.toggle('dark', this.isDark)
    },
  },

  persist: {
    key: 'theme-store',
    storage: localStorage,
    afterRestore(ctx) {
      ctx.store.init()
    },
  },
})
