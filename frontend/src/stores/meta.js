import { defineStore } from 'pinia'
import { api } from '@/api'

export const useMetaStore = defineStore('meta', {
  state: () => ({
    data: null,
    loading: false,
  }),
  getters: {
    llmEnabled: (s) => Boolean(s.data?.llm_enabled),
    llmLabel: (s) => (s.data?.llm_enabled ? s.data?.llm_model || '在线模型' : '离线模板'),
    currentTerm: (s) => s.data?.current_term || '2025-2026-2',
    graph: (s) => s.data?.graph || '',
    engineVersion: (s) => s.data?.engine_version || '',
  },
  actions: {
    async fetchMeta() {
      if (this.loading) return
      this.loading = true
      try {
        this.data = await api.meta()
      } catch {
        this.data = null
      } finally {
        this.loading = false
      }
    },
  },
})
