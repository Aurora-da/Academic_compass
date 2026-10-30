<template>
  <div class="page recommend-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">选课助手</h1>
        <p class="page-sub">以当学期开课计划为硬约束，先锁方向，再排课；每一门推荐都给出理由和不选的后果。</p>
      </div>
      <div class="head-actions">
        <span class="chip chip-line">
          <UiIcon name="calendar" :size="13" />
          {{ rec?.semester || meta.currentTerm }}
        </span>
        <button class="btn btn-sm" :disabled="loading" @click="load">
          <UiIcon name="refresh" :size="14" />
          重新计算
        </button>
      </div>
    </div>

    <div v-if="loading" class="grid" style="gap: 18px">
      <div class="skeleton" style="height: 180px" />
      <div class="skeleton" style="height: 520px" />
    </div>

    <template v-else-if="rec">
      <section class="direction-panel card reveal">
        <div class="direction-title">
          <div>
            <div class="row">
              <h3>第一步：专业方向三选一</h3>
              <span v-if="rec.direction_comparison.locked" class="chip chip-ok">
                <span class="dot" />已锁定
              </span>
              <span v-else class="chip chip-warn">
                <span class="dot warn" />待决策
              </span>
            </div>
            <p>方向不是“任选三门凑 6 分”，它同时决定 2 学分创新实践的内容，锁定后写入个性化方案。</p>
          </div>
          <div class="direction-lock">
            <span class="muted small">已锁定方向</span>
            <strong>{{ rec.direction_comparison.selected_name || '未选' }}</strong>
          </div>
        </div>

        <div class="direction-grid">
          <article
            v-for="option in rec.direction_comparison.options"
            :key="option.id"
            class="direction-card"
            :class="{ recommended: option.recommended, locked: rec.direction_comparison.selected === option.id && rec.direction_comparison.locked }"
          >
            <div class="dc-top">
              <span class="dc-name">{{ option.name }}</span>
              <span v-if="option.recommended" class="dc-rec">推荐</span>
              <span v-if="rec.direction_comparison.selected === option.id && rec.direction_comparison.locked" class="dc-locked">
                <UiIcon name="lock" :size="11" />已锁定
              </span>
            </div>
            <div class="dc-progress">
              <div class="dc-bar"><i :style="{ width: `${Math.min(100, (option.earned / option.require) * 100)}%` }" /></div>
              <strong>{{ option.earned.toFixed(1) }} <span>/ {{ option.require.toFixed(0) }}</span></strong>
            </div>
            <p class="dc-reason">{{ option.reason }}</p>
            <div class="dc-courses">
              <span
                v-for="course in option.remaining.slice(0, 3)"
                :key="course.code"
                class="dc-course"
                :class="{ earned: course.earned, conflict: course.conflict }"
              >
                {{ course.name }} · {{ course.credit.toFixed(1) }}
              </span>
            </div>
            <button
              class="btn btn-sm"
              :class="rec.direction_comparison.selected === option.id && rec.direction_comparison.locked ? 'btn-ghost' : 'btn-primary'"
              :disabled="locking || (rec.direction_comparison.selected === option.id && rec.direction_comparison.locked)"
              @click="lockDirection(option)"
            >
              <UiIcon :name="rec.direction_comparison.selected === option.id && rec.direction_comparison.locked ? 'check' : 'target'" :size="13" />
              {{ rec.direction_comparison.selected === option.id && rec.direction_comparison.locked ? '已锁定该方向' : '锁定此方向' }}
            </button>
          </article>
        </div>
      </section>

      <div class="rec-layout">
        <div class="rec-main">
          <section class="tier-panel card reveal reveal-2">
            <div class="tier-head">
              <div>
                <h3>第二步：选一套课表</h3>
                <p>三档方案均在学分上限与时间不冲突下求解，可继续手动增减。</p>
              </div>
              <div class="tier-tabs">
                <button
                  v-for="plan in rec.plans"
                  :key="plan.key"
                  :class="{ active: tier === plan.key, custom: tier === 'custom' }"
                  @click="applyTier(plan)"
                >
                  <strong>{{ plan.name }}</strong>
                  <span>{{ plan.total_with_locked.toFixed(1) }} 分</span>
                </button>
              </div>
            </div>

            <div class="credit-meter">
              <div class="meter-top">
                <span>
                  新增 <strong>{{ selectedCredits.toFixed(1) }}</strong> 分 ·
                  含在修 <strong>{{ totalWithLocked.toFixed(1) }}</strong> 分
                </span>
                <span class="muted small">建议上限 {{ activeBudget }} 分</span>
              </div>
              <div class="meter-bar">
                <i :style="{ width: `${Math.min(100, (totalWithLocked / 28) * 100)}%` }" :class="{ over: totalWithLocked > 28 }" />
                <span class="meter-tick" style="left: 71.4%">20</span>
                <span class="meter-tick" style="left: 85.7%">24</span>
                <span class="meter-tick" style="left: 100%">28</span>
              </div>
            </div>

            <div class="course-list-head">
              <div class="filter-tabs">
                <button v-for="tab in courseTabs" :key="tab.key" :class="{ active: courseTab === tab.key }" @click="selectCourseTab(tab.key)">
                  {{ tab.label }}
                  <span v-if="tab.key === 'available'" class="tab-count">{{ rec.candidates.length }}</span>
                  <span v-if="tab.key === 'blocked'" class="tab-count danger">{{ rec.blocked.length }}</span>
                </button>
              </div>
              <span class="hint">按优先级排序 · 分数越高越紧迫</span>
            </div>

            <div class="course-grid">
              <article
                v-for="course in visibleCandidates"
                :key="course.code"
                class="course-card"
                :class="{ selected: selectedCodes.has(course.code), conflict: course.status === 'conflict' }"
              >
                <div class="cc-top">
                  <span class="cc-code">{{ course.code }}</span>
                  <div class="row" style="gap: 6px">
                    <span class="cc-score" :class="scoreTone(course.score)">{{ course.score.toFixed(0) }}</span>
                    <StatusPill :status="course.status" />
                  </div>
                </div>
                <h4>{{ course.name }}</h4>
                <div class="cc-meta">
                  <span>{{ course.credit.toFixed(1) }} 学分</span>
                  <span>{{ course.module_name }}</span>
                  <span>{{ course.assessment }}</span>
                  <span v-if="course.required_child" class="cc-required">必选子项</span>
                </div>
                <p class="cc-reason">{{ course.reasons[0] || '按培养要求推荐' }}</p>
                <ul v-if="course.consequences.length" class="cc-cons">
                  <li v-for="(item, idx) in course.consequences.slice(0, 2)" :key="idx">{{ item }}</li>
                </ul>
                <div v-if="course.conflicts.length" class="cc-conflict">
                  <UiIcon name="alert" :size="12" />
                  {{ course.conflicts[0] }}
                </div>
                <div class="cc-foot">
                  <div class="cc-offering" v-if="course.offering">
                    <UiIcon name="calendar" :size="12" />
                    {{ course.offering.time_slots.join(' / ') }} · {{ course.offering.teacher }}
                  </div>
                  <div class="cc-diff" v-if="course.difficulty?.avg_score">
                    均分 {{ course.difficulty.avg_score }} · 挂科 {{ (course.difficulty.fail_rate * 100).toFixed(0) }}%
                  </div>
                  <button
                    class="cc-toggle"
                    :class="{ added: selectedCodes.has(course.code) }"
                    @click="toggleCourse(course)"
                  >
                    <UiIcon :name="selectedCodes.has(course.code) ? 'check' : 'plus'" :size="12" />
                    {{ selectedCodes.has(course.code) ? '已加入' : '加入课表' }}
                  </button>
                </div>
              </article>

              <article v-for="course in visibleBlocked" :key="course.code" class="course-card blocked">
                <div class="cc-top">
                  <span class="cc-code">{{ course.code }}</span>
                  <StatusPill :status="course.status" />
                </div>
                <h4>{{ course.name }}</h4>
                <div class="cc-meta">
                  <span>{{ course.credit.toFixed(1) }} 学分</span>
                  <span>{{ course.module_name }}</span>
                </div>
                <p class="cc-reason">
                  <template v-if="course.status === 'prereq_missing'">
                    先修未满足：{{ course.prereq_missing.join('、') }}
                  </template>
                  <template v-else-if="course.status === 'not_offered'">本学期开课计划中没有该课程，需关注后续学期。</template>
                  <template v-else-if="course.status === 'other_direction'">属于其他专业方向，锁定方向后不参与推荐。</template>
                  <template v-else-if="course.status === 'full'">容量已满，可尝试候补或选择其他班级。</template>
                  <template v-else>当前不满足硬约束。</template>
                </p>
              </article>

              <div v-if="!visibleCandidates.length && !visibleBlocked.length" class="empty" style="grid-column: 1/-1; padding: 44px">
                没有符合当前筛选的课程
              </div>
            </div>

            <button
              v-if="courseTab === 'available' && !showAll && rec.candidates.length > 8"
              class="show-all"
              @click="showAll = true"
            >
              显示全部 {{ rec.candidates.length }} 门可选课程
              <UiIcon name="chevron-down" :size="14" />
            </button>
          </section>

          <section class="feasibility card reveal reveal-3">
            <div class="card-head">
              <div>
                <h3>毕业可行性预检</h3>
                <p class="hint">学制 3–6 年，“能不能毕业”要按 3 / 4 / 5 年三个情景分别算。</p>
              </div>
              <span class="chip chip-info">剩余缺口 {{ rec.summary.gap.toFixed(1) }} 分</span>
            </div>
            <div class="scene-grid">
              <article
                v-for="scene in rec.feasibility.scenarios"
                :key="scene.years"
                class="scene"
                :class="{ feasible: scene.credits_feasible, recommended: scene.years === rec.feasibility.earliest_feasible_years }"
              >
                <div class="scene-top">
                  <strong>{{ scene.label }}</strong>
                  <span class="scene-state">{{ scene.credits_feasible ? '可行' : '不可行' }}</span>
                </div>
                <div class="scene-num">
                  <strong>{{ scene.per_term.toFixed(1) }}</strong>
                  <span>学分 / 学期</span>
                </div>
                <div class="scene-meta">
                  <span>剩余 {{ scene.remaining_terms }} 学期</span>
                  <span>缺口 {{ scene.gap.toFixed(1) }}</span>
                </div>
                <p>{{ scene.verdict }}</p>
                <div v-if="scene.blocked_courses.length" class="scene-blocked">
                  阻塞：{{ scene.blocked_courses.slice(0, 2).map((c) => c.name).join('、') }}
                </div>
              </article>
            </div>
            <p class="feas-summary">{{ rec.feasibility.summary }}</p>
            <div v-if="rec.feasibility.non_credit_blockers.length" class="feas-blockers">
              <UiIcon name="alert" :size="14" />
              <div>
                <strong>非学分卡点</strong>
                <span v-for="blocker in rec.feasibility.non_credit_blockers" :key="blocker">{{ blocker }}</span>
              </div>
            </div>
          </section>
        </div>

        <aside class="rec-side">
          <section class="card card-pad schedule-card">
            <div class="card-head">
              <h3>课表预览</h3>
              <span class="chip chip-line">{{ selectedCourses.length + rec.locked_courses.length }} 门 · {{ scheduleCredits.toFixed(1) }} 分</span>
            </div>
            <div class="timetable-grid">
              <div class="tt-head tt-corner">节次</div>
              <div v-for="day in days" :key="`h-${day}`" class="tt-head">{{ day }}</div>
              <template v-for="period in periods" :key="`p-${period}`">
                <div class="tt-period" :style="{ gridRow: period + 1, gridColumn: 1 }">{{ period }}</div>
                <template v-for="(day, dayIndex) in days" :key="`${day}-${period}`">
                  <div
                    v-if="cellAt(day, period)?.show"
                    class="tt-cell filled"
                    :class="cellAt(day, period).tone"
                    :style="{
                      gridRow: `${period + 1} / span ${cellAt(day, period).span}`,
                      gridColumn: dayIndex + 2,
                    }"
                  >
                    <strong>{{ cellAt(day, period).name }}</strong>
                    <span>{{ cellAt(day, period).room }}</span>
                  </div>
                  <div
                    v-else-if="!cellAt(day, period)?.skip"
                    class="tt-cell"
                    :style="{ gridRow: period + 1, gridColumn: dayIndex + 2 }"
                  />
                </template>
              </template>
            </div>
            <div v-if="unscheduled.length" class="unscheduled">
              <span class="hint">非排课时间</span>
              <span v-for="item in unscheduled" :key="item.code" class="unscheduled-item">{{ item.name }}</span>
            </div>
            <div class="schedule-legend">
              <span><i class="lg selected" />新增</span>
              <span><i class="lg locked" />在修/已锁定</span>
              <span><i class="lg danger" />冲突</span>
            </div>
          </section>

          <section class="card card-pad whatif-card">
            <div class="card-head">
              <h3>情景模拟</h3>
              <span class="hint">What-if</span>
            </div>
            <p class="hint" style="margin-bottom: 10px">假设某门课挂科，缺口与模块会怎样变化？</p>
            <div class="row" style="gap: 8px">
              <select v-model="simulateCode" class="select" style="height: 36px; font-size: 11.5px">
                <option value="">选择一门课</option>
                <option v-for="course in simulateOptions" :key="course.code" :value="course.code">
                  {{ course.name }}（{{ course.credit.toFixed(1) }}）
                </option>
              </select>
              <button class="btn btn-sm btn-primary" :disabled="!simulateCode || simulating" @click="runSimulation">
                {{ simulating ? '计算中…' : '模拟' }}
              </button>
            </div>
            <div v-if="simulation" class="sim-result">
              <div class="sim-head">
                <strong>{{ simulation.course.name }}</strong>
                <span class="chip" :class="simulation.gap_delta > 0 ? 'chip-danger' : 'chip-warn'">
                  缺口 {{ simulation.summary_before.gap.toFixed(1) }} → {{ simulation.summary_after.gap.toFixed(1) }}
                </span>
              </div>
              <p>{{ simulation.verdict }}</p>
              <div v-for="change in simulation.module_changes.slice(0, 3)" :key="change.id" class="sim-change">
                <span>{{ change.name }}</span>
                <span>{{ change.gap_before.toFixed(1) }} → {{ change.gap_after.toFixed(1) }}</span>
              </div>
            </div>
          </section>

          <section class="card card-pad plan-summary">
            <div class="card-head">
              <h3>{{ tierLabel }}</h3>
              <span class="chip chip-line">{{ totalWithLocked.toFixed(1) }} / {{ activeBudget }} 分</span>
            </div>
            <div class="summary-list">
              <div v-for="course in selectedCourses" :key="course.code" class="summary-item">
                <span class="summary-dot" />
                <div>
                  <strong>{{ course.name }}</strong>
                  <span>{{ course.credit.toFixed(1) }} 分 · {{ course.offering?.time_slots?.join(' / ') || '时间待定' }}</span>
                </div>
                <button class="summary-remove" @click="toggleCourse(course)">
                  <UiIcon name="close" :size="12" />
                </button>
              </div>
              <div v-if="!selectedCourses.length" class="empty" style="padding: 20px">还没有加入课程</div>
            </div>
            <div v-if="planWarnings.length" class="plan-warnings">
              <span v-for="warning in planWarnings" :key="warning">
                <UiIcon name="alert" :size="12" />{{ warning }}
              </span>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <div v-else class="empty card" style="padding: 60px">
      <UiIcon name="alert" :size="26" />
      <p>选课建议加载失败</p>
      <button class="btn" @click="load">重试</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatusPill from '@/components/StatusPill.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useToastStore } from '@/stores/toast'

