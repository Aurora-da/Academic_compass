<template>
  <span class="pill" :class="kindClass">
    <span class="dot" :class="dotClass" />
    {{ label || defaultLabel }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: 'ok' },
  label: { type: String, default: '' },
})

const MAP = {
  ok: { label: '达标', dot: '', cls: 'ok' },
  over: { label: '已达标', dot: '', cls: 'ok' },
  gap: { label: '有缺口', dot: 'warn', cls: 'warn' },
  structure_gap: { label: '结构未达标', dot: 'danger', cls: 'danger' },
  structure_priority: { label: '结构优先', dot: 'danger', cls: 'danger' },
  unmet: { label: '未达标', dot: 'danger', cls: 'danger' },
  missing: { label: '待确认', dot: 'muted', cls: 'muted' },
  met: { label: '达标', dot: '', cls: 'ok' },
  pending: { label: '待审核', dot: 'warn', cls: 'warn' },
  approved: { label: '已通过', dot: '', cls: 'ok' },
  rejected: { label: '已驳回', dot: 'danger', cls: 'danger' },
  studying: { label: '在修', dot: 'warn', cls: 'info' },
  passed: { label: '已通过', dot: '', cls: 'ok' },
  failed: { label: '未通过', dot: 'danger', cls: 'danger' },
  not_started: { label: '未修', dot: 'muted', cls: 'muted' },
  conflict: { label: '时间冲突', dot: 'danger', cls: 'danger' },
  available: { label: '可选', dot: '', cls: 'ok' },
  prereq_missing: { label: '先修未满足', dot: 'danger', cls: 'danger' },
  not_offered: { label: '本学期未开', dot: 'muted', cls: 'muted' },
  full: { label: '已满', dot: 'warn', cls: 'warn' },
  other_direction: { label: '其他方向', dot: 'muted', cls: 'muted' },
  grade_blocked: { label: '年级限制', dot: 'muted', cls: 'muted' },
}

const meta = computed(() => MAP[props.status] || MAP.ok)
const label = computed(() => props.label || meta.value.label)
const kindClass = computed(() => `pill-${meta.value.cls}`)
const dotClass = computed(() => meta.value.dot)
const defaultLabel = computed(() => meta.value.label)
</script>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 10px;
  border-radius: 99px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}

.pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.pill-ok {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.1);
}

.pill-ok .dot {
  background: var(--green);
}

.pill-warn {
  color: #94530f;
  background: rgba(178, 106, 27, 0.13);
}

.pill-warn .dot {
  background: var(--amber);
}

.pill-danger {
  color: #96332e;
  background: rgba(184, 69, 63, 0.1);
}

.pill-danger .dot {
  background: var(--rose);
}

.pill-info {
  color: #3730a3;
  background: rgba(47, 102, 232, 0.1);
}

.pill-info .dot {
  background: var(--blue);
}

.pill-muted {
  color: var(--muted);
  background: rgba(21, 32, 43, 0.05);
}

.pill-muted .dot {
  background: var(--muted-2);
}
</style>
