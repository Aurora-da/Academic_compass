<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'

const auth = useAuthStore()
const meta = useMetaStore()

onMounted(async () => {
  meta.fetchMeta()
  if (auth.token) {
    await auth.loadMe().catch(() => {})
  }
})
</script>