const meta = useMetaStore()
const toast = useToastStore()

const loading = ref(true)
const rec = ref(null)
const tier = ref('balanced')
const selectedCodes = ref(new Set())
const courseTab = ref('available')
const showAll = ref(false)
const simulateCode = ref('')
const simulation = ref(null)
const simulating = ref(false)
const locking = ref(false)

const days = ['周一', '周二', '周三', '周四', '周五']
const periods = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

const courseTabs = computed(() => [
  { key: 'available', label: '可选推荐' },
  { key: 'selected', label: '已加入' },
  { key: 'blocked', label: '硬约束拦截' },
])

const activePlan = computed(() => rec.value?.plans.find((p) => p.key === tier.value) || null)
const activeBudget = computed(() => activePlan.value?.budget || 28)
const tierLabel = computed(() => (tier.value === 'custom' ? '自定义方案' : activePlan.value?.name || '方案'))
const planWarnings = computed(() => (tier.value === 'custom' ? [] : activePlan.value?.warnings || []))

const selectedCourses = computed(() => {
  if (!rec.value) return []
  return rec.value.candidates.filter((c) => selectedCodes.value.has(c.code))
})

const selectedCredits = computed(() => selectedCourses.value.reduce((sum, c) => sum + c.credit, 0))
const totalWithLocked = computed(() => selectedCredits.value + (rec.value?.current_credits || 0))

