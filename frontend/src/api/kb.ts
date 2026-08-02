/** 知识库管理 API */
import { api } from './client'

export interface KnowledgeBase {
  id: string
  name: string
  document_count: number
  documents: any[]
}

export function getKbs() {
  return api.get('/kbs')
}

export function createKb(name: string) {
  return api.post('/kbs', { name })
}

export function deleteKb(id: string) {
  return api.delete(`/kbs/${id}`)
}
