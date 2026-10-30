<template>
  <div class="not-found">
    <AuroraBackground />
    <div class="nf-card">
      <div class="nf-code">404</div>
      <h1>这条路径不在培养方案里</h1>
      <p>页面可能已移动，或链接写错了。回到学业总览继续。</p>
      <router-link to="/" class="btn btn-primary">
        <UiIcon name="grid" :size="16" />
        返回学业总览
      </router-link>
    </div>
  </div>
</template>

<script setup>
import AuroraBackground from '@/components/AuroraBackground.vue'
import UiIcon from '@/components/UiIcon.vue'
</script>

<style scoped>
.not-found {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.nf-card {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 12px;
  text-align: center;
  padding: 46px 52px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(20px);
}

.nf-code {
  font-family: var(--font-display);
  font-size: 84px;
  font-weight: 800;
  letter-spacing: -0.06em;
  line-height: 1;
  background: var(--grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.nf-card h1 {
  font-size: 22px;
}

.nf-card p {
  color: var(--muted);
  font-size: 12.5px;
  margin-bottom: 8px;
}
</style>
