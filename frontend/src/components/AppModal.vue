<template>
  <teleport to="body">
    <transition name="modal">
      <div v-if="open" class="modal-mask" @click.self="$emit('close')">
        <div class="modal-card" :style="{ maxWidth: width }">
          <header class="modal-head">
            <div>
              <h3>{{ title }}</h3>
              <p v-if="subtitle" class="muted small">{{ subtitle }}</p>
            </div>
            <button class="modal-close" @click="$emit('close')">
              <UiIcon name="close" :size="18" />
            </button>
          </header>
          <div class="modal-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import UiIcon from './UiIcon.vue'

defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '640px' },
})
defineEmits(['close'])
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 250;
  background: rgba(8, 14, 30, 0.42);
  backdrop-filter: blur(6px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.modal-card {
  width: 100%;
  max-height: min(86vh, 900px);
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--line);
}

.modal-head h3 {
  font-size: 18px;
}

.modal-head p {
  margin-top: 6px;
}

.modal-close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  color: var(--muted);
}

.modal-close:hover {
  background: rgba(21, 32, 43, 0.06);
  color: var(--ink);
}

.modal-body {
  padding: 22px 24px;
  overflow-y: auto;
}

.modal-foot {
  padding: 14px 24px 20px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.24s ease;
}

.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
  transition: transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-card,
.modal-leave-to .modal-card {
  transform: translateY(16px) scale(0.97);
}
</style>