const visibleCandidates = computed(() => {
  if (!rec.value) return []
  if (courseTab.value === 'blocked') return []
  if (courseTab.value === 'selected') return rec.value.candidates.filter((c) => selectedCodes.value.has(c.code))
  return showAll.value ? rec.value.candidates : rec.value.candidates.slice(0, 8)
})

const visibleBlocked = computed(() => {
  if (!rec.value || courseTab.value !== 'blocked') return []
  return rec.value.blocked
})

const simulateOptions = computed(() => {
  if (!rec.value) return []
  const map = new Map()
  for (const course of rec.value.audit.passed_courses) map.set(course.code, course)
  for (const course of rec.value.candidates) map.set(course.code, course)
  return Array.from(map.values()).sort((a, b) => b.credit - a.credit).slice(0, 30)
})

/* ---- timetable ---- */
const slotMap = computed(() => {
  const map = {}
  const add = (course, locked) => {
    const slots = course.offering?.time_slots || course.slots || []
    for (const slot of slots) {
      const [day, period] = String(slot).split(' ')
      if (!day || !period) continue
      const [start, end] = period.split('-').map(Number)
      for (let p = start; p <= (end || start); p++) {
        const key = `${day}-${p}`
        const existing = map[key]
        const cell = {
          name: course.name,
          code: course.code,
          locked,
          tone: locked ? 'locked' : 'selected',
          day,
          period: p,
        }
        if (existing && existing.code !== course.code) {
          existing.tone = 'danger'
          cell.tone = 'danger'
        }
        map[key] = cell
      }
    }
  }
  for (const course of rec.value?.locked_courses || []) add(course, true)
  for (const course of selectedCourses.value) add(course, false)
  return map
})

