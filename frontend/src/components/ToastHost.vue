<template>
  <teleport to="body">
    <div class="toast-host">
      <transition-group name="toast">
        <div v-for="item in toast.items" :key="item.id" class="toast" :class="`toast-${item.type}`">
          <span class="toast-icon">
            <UiIcon :name="icon(item.type)" :size="17" />
          </span>
          <span class="toast-msg">{{ item.message }}</span>
          <button class="toast-close" @click="toast.remove(item.id)">
            <UiIcon name="close" :size="14" />
          </button>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import UiIcon from './UiIcon.vue'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

function icon(type) {
  if (type === 'success') return 'check'
  if (type === 'error') return 'alert'
  return 'info'
}
</script>

<style scoped>
.toast-host {
  position: fixed;
  z-index: 300;
  top: 22px;
  right: 24px;
  display: grid;
  gap: 10px;
  width: min(380px, calc(100vw - 40px));
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 13px 13px 13px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(16px);
  pointer-events: auto;
  font-size: 13px;
  line-height: 1.45;
}

.toast-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  flex: none;
  color: #fff;
  background: var(--grad);
}

.toast-error .toast-icon {
  background: linear-gradient(135deg, #f43f5e, #e11d48);
}

.toast-success .toast-icon {
  background: linear-gradient(135deg, #10b981, #059669);
}

.toast-msg {
  flex: 1;
  color: var(--ink-2);
}

.toast-close {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  color: var(--muted-2);
}

.toast-close:hover {
  background: rgba(21, 32, 43, 0.06);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(18px) scale(0.96);
}

.toast-move {
  transition: transform 0.25s ease;
}
</style>
