<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="ui-icon"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
  strokeWidth: { type: [Number, String], default: 1.7 },
})

const ICONS = {
  grid: ['M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z'],
  tree: ['M5 4v16', 'M5 9h7M5 16h7', 'M12 5h7v8h-7zM12 15h7v4h-7z'],
  compass: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M15.6 8.4l-2.1 5.1-5.1 2.1 2.1-5.1 5.1-2.1z'],
  report: ['M7 3h7l4 4v14H7z', 'M14 3v5h5', 'M10 12h7M10 16h5'],
  medal: ['M8 3h8l-2 6H10z', 'M12 9a5 5 0 100 10 5 5 0 000-10z', 'M10.5 14l1 2 1.5-1 1.5 1 1-2'],
  upload: ['M12 16V4', 'M7 9l5-5 5 5', 'M5 20h14'],
  download: ['M12 4v12', 'M7 11l5 5 5-5', 'M5 20h14'],
  sparkles: [
    'M11 3l1.8 4.9L18 9.7l-4.8 1.8L11 16l-1.8-4.5L4.5 9.7l4.7-1.8L11 3z',
    'M19 15l.7 2 2 .7-2 .7L19 21l-.7-2.6-2-.7 2-.7L19 15z',
  ],
  logout: ['M15 4h4v16h-4', 'M11 8l-4 4 4 4', 'M7 12h9'],
  menu: ['M4 7h16M4 12h16M4 17h16'],
  close: ['M6 6l12 12M18 6L6 18'],
  chevron: ['M9 6l6 6-6 6'],
  'chevron-down': ['M6 9l6 6 6-6'],
  check: ['M5 13l4 4L19 7'],
  alert: ['M12 4l9 16H3z', 'M12 9v5', 'M12 17h.01'],
  search: ['M11 4a7 7 0 100 14 7 7 0 000-14z', 'M20 20l-4-4'],
  plus: ['M12 5v14M5 12h14'],
  print: ['M7 8V3h10v5', 'M7 14H5a2 2 0 01-2-2V8a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2h-2', 'M7 12h10v9H7z'],
  calendar: ['M4 6h16v15H4z', 'M8 3v5M16 3v5', 'M4 11h16'],
  clock: ['M12 7v5l3 2', 'M12 3a9 9 0 100 18 9 9 0 000-18z'],
  book: ['M4 5a3 3 0 013-3h13v18H7a3 3 0 00-3 3z', 'M4 5v16'],
  target: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M12 8a4 4 0 100 8 4 4 0 000-8z', 'M12 11a1 1 0 100 2 1 1 0 000-2z'],
  refresh: ['M20 12a8 8 0 11-2.4-5.7', 'M20 4v5h-5'],
  send: ['M22 2L11 13', 'M22 2l-7 20-4-9-9-4z'],
  user: ['M12 12a4 4 0 100-8 4 4 0 000 8z', 'M4 21a8 8 0 0116 0'],
  shield: ['M12 3l8 3v6c0 5-3.5 8.2-8 9-4.5-.8-8-4-8-9V6z', 'M9 12l2 2 4-4'],
  layers: ['M12 3l9 5-9 5-9-5 9-5z', 'M3 13l9 5 9-5', 'M3 17l9 5 9-5'],
  chart: ['M4 20V10M10 20V4M16 20v-7M22 20H2'],
  'arrow-up': ['M12 19V5M6 11l6-6 6 6'],
  'arrow-right': ['M5 12h14M13 6l6 6-6 6'],
  info: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M12 11v6', 'M12 8h.01'],
  sliders: ['M4 7h16M7 12h10M10 17h4', 'M8 5v4M16 10v4M12 15v4'],
  lock: ['M6 11h12v10H6z', 'M9 11V7a3 3 0 016 0v4'],
  star: ['M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3z'],
  swap: ['M7 4L3 8l4 4', 'M3 8h13a4 4 0 014 4', 'M17 20l4-4-4-4', 'M21 16H8a4 4 0 01-4-4'],
  flag: ['M5 21V4', 'M5 4h12l-2 4 2 4H5'],
  database: ['M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3z', 'M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6', 'M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3'],
  bell: ['M6 9a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z', 'M10 20a2 2 0 004 0'],
  eye: ['M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z', 'M12 9a3 3 0 100 6 3 3 0 000-6z'],
  'eye-off': ['M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z', 'M12 9a3 3 0 100 6 3 3 0 000-6z', 'M4 4l16 16'],
}

const paths = computed(() => ICONS[props.name] || ICONS.info)
</script>

<style scoped>
.ui-icon {
  display: block;
  flex: none;
}
</style>