const cellGrid = computed(() => {
  const grid = {}
  for (const day of days) {
    grid[day] = {}
    for (const p of periods) grid[day][p] = null
  }
  for (const [key, value] of Object.entries(slotMap.value)) {
    const [day, p] = key.split('-')
    grid[day][Number(p)] = value
  }
  const result = {}
  for (const day of days) {
    result[day] = {}
    let p = 1
    while (p <= periods.length) {
      const cell = grid[day][p]
      if (!cell) {
        result[day][p] = { skip: false, show: false }
        p += 1
        continue
      }
      let span = 1
      while (grid[day][p + span] && grid[day][p + span].code === cell.code) span += 1
      result[day][p] = { show: true, span, ...cell }
      for (let i = 1; i < span; i++) result[day][p + i] = { skip: true, show: false }
      p += span
    }
  }
  return result
})

function cellAt(day, period) {
  return cellGrid.value?.[day]?.[period]
}

const unscheduled = computed(() => {
  return [...selectedCourses.value, ...(rec.value?.locked_courses || [])].filter((course) => {
    const slots = course.offering?.time_slots || course.slots || []
    return !slots.some((slot) => String(slot).includes(' '))
  })
})

const scheduleCredits = computed(() => {
  const credits = new Map()
  for (const course of [...(rec.value?.locked_courses || []), ...selectedCourses.value]) {
    credits.set(course.code, Number(course.credit || 0))
  }
  return [...credits.values()].reduce((sum, credit) => sum + credit, 0)
})

