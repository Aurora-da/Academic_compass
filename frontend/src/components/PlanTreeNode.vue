<template>
  <div v-if="visible" class="tree-node">
    <div class="node-shell">
      <button class="node-card" :class="[tone, { active }]" @click="$emit('select', node.id)">
        <div class="node-row">
          <span
            v-if="hasChildren"
            class="caret"
            :class="{ open }"
            @click.stop="$emit('toggle', node.id)"
          >
            <UiIcon name="chevron" :size="12" />
          </span>
          <span v-else class="caret placeholder" />
          <span class="node-dot" />
          <div class="node-text">
            <strong>{{ node.name }}</strong>
            <span>{{ modeLabel }}<template v-if="courseCount"> · {{ courseCount }} 门</template></span>
          </div>
          <div class="node-credits">
            <strong>{{ info.earned.toFixed(1) }}</strong>
            <span>/ {{ info.require.toFixed(1) }}</span>
          </div>
          <span v-if="node.window" class="window-tag">第 {{ node.window.from_term }} 学期起</span>
        </div>

        <div class="node-bar">
          <i :class="tone" :style="{ width: `${progress}%` }" />
        </div>

        <div class="node-foot">
          <StatusPill :status="info.status" />
          <span v-if="info.gap > 0" class="gap">缺 {{ info.gap.toFixed(1) }}</span>
          <span v-if="info.over > 0" class="over">超修 {{ info.over.toFixed(1) }}</span>
          <span v-if="node.direction" class="direction-tag">{{ info.picked_name || '方向组' }}</span>
          <span v-if="structureGap" class="structure">
            {{ structureGap }}
          </span>
        </div>
      </button>
    </div>

    <div v-if="hasChildren && open" class="tree-children">
      <PlanTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :audit-map="auditMap"
        :expanded="expanded"
        :selected="selected"
        :query="query"
        :depth="depth + 1"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusPill from './StatusPill.vue'
import UiIcon from './UiIcon.vue'

const props = defineProps({
  node: { type: Object, required: true },
  auditMap: { type: Object, default: () => ({}) },
  expanded: { type: Set, default: () => new Set() },
  selected: { type: String, default: '' },
  query: { type: String, default: '' },
  depth: { type: Number, default: 0 },
})

defineEmits(['select', 'toggle'])

const info = computed(() => {
  const item = props.auditMap[props.node.id]
  return {
    require: item?.require ?? props.node.require ?? 0,
    earned: item?.earned ?? 0,
    gap: item?.gap ?? 0,
    over: item?.over ?? 0,
    status: item?.status ?? 'gap',
    child_ok: item?.child_ok ?? true,
    own_ok: item?.own_ok ?? false,
    picked_name: item?.picked_name,
    courses_total: item?.courses_total,
    children: item?.children || [],
  }
})

const hasChildren = computed(() => (props.node.children || []).length > 0)
const open = computed(() => props.expanded.has(props.node.id) || Boolean(props.query))
const active = computed(() => props.selected === props.node.id)

const modeLabel = computed(() => {
  const map = { all_of: '全部满足', any_of: '任选其一', free: '总量约束' }
  return map[props.node.mode] || props.node.mode
})

const courseCount = computed(() => {
  if (info.value.courses_total) return info.value.courses_total
  let count = (props.node.courses || []).length
  for (const child of props.node.children || []) {
    count += countCourses(child)
  }
  return count
})

function countCourses(node) {
  let n = (node.courses || []).length
  for (const child of node.children || []) n += countCourses(child)
  return n
}

const progress = computed(() => {
  const require = info.value.require
  if (!require) return 100
  return Math.max(0, Math.min(100, (info.value.earned / require) * 100))
})

const tone = computed(() => {
  if (info.value.status === 'ok') return 'ok'
  if (info.value.status === 'structure_gap') return 'structure'
  return 'gap'
})

const structureGap = computed(() => {
  if (info.value.child_ok) return ''
  const child = info.value.children.find((c) => c.require > 0 && !c.ok)
  if (!child) return ''
  return `${child.name}差 ${child.gap.toFixed(1)}`
})

const visible = computed(() => {
  const q = props.query.trim()
  if (!q) return true
  return subtreeMatch(props.node, q)
})

function subtreeMatch(node, q) {
  if (node.name.includes(q)) return true
  if ((node.courses || []).some((c) => c.name.includes(q) || c.code.includes(q))) return true
  return (node.children || []).some((child) => subtreeMatch(child, q))
}
</script>

<style scoped>
.tree-node {
  position: relative;
}

.node-shell {
  position: relative;
}

.node-card {
  width: 100%;
  display: grid;
  gap: 7px;
  padding: 11px 13px 9px;
  border-radius: 13px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.55);
  text-align: left;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.node-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(30, 78, 216, 0.18);
  transform: translateX(2px);
  box-shadow: 0 6px 16px rgba(12, 22, 48, 0.05);
}

.node-card.active {
  background: rgba(30, 78, 216, 0.06);
  border-color: rgba(30, 78, 216, 0.3);
  box-shadow: 0 8px 20px rgba(30, 78, 216, 0.1);
}

.node-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.caret {
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 5px;
  color: var(--muted-2);
  transition: transform 0.2s ease, background 0.2s ease;
  flex: none;
}

.caret:hover {
  background: rgba(21, 32, 43, 0.06);
}

.caret.open {
  transform: rotate(90deg);
}

.caret.placeholder {
  background: transparent;
}

.node-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(18, 131, 111, 0.1);
}

.node-card.gap .node-dot {
  background: var(--amber);
  box-shadow: 0 0 0 3px rgba(178, 106, 27, 0.12);
}

.node-card.structure .node-dot {
  background: var(--rose);
  box-shadow: 0 0 0 3px rgba(184, 69, 63, 0.1);
}

.node-text {
  display: grid;
  min-width: 0;
  flex: 1;
}

.node-text strong {
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-text span {
  font-size: 9px;
  color: var(--muted-2);
  margin-top: 1px;
}

.node-credits {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted-2);
  white-space: nowrap;
}

.node-credits strong {
  font-size: 13px;
  color: var(--ink);
}

.window-tag {
  font-size: 8.5px;
  padding: 2px 5px;
  border-radius: 4px;
  background: rgba(47, 102, 232, 0.07);
  color: #3730a3;
  white-space: nowrap;
}

.node-bar {
  height: 3.5px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.05);
  overflow: hidden;
  margin-left: 26px;
}

.node-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--grad);
  transition: width 0.9s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.node-bar i.gap {
  background: linear-gradient(90deg, #f59e0b, #fb923c);
}

.node-bar i.structure {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
}

.node-foot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: 26px;
}

.node-foot .gap {
  font-size: 9px;
  color: #94530f;
}

.node-foot .over {
  font-size: 9px;
  color: #0b6b5b;
}

.node-foot .structure {
  font-size: 9px;
  color: #96332e;
  background: rgba(184, 69, 63, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
}

.direction-tag {
  font-size: 8.5px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(30, 78, 216, 0.08);
  color: var(--violet);
}

.tree-children {
  margin-left: 14px;
  padding-left: 10px;
  border-left: 1px dashed rgba(21, 32, 43, 0.1);
  display: grid;
  gap: 4px;
  margin-top: 4px;
}
</style>
