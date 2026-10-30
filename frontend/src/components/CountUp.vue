<template>
  <span class="countup">{{ prefix }}{{ display }}{{ suffix }}</span>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  decimals: { type: Number, default: 0 },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' },
  duration: { type: Number, default: 1100 },
  group: { type: Boolean, default: false },
})

const display = ref(format(0))
let frame = 0
let from = 0
let start = 0
let target = 0

function format(value) {
  const fixed = Number(value).toFixed(props.decimals)
  if (!props.group) return fixed
  const [int, dec] = fixed.split('.')
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return dec !== undefined ? `${grouped}.${dec}` : grouped
}

function animate(now) {
  if (!start) start = now
  const progress = Math.min(1, (now - start) / props.duration)
  const eased = 1 - Math.pow(1 - progress, 3)
  display.value = format(from + (target - from) * eased)
  if (progress < 1) frame = requestAnimationFrame(animate)
}

function run(next, immediate = false) {
  cancelAnimationFrame(frame)
  from = immediate ? next : Number(display.value.replace(/,/g, '')) || 0
  target = next
  start = 0
  if (immediate || props.duration <= 0) {
    display.value = format(next)
    return
  }
  frame = requestAnimationFrame(animate)
}

watch(
  () => props.value,
  (next) => run(Number(next) || 0),
)

onMounted(() => run(Number(props.value) || 0, true))
onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>