/* ---- actions ---- */
function applyTier(plan) {
  tier.value = plan.key
  selectedCodes.value = new Set(plan.courses.map((c) => c.code))
}

function selectCourseTab(key) {
  courseTab.value = key
  showAll.value = false
}

function toggleCourse(course) {
  const next = new Set(selectedCodes.value)
  const removing = next.has(course.code)
  if (removing) next.delete(course.code)
  else next.add(course.code)
  selectedCodes.value = next
  tier.value = 'custom'
  if (removing) {
    toast.info(`已移出课表：${course.name}`)
  } else if (course.conflicts?.length) {
    toast.info(`已加入 ${course.name}，但需处理时间冲突`)
  } else {
    toast.success(`已加入课表：${course.name}`)
  }
}

async function lockDirection(option) {
  if (locking.value) return
  locking.value = true
  try {
    const result = await api.lockDirection(option.id)
    toast.success(result.message)
    await load()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    locking.value = false
  }
}

async function runSimulation() {
  if (!simulateCode.value) return
  simulating.value = true
  try {
    simulation.value = await api.simulate(simulateCode.value)
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    simulating.value = false
  }
}

function scoreTone(score) {
  if (score >= 55) return 'high'
  if (score >= 35) return 'mid'
  return 'low'
}

async function load() {
  loading.value = true
  try {
    rec.value = await api.recommend()
    const balanced = rec.value.plans.find((p) => p.key === 'balanced') || rec.value.plans[0]
    if (balanced) {
      tier.value = balanced.key
      selectedCodes.value = new Set(balanced.courses.map((c) => c.code))
    }
  } catch (error) {
    toast.error(getErrorMessage(error))
    rec.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.direction-panel {
  padding: 22px 24px;
}

.direction-title {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.direction-title h3 {
  font-size: 17px;
}

.direction-title p {
  margin-top: 7px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.6;
  max-width: 720px;
}

.direction-lock {
  display: grid;
  justify-items: end;
  gap: 2px;
  flex: none;
}

.direction-lock strong {
  font-size: 13px;
  color: var(--violet);
}

.direction-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.direction-card {
  position: relative;
  display: grid;
  gap: 10px;
  padding: 15px;
  border-radius: 15px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.55);
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}

.direction-card:hover {
  transform: translateY(-2px);
  border-color: rgba(30, 78, 216, 0.22);
  box-shadow: var(--shadow-sm);
}

.direction-card.recommended {
  border-color: rgba(30, 78, 216, 0.3);
  background: linear-gradient(160deg, rgba(30, 78, 216, 0.055), rgba(255, 255, 255, 0.7));
}

.direction-card.locked {
  box-shadow: 0 0 0 1px rgba(18, 131, 111, 0.25);
}

.dc-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dc-name {
  font-size: 14px;
  font-weight: 700;
}

.dc-rec {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 99px;
  color: #fff;
  background: var(--grad);
}

.dc-locked {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  color: #0b6b5b;
  margin-left: auto;
}

.dc-progress {
  display: flex;
  align-items: center;
  gap: 9px;
}

.dc-bar {
  flex: 1;
  height: 5px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.06);
  overflow: hidden;
}

.dc-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--grad);
}

