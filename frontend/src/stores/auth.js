import { defineStore } from 'pinia'
import { api } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('ac_token') || '',
    user: JSON.parse(localStorage.getItem('ac_user') || 'null'),
    loading: false,
  }),
  getters: {
    isLoggedIn: (s) => Boolean(s.token),
    isAdmin: (s) => s.user?.role === 'admin',
    displayName: (s) => s.user?.display_name || s.user?.student?.name || '同学',
    student: (s) => s.user?.student || null,
  },
  actions: {
    setSession(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('ac_token', token)
      localStorage.setItem('ac_user', JSON.stringify(user))
    },
    async login(username, password) {
      this.loading = true
      try {
        const data = await api.login(username, password)
        this.setSession(data.access_token, data.user)
        return data.user
      } finally {
        this.loading = false
      }
    },
    async loadMe() {
      if (!this.token) return null
      const user = await api.me()
      this.user = user
      localStorage.setItem('ac_user', JSON.stringify(user))
      return user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('ac_token')
      localStorage.removeItem('ac_user')
    },
  },
})
