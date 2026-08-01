import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import { createPersistedState } from 'pinia-plugin-persistedstate'
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
pinia.use(createPersistedState())

createApp(App).use(pinia).use(router).mount('#app')