.dc-progress strong {
  font-family: var(--font-mono);
  font-size: 11px;
}

.dc-progress strong span {
  color: var(--muted-2);
}

.dc-reason {
  font-size: 10.5px;
  color: var(--muted);
  line-height: 1.55;
  min-height: 32px;
}

.dc-courses {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.dc-course {
  font-size: 8.5px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.045);
  color: var(--muted);
}

.dc-course.earned {
  background: rgba(18, 131, 111, 0.08);
  color: #0b6b5b;
}

.dc-course.conflict {
  background: rgba(184, 69, 63, 0.08);
  color: #96332e;
}

.direction-card .btn {
  justify-self: start;
}

.rec-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(380px, 0.8fr);
  gap: 20px;
  margin-top: 18px;
  align-items: start;
}

.rec-main,
.rec-side {
  display: grid;
  gap: 18px;
}

.tier-panel {
  padding: 22px;
}

.tier-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}

.tier-head h3 {
  font-size: 17px;
}

.tier-head p {
  margin-top: 6px;
  color: var(--muted);
  font-size: 11px;
}

.tier-tabs {
  display: flex;
  gap: 5px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(21, 32, 43, 0.04);
}

.tier-tabs button {
  display: grid;
  gap: 1px;
  padding: 6px 12px;
  border-radius: 9px;
  color: var(--muted);
  min-width: 78px;
}

.tier-tabs button strong {
  font-size: 11px;
}

.tier-tabs button span {
  font-family: var(--font-mono);
  font-size: 9.5px;
}

.tier-tabs button.active {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 3px 9px rgba(12, 22, 48, 0.08);
}

.credit-meter {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(21, 32, 43, 0.025);
}

.meter-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 9px;
}

.meter-top strong {
  color: var(--ink);
  font-family: var(--font-mono);
}

.meter-bar {
  position: relative;
  height: 7px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.06);
  overflow: visible;
}

.meter-bar > i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--grad);
  transition: width 0.8s ease;
}

