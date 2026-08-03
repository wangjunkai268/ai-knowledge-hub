/** 文档管理 API */
import { api } from './client'

export function getDocuments(kbId?: string | null) {
  return api.get('/documents', { params: { kb_id: kbId ?? undefined } })
}

export function uploadDocument(file: File, kbId?: string | null) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    params: { kb_id: kbId ?? undefined },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id: string, kbId?: string | null) {
  return api.delete(`/documents/${id}`, { params: { kb_id: kbId ?? undefined } })
}

export function batchDeleteDocuments(ids: string[], kbId?: string | null) {
  return api.post('/documents/batch-delete', {
    kb_id: kbId ?? null,
    doc_ids: ids,
  })
}
