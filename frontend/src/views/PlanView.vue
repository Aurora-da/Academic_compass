<template>
  <div class="page plan-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">培养方案</h1>
        <p class="page-sub">
          结构照抄教务系统，增量放在标注层：每个模块都回答“要求多少、已获多少、还缺什么”。
        </p>
      </div>
      <div class="head-actions">
        <span v-if="validation" class="chip" :class="validation.errors ? 'chip-danger' : 'chip-ok'">
          <span class="dot" :class="validation.errors ? 'danger' : ''" />
          方案校验 {{ validation.errors ? `${validation.errors} 项错误` : '通过' }}
        </span>
        <button class="btn btn-sm" @click="toggleAll">
          <UiIcon name="layers" :size="14" />
          {{ allExpanded ? '全部收起' : '全部展开' }}
        </button>
        <router-link to="/recommend" class="btn btn-sm btn-primary">
          <UiIcon name="compass" :size="14" />
          去选课
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="skeleton" style="height: 560px" />

    <template v-else-if="plan && audit">
      <section class="plan-meta card reveal">
        <div class="meta-brand">
          <div class="meta-icon"><UiIcon name="book" :size="20" /></div>
          <div>
            <strong>{{ plan.name }}</strong>
            <span>{{ plan.major }} · {{ plan.grade }} 级 · {{ plan.degree }}</span>
          </div>
        </div>
        <div class="meta-facts">
          <div><span>总学分</span><strong>{{ plan.total_credits.toFixed(0) }}</strong></div>
          <div><span>学制</span><strong>{{ plan.duration.standard }} 年</strong><small>弹性 {{ plan.duration.min }}–{{ plan.duration.max }}</small></div>
          <div><span>课程</span><strong>{{ plan.course_count }} <small>门</small></strong></div>
          <div><span>模块</span><strong>{{ plan.modules.length }} <small>个</small></strong></div>
          <div><span>状态</span><strong class="frozen">{{ plan.status === 'frozen' ? '已冻结' : plan.status }}</strong></div>
        </div>
        <div class="meta-source">
          <UiIcon name="shield" :size="14" />
          <span>来源：{{ plan.source }}</span>
        </div>
      </section>

      <div class="plan-layout">
        <aside class="tree-panel card reveal reveal-2">
          <div class="tree-head">
            <div class="row">
              <h3>主修</h3>
              <span class="chip chip-line">{{ audit.modules.filter((m) => m.ok).length }}/{{ audit.modules.length }} 达标</span>
            </div>
            <div class="search-wrap">
              <UiIcon name="search" :size="15" />
              <input v-model="query" class="input" placeholder="搜索模块或课程…" />
            </div>
          </div>
          <div class="tree-body">
            <PlanTreeNode
              v-for="node in plan.modules"
              :key="node.id"
              :node="node"
              :audit-map="auditMap"
              :expanded="expanded"
              :selected="selectedId"
              :query="query"
              @select="selectNode"
              @toggle="toggleNode"
            />
            <div v-if="query && !treeHasMatch" class="empty" style="padding: 30px">
              没有匹配的模块或课程
            </div>
          </div>
          <div class="tree-legend">
            <span><i class="lg ok" />达标</span>
            <span><i class="lg gap" />有缺口</span>
            <span><i class="lg structure" />结构未达标</span>
          </div>
        </aside>

        <section class="detail-panel reveal reveal-3">
          <div v-if="selectedNode" class="detail-head card">
            <div class="detail-path">{{ pathLabel }}</div>
            <div class="detail-title-row">
              <div>
                <h2>{{ selectedNode.name }}</h2>
                <div class="detail-tags">
                  <span class="chip chip-line">{{ modeLabel(selectedNode.mode) }}</span>
                  <span v-if="selectedNode.window" class="chip chip-info">
                    <UiIcon name="calendar" :size="12" />
                    第 {{ selectedNode.window.from_term }} 学期起可选
                  </span>
                  <StatusPill v-if="selectedAudit" :status="selectedAudit.status" />
                </div>
              </div>
              <div class="detail-nums">
                <div><span>要求</span><strong>{{ num(selectedAudit?.require ?? selectedNode.require) }}</strong></div>
                <div><span>已获</span><strong class="earned">{{ num(selectedAudit?.earned ?? 0) }}</strong></div>
                <div><span>缺口</span><strong class="gap">{{ num(selectedAudit?.gap ?? 0) }}</strong></div>
              </div>
            </div>

            <div class="detail-bar">
              <i :style="{ width: `${detailProgress}%` }" :class="detailTone" />
            </div>

            <p class="mode-note">{{ modeNote(selectedNode.mode) }}</p>

            <div v-if="structureChildren.length" class="alert alert-warn structure-callout">
              <span class="alert-ic"><UiIcon name="alert" :size="15" /></span>
              <div class="alert-body">
                <strong>总量与结构要分开看</strong>
                <p>
                  {{ selectedNode.name }}总量
                  {{ selectedAudit.own_ok ? '已达标' : `差 ${num(selectedAudit.gap)} 分` }}，
                  但
                  <template v-for="(child, idx) in structureChildren" :key="child.id">
                    「{{ child.name }}」还差 {{ num(child.gap) }} 分<template v-if="idx < structureChildren.length - 1">；</template>
                  </template>
                  。补课时优先补子项，否则总量补满、结构仍不合格。
                </p>
              </div>
            </div>

            <div v-if="directionOptions.length" class="direction-strip">
              <div class="direction-head">
                <strong>方向三选一</strong>
                <span class="hint">方向同时决定 2 学分创新实践内容</span>
              </div>
              <div class="direction-options">
                <button
                  v-for="option in directionOptions"
                  :key="option.id"
                  class="direction-option"
                  :class="{ picked: selectedAudit?.picked === option.id }"
                  @click="selectNode(option.id)"
                >
                  <span>{{ option.name }}</span>
                  <strong>{{ num(option.earned) }} / {{ num(option.require) }}</strong>
                  <small>{{ option.ok ? '已达标' : `缺 ${num(option.gap)}` }}</small>
                </button>
              </div>
            </div>

            <div class="detail-stat-row">
              <div><span>子模块</span><strong>{{ selectedNode.children?.length || 0 }}</strong></div>
              <div><span>课程数</span><strong>{{ detailCourses.length }}</strong></div>
              <div><span>已通过</span><strong>{{ detailCourses.filter((c) => c.status === 'passed').length }}</strong></div>
              <div><span>在修</span><strong>{{ detailCourses.filter((c) => c.status === 'studying').length }}</strong></div>
              <div><span>未通过</span><strong>{{ detailCourses.filter((c) => !['passed', 'studying'].includes(c.status)).length }}</strong></div>
            </div>
          </div>

          <div class="courses-card card">
            <div class="courses-head">
              <div class="row">
                <h3>课程明细</h3>
                <span class="chip chip-line">{{ filteredCourses.length }} 门</span>
              </div>
              <div class="course-filters">
                <div class="filter-tabs">
                  <button
                    v-for="tab in filters"
                    :key="tab.key"
                    :class="{ active: filterStatus === tab.key }"
                    @click="filterStatus = tab.key"
                  >
                    {{ tab.label }}
                  </button>
                </div>
                <div class="search-wrap course-search">
                  <UiIcon name="search" :size="14" />
                  <input v-model="courseQuery" class="input" placeholder="课程名 / 编码" />
                </div>
              </div>
            </div>

            <div class="table-wrap">
              <table class="table course-table">
                <thead>
                  <tr>
                    <th class="sortable" :aria-sort="ariaSort('name')" @click="sortBy('name')">课程 <span class="sort-mark">{{ sortMark('name') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('credit')" @click="sortBy('credit')">学分 <span class="sort-mark">{{ sortMark('credit') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('term')" @click="sortBy('term')">指导学期 <span class="sort-mark">{{ sortMark('term') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('assessment')" @click="sortBy('assessment')">考核 <span class="sort-mark">{{ sortMark('assessment') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('moduleName')" @click="sortBy('moduleName')">模块 <span class="sort-mark">{{ sortMark('moduleName') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('status')" @click="sortBy('status')">状态 <span class="sort-mark">{{ sortMark('status') }}</span></th>
                    <th class="sortable" :aria-sort="ariaSort('score')" @click="sortBy('score')">成绩 <span class="sort-mark">{{ sortMark('score') }}</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="course in sortedCourses" :key="course.code">
                    <td>
                      <div class="course-name">
                        <strong>{{ course.name }}</strong>
                        <span>{{ course.code }}</span>
                      </div>
                    </td>
                    <td class="mono">{{ course.credit.toFixed(1) }}</td>
                    <td><span class="term-pill">{{ course.term }}</span></td>
                    <td>{{ course.assessment }}</td>
                    <td><span class="module-pill" :title="course.moduleName">{{ course.moduleName }}</span></td>
                    <td><StatusPill :status="course.status" /></td>
                    <td class="mono">{{ course.score ?? '—' }}</td>
                  </tr>
                  <tr v-if="!filteredCourses.length">
                    <td colspan="7">
                      <div class="empty" style="padding: 36px">没有符合条件的课程</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </template>

    <div v-else class="empty card" style="padding: 60px">
      <UiIcon name="alert" :size="26" />
      <p>培养方案加载失败</p>
      <button class="btn" @click="load">重试</button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlanTreeNode from '@/components/PlanTreeNode.vue'
import StatusPill from '@/components/StatusPill.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const loading = ref(true)
const plan = ref(null)
const audit = ref(null)
const validation = ref(null)
const enrollments = ref([])
const selectedId = ref('M6')
const expanded = ref(new Set())
const query = ref('')
const courseQuery = ref('')
const filterStatus = ref('all')
const sortKey = ref('term')
const sortDir = ref('asc')

const filters = [
  { key: 'all', label: '全部' },
  { key: 'missing', label: '未通过' },
  { key: 'studying', label: '在修' },
  { key: 'passed', label: '已通过' },
]

const auditMap = computed(() => {
  const map = {}
  function walk(nodes) {
    for (const node of nodes || []) {
      map[node.id] = node
      walk(node.children)
    }
  }
  walk(audit.value?.modules)
  return map
})

const selectedAudit = computed(() => auditMap.value[selectedId.value] || null)

const selectedNode = computed(() => {
  let found = null
  function walk(nodes, path) {
    for (const node of nodes || []) {
      if (node.id === selectedId.value) {
        found = { ...node, _path: path }
        return
      }
      walk(node.children, [...path, node.name])
    }
  }
  walk(plan.value?.modules, [])
  return found
})

const pathLabel = computed(() => (selectedNode.value?._path?.length ? selectedNode.value._path.join(' / ') : '主修'))

const detailProgress = computed(() => {
  const require = selectedAudit.value?.require || 0
  if (!require) return 100
  return Math.max(0, Math.min(100, ((selectedAudit.value?.earned || 0) / require) * 100))
})

const detailTone = computed(() => {
  const status = selectedAudit.value?.status
  if (status === 'ok') return 'ok'
  if (status === 'structure_gap') return 'structure'
  return 'gap'
})

const structureChildren = computed(() => {
  if (!selectedAudit.value || selectedAudit.value.child_ok) return []
  return (selectedAudit.value.children || []).filter((c) => c.require > 0 && !c.ok)
})

const directionOptions = computed(() => {
  if (!selectedAudit.value || selectedAudit.value.mode !== 'any_of') return []
  return selectedAudit.value.children || []
})

const detailCourses = computed(() => {
  if (!selectedNode.value) return []
  const passed = new Map((audit.value?.passed_courses || []).map((c) => [c.code, c]))
  const scoreMap = new Map()
  for (const enrollment of enrollments.value) {
    if (!scoreMap.has(enrollment.code) || enrollment.term > (scoreMap.get(enrollment.code).term || '')) {
      scoreMap.set(enrollment.code, enrollment)
    }
  }
  const rows = []
  const seen = new Set()
  function walk(node) {
    for (const course of node.courses || []) {
      if (seen.has(course.code)) continue
      seen.add(course.code)
      const info = auditMap.value[node.id]
      let status = 'not_started'
      if (passed.has(course.code)) status = 'passed'
      else {
        const local = (info?.missing || []).find((m) => m.code === course.code)
        const root = (audit.value?.modules || []).flatMap(function flatten(m) {
          return [m, ...(m.children || []).flatMap(flatten)]
        }).find((m) => m.id === node.id)
        if (local?.status) status = local.status
        else if ((auditMap.value[node.id]?.studying_courses || []).some((s) => s.code === course.code)) status = 'studying'
        else if (root) {
          const found = (root.missing || []).find((m) => m.code === course.code)
          if (found) status = found.status
        }
      }
      const enroll = scoreMap.get(course.code)
      rows.push({
        code: course.code,
        name: course.name,
        credit: course.credit,
        term: course.term,
        assessment: course.assessment,
        nature: course.nature,
        moduleName: node.name,
        status,
        score: passed.get(course.code)?.score ?? enroll?.score ?? null,
      })
    }
    for (const child of node.children || []) walk(child)
  }
  walk(selectedNode.value)
  return rows.sort((a, b) => termValue(a.term) - termValue(b.term) || a.code.localeCompare(b.code))
})

const filteredCourses = computed(() => {
  const q = courseQuery.value.trim().toLowerCase()
  return detailCourses.value.filter((course) => {
    if (filterStatus.value === 'missing' && ['passed', 'studying'].includes(course.status)) return false
    if (filterStatus.value === 'studying' && course.status !== 'studying') return false
    if (filterStatus.value === 'passed' && course.status !== 'passed') return false
    if (q && !course.name.toLowerCase().includes(q) && !course.code.toLowerCase().includes(q)) return false
    return true
  })
})

const statusRank = { passed: 0, studying: 1, failed: 2, withdrawn: 3 }

const sortedCourses = computed(() => {
  const rows = [...filteredCourses.value]
  const direction = sortDir.value === 'asc' ? 1 : -1
  rows.sort((a, b) => {
    if (sortKey.value === 'score') {
      if (a.score == null && b.score == null) return a.code.localeCompare(b.code)
      if (a.score == null) return 1
      if (b.score == null) return -1
      return (Number(a.score) - Number(b.score)) * direction
    }
    let left
    let right
    if (sortKey.value === 'credit') {
      left = Number(a.credit || 0)
      right = Number(b.credit || 0)
    } else if (sortKey.value === 'term') {
      left = termValue(a.term)
      right = termValue(b.term)
    } else if (sortKey.value === 'status') {
      left = statusRank[a.status] ?? 9
      right = statusRank[b.status] ?? 9
    } else {
      left = String(a[sortKey.value] || '')
      right = String(b[sortKey.value] || '')
      return left.localeCompare(right, 'zh-CN') * direction || a.code.localeCompare(b.code)
    }
    return (left - right) * direction || a.code.localeCompare(b.code)
  })
  return rows
})

function sortBy(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortDir.value = 'asc'
}

function sortMark(key) {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 'asc' ? '↑' : '↓'
}

function ariaSort(key) {
  if (sortKey.value !== key) return 'none'
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

const treeHasMatch = computed(() => {
  if (!query.value.trim()) return true
  function walk(nodes) {
    return (nodes || []).some(
      (node) =>
        node.name.includes(query.value) ||
        (node.courses || []).some((c) => c.name.includes(query.value) || c.code.includes(query.value)) ||
        walk(node.children),
    )
  }
  return walk(plan.value?.modules)
})

const allExpanded = computed(() => expanded.value.size >= allNodeIds.value.size && allNodeIds.value.size > 0)

const allNodeIds = computed(() => {
  const ids = new Set()
  function walk(nodes) {
    for (const node of nodes || []) {
      if (node.children?.length) ids.add(node.id)
      walk(node.children)
    }
  }
  walk(plan.value?.modules)
  return ids
})

function termValue(term) {
  const [year, half] = String(term || '1-1').split('-')
  return Number(year) * 2 + Number(half)
}

function num(value) {
  return Number(value || 0).toFixed(1)
}

function modeLabel(mode) {
  return { all_of: '全部满足', any_of: '任选其一', free: '总量约束' }[mode] || mode
}

function modeNote(mode) {
  if (mode === 'any_of') return '任选其一：只认被选中的方向；换方向会改变 6 学分方向课与 2 学分创新实践。'
  if (mode === 'free') return '自由选修：父项只看总量下限，但带下限的子项仍必须各自达标——总量达标 ≠ 结构达标。'
  return '全部满足：父项只检查自身学分下限，子项全部通过；父项缺口不等于子项缺口之和。'
}

function selectNode(id) {
  selectedId.value = id
  const node = findNode(id)
  if (node?.children?.length) expanded.value = new Set([...expanded.value, id])
  router.replace({ query: { module: id } })
  nextTick(() => scrollSelectedIntoView())
}

async function scrollSelectedIntoView() {
  await nextTick()
  const container = document.querySelector('.tree-body')
  const el = container?.querySelector('.node-card.active')
  if (!container || !el) return
  const cRect = container.getBoundingClientRect()
  const eRect = el.getBoundingClientRect()
  const target = container.scrollTop + (eRect.top - cRect.top) - container.clientHeight / 2 + eRect.height / 2
  container.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
}

function findNode(id) {
  let found = null
  function walk(nodes) {
    for (const node of nodes || []) {
      if (node.id === id) found = node
      walk(node.children)
    }
  }
  walk(plan.value?.modules)
  return found
}

function toggleNode(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

function toggleAll() {
  expanded.value = allExpanded.value ? new Set() : new Set(allNodeIds.value)
}

function buildExpanded(nodes, set) {
  for (const node of nodes || []) {
    if (node.children?.length) set.add(node.id)
    buildExpanded(node.children, set)
  }
  return set
}

async function load() {
  loading.value = true
  try {
    audit.value = await api.audit()
    const planId = audit.value?.plan?.id || auth.student?.plan_id || 'CS-BT-2024-v1'
    const [planData, enrollmentData] = await Promise.all([
      api.plan(planId),
      api.enrollments().catch(() => []),
    ])
    plan.value = planData
    enrollments.value = enrollmentData
    expanded.value = buildExpanded(planData.modules, new Set())
    const requested = typeof route.query.module === 'string' ? route.query.module : ''
    if (requested && findNode(requested)) selectedId.value = requested
    api.validation(planId).then((v) => (validation.value = v)).catch(() => {})
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    loading.value = false
    await nextTick()
    scrollSelectedIntoView()
  }
}

watch(
  () => route.query.module,
  (value) => {
    if (typeof value === 'string' && value && findNode(value)) {
      selectedId.value = value
      scrollSelectedIntoView()
    }
  },
)

onMounted(load)
</script>

<style scoped>
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.plan-meta {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}

.meta-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 250px;
  flex: 1;
}

.meta-icon {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--grad);
  flex: none;
}

.meta-brand strong {
  display: block;
  font-size: 14px;
}

.meta-brand span {
  display: block;
  font-size: 10.5px;
  color: var(--muted-2);
  margin-top: 3px;
}

.meta-facts {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}

.meta-facts div {
  display: grid;
  gap: 1px;
}

.meta-facts span {
  font-size: 9.5px;
  color: var(--muted-2);
  letter-spacing: 0.02em;
}

.meta-facts strong {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.meta-facts strong.frozen {
  font-size: 12px;
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.1);
  padding: 3px 8px;
  border-radius: 6px;
  width: fit-content;
}

.meta-facts strong small {
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 500;
  color: var(--muted-2);
  margin-left: 2px;
}

.meta-facts small {
  font-size: 9px;
  color: var(--muted-2);
}

.meta-source {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted-2);
  font-size: 9.5px;
  padding-left: 18px;
  border-left: 1px solid var(--line);
  max-width: 260px;
}

.plan-layout {
  display: grid;
  grid-template-columns: minmax(400px, 0.9fr) minmax(0, 1.4fr);
  gap: 18px;
  margin-top: 18px;
  align-items: start;
}

.tree-panel {
  position: sticky;
  top: calc(var(--topbar-h) + 16px);
  max-height: calc(100vh - var(--topbar-h) - 40px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 14px 12px;
}

.tree-head {
  display: grid;
  gap: 12px;
  padding: 0 4px 12px;
  border-bottom: 1px solid var(--line);
}

.tree-head h3 {
  font-size: 15px;
}

.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px 4px 6px;
  display: grid;
  gap: 3px;
}

.tree-legend {
  display: flex;
  gap: 14px;
  padding: 10px 4px 2px;
  border-top: 1px solid var(--line);
  color: var(--muted-2);
  font-size: 9.5px;
}

.tree-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.lg {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
}

.lg.gap {
  background: var(--amber);
}

.lg.structure {
  background: var(--rose);
}

.detail-panel {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.detail-head {
  padding: 22px 24px;
}

.detail-path {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--muted-2);
  text-transform: uppercase;
  margin-bottom: 7px;
}

.detail-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.detail-title-row h2 {
  font-size: 25px;
  letter-spacing: -0.03em;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
}

.detail-nums {
  display: flex;
  gap: 18px;
  flex: none;
}

.detail-nums div {
  display: grid;
  gap: 1px;
  text-align: right;
}

.detail-nums span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.detail-nums strong {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.detail-nums strong.earned {
  color: var(--indigo);
}

.detail-nums strong.gap {
  color: #94530f;
}

.detail-bar {
  height: 6px;
  margin: 16px 0 12px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.05);
  overflow: hidden;
}

.detail-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--grad);
  transition: width 1s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.detail-bar i.gap {
  background: linear-gradient(90deg, #f59e0b, #fb923c);
}

.detail-bar i.structure {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
}

.mode-note {
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.structure-callout {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: var(--r-sm);
  background: var(--warning-bg);
  border: 1px solid var(--warning-line);
}

.callout-ic {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(184, 69, 63, 0.1);
  color: #96332e;
  flex: none;
}

.structure-callout strong {
  font-size: 12.5px;
  color: var(--warning);
}

.structure-callout p {
  margin-top: 3px;
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--ink-2);
}

.direction-strip {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(30, 78, 216, 0.05);
  border: 1px solid rgba(30, 78, 216, 0.12);
}

.direction-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 9px;
}

.direction-head strong {
  font-size: 11.5px;
}

.direction-head span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.direction-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.direction-option {
  display: grid;
  gap: 2px;
  padding: 9px 10px;
  border-radius: 9px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  text-align: left;
}

.direction-option:hover {
  border-color: rgba(30, 78, 216, 0.3);
}

.direction-option.picked {
  border-color: rgba(30, 78, 216, 0.4);
  background: rgba(30, 78, 216, 0.08);
}

.direction-option span {
  font-size: 10.5px;
  font-weight: 600;
}

.direction-option strong {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
}

.direction-option small {
  font-size: 9px;
  color: var(--muted-2);
}

.detail-stat-row {
  display: flex;
  gap: 28px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}

.detail-stat-row div {
  display: grid;
  gap: 1px;
}

.detail-stat-row span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.detail-stat-row strong {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
}

.courses-card {
  overflow: hidden;
}

.courses-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px 14px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--line);
}

.courses-head h3 {
  font-size: 16px;
}

.course-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-tabs {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 9px;
  background: rgba(21, 32, 43, 0.04);
}

.filter-tabs button {
  height: 27px;
  padding: 0 10px;
  border-radius: 7px;
  font-size: 10.5px;
  color: var(--muted);
}

.filter-tabs button.active {
  background: #fff;
  color: var(--ink);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(12, 22, 48, 0.07);
}

.course-search {
  width: 160px;
}

.course-search .input {
  height: 33px;
  font-size: 11.5px;
}

.course-table {
  table-layout: fixed;
}

.course-table th,
.course-table td {
  padding-left: 10px;
  padding-right: 10px;
}

.course-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.course-table th.sortable:hover {
  color: var(--violet);
}

.sort-mark {
  margin-left: 2px;
  color: var(--muted-2);
  font-size: 9px;
  opacity: 0.6;
}

.course-table th[aria-sort='ascending'] .sort-mark,
.course-table th[aria-sort='descending'] .sort-mark {
  color: var(--violet);
  opacity: 1;
}

@media (min-width: 900px) {
  .courses-card {
    overflow: visible;
  }

  .courses-card .table-wrap {
    overflow: visible;
  }

  .course-table thead th {
    position: sticky;
    top: 69px;
    z-index: 4;
    background: var(--surface-2);
    box-shadow: inset 0 -1px 0 var(--line);
  }
}

.course-table th:nth-child(1) { width: 29%; }
.course-table th:nth-child(2) { width: 8%; }
.course-table th:nth-child(3) { width: 10%; }
.course-table th:nth-child(4) { width: 8%; }
.course-table th:nth-child(5) { width: 24%; }
.course-table th:nth-child(6) { width: 12%; }
.course-table th:nth-child(7) { width: 9%; }

.course-table th:nth-child(2),
.course-table th:nth-child(3),
.course-table th:nth-child(4),
.course-table th:nth-child(6),
.course-table th:nth-child(7),
.course-table td:nth-child(2),
.course-table td:nth-child(3),
.course-table td:nth-child(4),
.course-table td:nth-child(6),
.course-table td:nth-child(7) {
  text-align: center;
  white-space: nowrap;
}

.course-name {
  display: grid;
  gap: 2px;
}

.course-name strong {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
}

.course-name span {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted-2);
}

.term-pill {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted);
}

.module-pill {
  display: inline-block;
  max-width: 100%;
  font-size: 9.5px;
  line-height: 1.35;
  color: var(--muted);
  background: rgba(30, 78, 216, 0.06);
  padding: 2px 6px;
  border-radius: 5px;
  white-space: normal;
  overflow-wrap: anywhere;
}

@media (max-width: 1200px) {
  .plan-layout {
    grid-template-columns: 1fr;
  }

  .tree-panel {
    position: static;
    max-height: none;
  }

  .tree-body {
    max-height: 460px;
  }
}

@media (max-width: 760px) {
  .detail-title-row {
    flex-direction: column;
  }

  .detail-nums {
    width: 100%;
    justify-content: space-between;
  }

  .direction-options {
    grid-template-columns: 1fr;
  }

  .meta-source {
    border-left: 0;
    padding-left: 0;
  }
}
</style>