.meter-bar > i.over {
  background: linear-gradient(90deg, #f59e0b, #f43f5e);
}

.meter-tick {
  position: absolute;
  top: 10px;
  font-size: 8px;
  color: var(--muted-2);
  transform: translateX(-50%);
}

.course-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 18px 0 12px;
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
  display: inline-flex;
  align-items: center;
  gap: 5px;
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

.tab-count {
  font-size: 8.5px;
  padding: 0 4px;
  border-radius: 99px;
  background: rgba(30, 78, 216, 0.1);
  color: var(--violet);
}

.tab-count.danger {
  background: rgba(184, 69, 63, 0.1);
  color: #96332e;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.show-all {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 38px;
  margin-top: 12px;
  border-radius: 10px;
  border: 1px dashed var(--line-strong);
  color: var(--muted);
  font-size: 10.5px;
  background: rgba(255, 255, 255, 0.45);
  transition: color 0.2s ease, border-color 0.2s ease;
}

.show-all:hover {
  color: var(--violet);
  border-color: rgba(30, 78, 216, 0.35);
}

.course-card {
  position: relative;
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.6);
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: rgba(30, 78, 216, 0.18);
}

.course-card.selected {
  border-color: rgba(18, 131, 111, 0.35);
  background: rgba(18, 131, 111, 0.035);
}

.course-card.conflict,
.course-card.blocked {
  background: rgba(21, 32, 43, 0.025);
  opacity: 0.82;
}

.cc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.cc-code {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted-2);
}

.cc-score {
  display: grid;
  place-items: center;
  min-width: 24px;
  height: 20px;
  padding: 0 5px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
}

.cc-score.high {
  color: #96332e;
  background: rgba(184, 69, 63, 0.1);
}

.cc-score.mid {
  color: #94530f;
  background: rgba(178, 106, 27, 0.12);
}

.cc-score.low {
  color: var(--muted);
  background: rgba(21, 32, 43, 0.05);
}

.course-card h4 {
  font-size: 14px;
  font-weight: 700;
}

.cc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 9px;
  font-size: 10.5px;
  color: var(--muted-2);
}

.cc-required {
  color: #96332e;
  background: rgba(184, 69, 63, 0.07);
  padding: 0 5px;
  border-radius: 4px;
}

.cc-reason {
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--muted);
  text-wrap: pretty;
}

.cc-cons {
  display: grid;
  gap: 3px;
  padding-left: 12px;
  list-style: disc;
}

.cc-cons li {
  font-size: 10.5px;
  color: var(--muted-2);
  line-height: 1.55;
}

.cc-cons li::marker {
  color: var(--amber);
}

.cc-conflict {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 5px 7px;
  border-radius: 7px;
  background: rgba(184, 69, 63, 0.06);
  color: #96332e;
  font-size: 9.5px;
  line-height: 1.45;
}

.cc-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 7px;
  border-top: 1px dashed var(--line);
  flex-wrap: wrap;
}

.cc-offering,
.cc-diff {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--muted-2);
}

.cc-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 27px;
  padding: 0 9px;
  margin-left: auto;
  border-radius: 7px;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--violet);
  background: rgba(30, 78, 216, 0.08);
  transition: background 0.2s ease, color 0.2s ease;
}

.cc-toggle:hover {
  background: rgba(30, 78, 216, 0.14);
}

.cc-toggle.added {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.1);
}

.feasibility {
  padding: 22px;
}

.feasibility .card-head p {
  margin-top: 4px;
}

.scene-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.scene {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(184, 69, 63, 0.025);
}

.scene.feasible {
  background: rgba(18, 131, 111, 0.03);
  border-color: rgba(18, 131, 111, 0.14);
}

.scene.recommended {
  box-shadow: 0 0 0 1px rgba(30, 78, 216, 0.28);
}

.scene-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scene-top strong {
  font-size: 12px;
}

.scene-state {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 99px;
  color: #96332e;
  background: rgba(184, 69, 63, 0.1);
}

.scene.feasible .scene-state {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.12);
}

