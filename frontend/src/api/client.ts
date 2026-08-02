import axios from 'axios'

/** 共享 axios 实例 */
export const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})
