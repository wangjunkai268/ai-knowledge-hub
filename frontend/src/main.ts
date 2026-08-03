import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import './style.css'

import ChatPage from './pages/ChatPage.vue'
import KnowledgePage from './pages/KnowledgePage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: ChatPage },
    { path: '/knowledge', name: 'knowledge', component: KnowledgePage },
    { path: '/settings', name: 'settings', component: SettingsPage },
  ],
})

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

// 路由守卫：负责从别的页面进入聊天页后滚动到底部（导航完成后 DOM 已就绪）
router.afterEach((to) => {
  if (to.name !== 'chat') return
  setTimeout(() => {
    const el = document.querySelector('.chat-scroll-container')
    if (el) el.scrollTop = el.scrollHeight
  }, 0)
})

createApp(App).use(pinia).use(router).mount('#app')