.scene-num {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.scene-num strong {
  font-family: var(--font-display);
  font-size: 27px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.scene-num span {
  font-size: 9px;
  color: var(--muted-2);
}

.scene-meta {
  display: flex;
  gap: 9px;
  font-size: 9px;
  color: var(--muted-2);
}

.scene p {
  font-size: 9.5px;
  color: var(--muted);
  line-height: 1.5;
}

.scene-blocked {
  font-size: 9px;
  color: #96332e;
  background: rgba(184, 69, 63, 0.06);
  padding: 4px 6px;
  border-radius: 5px;
}

.feas-summary {
  margin-top: 14px;
  font-size: 11px;
  color: var(--muted);
  line-height: 1.65;
  padding: 11px 13px;
  border-radius: 10px;
  background: rgba(21, 32, 43, 0.025);
}

.feas-blockers {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(178, 106, 27, 0.06);
  color: #92400e;
}

.feas-blockers strong {
  display: block;
  font-size: 10px;
  margin-bottom: 3px;
}

.feas-blockers span {
  display: block;
  font-size: 9.5px;
  line-height: 1.5;
}

.schedule-card {
  padding-bottom: 16px;
}

.timetable-grid {
  display: grid;
  grid-template-columns: 30px repeat(5, minmax(0, 1fr));
  grid-auto-rows: 27px;
  gap: 3px;
  font-size: 9px;
}

.tt-head {
  display: grid;
  place-items: center;
  font-size: 8.5px;
  color: var(--muted-2);
  padding-bottom: 2px;
}

.tt-corner {
  justify-items: start;
  padding-left: 2px;
}

.tt-period {
  display: grid;
  place-items: center;
  color: var(--muted-2);
  font-family: var(--font-mono);
  font-size: 7.5px;
}

.tt-cell {
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.025);
  min-height: 25px;
}

.tt-cell.filled {
  display: grid;
  align-content: center;
  gap: 1px;
  padding: 2px 4px;
  background: linear-gradient(135deg, rgba(30, 78, 216, 0.12), rgba(47, 102, 232, 0.08));
  border: 1px solid rgba(30, 78, 216, 0.16);
  overflow: hidden;
}

.tt-cell.filled strong {
  font-size: 9px;
  line-height: 1.25;
  font-weight: 600;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.tt-cell.filled span {
  font-size: 7.5px;
  color: var(--muted-2);
}

.tt-cell.filled.locked {
  background: rgba(21, 32, 43, 0.05);
  border-color: rgba(21, 32, 43, 0.08);
}

.tt-cell.filled.danger {
  background: rgba(184, 69, 63, 0.1);
  border-color: rgba(184, 69, 63, 0.2);
}

.unscheduled {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  margin-top: 9px;
}

.unscheduled-item {
  font-size: 8.5px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted);
}

.schedule-legend {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px dashed var(--line);
  font-size: 8.5px;
  color: var(--muted-2);
}

.schedule-legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.lg {
  width: 6px;
  height: 6px;
  border-radius: 2px;
  background: var(--green);
}

.lg.selected {
  background: var(--violet);
}

.lg.locked {
  background: var(--muted-2);
}

.lg.danger {
  background: var(--rose);
}

.whatif-card p {
  color: var(--muted);
}

.sim-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 11px;
  background: rgba(178, 106, 27, 0.055);
  border: 1px solid rgba(178, 106, 27, 0.12);
}

.sim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sim-head strong {
  font-size: 11.5px;
}

.sim-result p {
  margin: 6px 0 8px;
  font-size: 9.5px;
  line-height: 1.55;
  color: #92400e;
}

.sim-change {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 9.5px;
  color: var(--muted);
  padding: 3px 0;
  border-top: 1px dashed rgba(178, 106, 27, 0.16);
}

.plan-summary {
  padding-bottom: 24px;
}

.summary-list {
  display: grid;
  gap: 5px;
  max-height: none;
  overflow-y: visible;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 4px;
  border-bottom: 1px solid var(--line);
}

.summary-item:last-child {
  border-bottom: 0;
}

.summary-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--violet);
  flex: none;
}

.summary-item div {
  display: grid;
  flex: 1;
  min-width: 0;
}

.summary-item strong {
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-item span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.summary-remove {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  display: grid;
  place-items: center;
  color: var(--muted-2);
}

.summary-remove:hover {
  background: rgba(184, 69, 63, 0.08);
  color: #96332e;
}

.plan-warnings {
  display: grid;
  gap: 4px;
  margin-top: 10px;
}

.plan-warnings span {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  font-size: 9px;
  color: #94530f;
  line-height: 1.45;
}

@media (max-width: 1200px) {
  .rec-layout {
    grid-template-columns: 1fr;
  }

  .direction-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .course-grid {
    grid-template-columns: 1fr;
  }

  .scene-grid {
    grid-template-columns: 1fr;
  }

  .direction-title {
    flex-direction: column;
  }

  .tier-head {
    flex-direction: column;
  }

  .direction-grid {
    grid-template-columns: 1fr;
  }
}
</style>
