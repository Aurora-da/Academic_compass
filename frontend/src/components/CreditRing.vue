<template>
  <div class="ring" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <defs>
        <linearGradient :id="gradId" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#173a9c" />
          <stop offset="62%" stop-color="#1e4ed8" />
          <stop offset="100%" stop-color="#2f66e8" />
        </linearGradient>
      </defs>
      <circle class="track" :cx="c" :cy="c" :r="r" :stroke-width="stroke" />
      <circle
        class="value"
        :cx="c"
        :cy="c"
        :r="r"
        :stroke="`url(#${gradId})`"
        :stroke-width="stroke"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${c} ${c})`"
      />
    </svg>
    <div class="ring-center">
      <slot>
        <strong>{{ Math.round(percent) }}<i>%</i></strong>
        <span>{{ caption }}</span>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  percent: { type: Number, default: 0 },
  size: { type: Number, default: 168 },
  stroke: { type: Number, default: 11 },
  caption: { type: String, default: '学分完成度' },
})

const uid = useId()
const gradId = `ring-grad-${uid}`
const c = computed(() => props.size / 2)
const r = computed(() => props.size / 2 - props.stroke / 2 - 4)
const circumference = computed(() => 2 * Math.PI * r.value)
const offset = computed(() => {
  const pct = Math.max(0, Math.min(100, props.percent)) / 100
  return circumference.value * (1 - pct)
})
</script>

<style scoped>
.ring {
  position: relative;
  display: grid;
  place-items: center;
}

svg {
  position: absolute;
  inset: 0;
}

.track {
  fill: none;
  stroke: rgba(21, 32, 43, 0.08);
}

.value {
  fill: none;
  stroke-linecap: round;
  transition: stroke-dashoffset 1.2s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.ring-center {
  display: grid;
  place-items: center;
  gap: 4px;
  text-align: center;
  z-index: 1;
  padding-top: 2px;
}

.ring-center strong {
  font-family: var(--font-serif);
  font-size: 46px;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.ring-center strong i {
  font-style: normal;
  font-size: 16px;
  font-weight: 500;
  color: var(--muted);
  margin-left: 1px;
}

.ring-center span {
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 0.02em;
}
</style>
