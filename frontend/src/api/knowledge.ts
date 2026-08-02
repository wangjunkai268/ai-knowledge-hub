/** 知识库统计 + 健康检查 API */
import { api } from './client'

export function getKnowledgeStats(kbId?: string | null) {
  return api.get('/knowledge/stats', { params: { kb_id: kbId ?? undefined } })
}

export function reloadKnowledge() {
  return api.post('/knowledge/reload')
}

export function healthCheck() {
  return api.get('/health')
}
