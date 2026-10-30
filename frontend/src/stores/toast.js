import { defineStore } from 'pinia'

let seq = 0

export const useToastStore = defineStore('toast', {
  state: () => ({ items: [] }),
  actions: {
    push(message, type = 'info', duration = 3600) {
      const id = ++seq
      this.items.push({ id, message, type })
      if (duration) setTimeout(() => this.remove(id), duration)
      return id
    },
    success(message, duration) {
      return this.push(message, 'success', duration)
    },
    error(message, duration = 5000) {
      return this.push(message, 'error', duration)
    },
    info(message, duration) {
      return this.push(message, 'info', duration)
    },
    remove(id) {
      this.items = this.items.filter((t) => t.id !== id)
    },
  },
})
