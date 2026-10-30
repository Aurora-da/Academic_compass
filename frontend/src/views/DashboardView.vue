<template>
  <div class="page dashboard">
    <div v-if="loading" class="grid" style="gap: 18px">
      <div class="skeleton" style="height: 230px" />
      <div class="grid g4">
        <div v-for="i in 4" :key="i" class="skeleton" style="height: 116px" />
      </div>
      <div class="skeleton" style="height: 360px" />
    </div>

    <template v-else-if="audit">
      <div class="page-head dash-head">
        <div>
          <h1 class="page-title">学业总览</h1>
          <p class="page-sub">
            {{ audit.as_of }} · {{ programTermLabel }} · 毕业预演
            <span class="head-sep">/</span>
            先看风险，再看模块，最后决定这学期怎么排。
          </p>
        </div>
        <div class="head-actions">
          <span class="chip" :class="`chip-${riskGrade.tone}`">
            <span class="dot" :class="riskGrade.dot" />
            {{ riskGrade.label }}
          </span>
          <button class="btn btn-sm" :disabled="refreshing" @click="load(true)">
            <UiIcon name="refresh" :size="14" />
            {{ refreshing ? '刷新中…' : '刷新数据' }}
          </button>
        </div>
      </div>

      <section class="hero card reveal" :class="`hero-${riskGrade.tone}`">
        <div class="hero-glow" />
        <div class="hero-left">
          <div class="hero-topline">
            <span class="chip chip-line">
              <UiIcon name="calendar" :size="13" />
              {{ audit.as_of }} · {{ programTermLabel }}
            </span>
            <span class="chip" :class="audit.graduation.ok ? 'chip-ok' : 'chip-warn'">
              <span class="dot" :class="audit.graduation.ok ? '' : 'warn'" />
              {{ audit.graduation.ok ? '毕业条件已全部满足' : '毕业条件尚未全部满足' }}
            </span>
          </div>

          <div class="hero-kicker">本学期学业判断</div>
          <h2 class="hero-title">{{ riskGrade.title }}</h2>
          <p class="hero-desc">{{ riskSummary }}</p>

          <div v-if="diff" class="diff-pill reveal-2">
            <span class="diff-icon"><UiIcon name="chart" :size="14" /></span>
            <span>{{ diff.headline }}</span>
            <span class="diff-tag">较 {{ diff.from.semester }}</span>
          </div>

          <div class="hero-signals">
            <div v-for="signal in signals" :key="signal.label" class="hero-signal">
              <span>{{ signal.label }}</span>
              <strong :class="signal.tone">{{ signal.value }}</strong>
              <small>{{ signal.hint }}</small>
            </div>
          </div>

          <div class="hero-actions">
            <router-link to="/recommend" class="btn btn-primary">
              <UiIcon name="compass" :size="16" />
              这学期选什么
            </router-link>
            <router-link to="/report" class="btn">
              <UiIcon name="report" :size="16" />
              查看学业报告
            </router-link>
            <button class="btn btn-ghost" :disabled="refreshing" @click="load(true)">
              <UiIcon name="refresh" :size="15" />
              {{ refreshing ? '刷新中…' : '刷新' }}
            </button>
          </div>
        </div>

        <div class="hero-right">
          <CreditRing :percent="audit.summary.percent" :size="180" :stroke="11" caption="学分完成度" />
          <div class="ring-stats">
            <div>
              <span>已获</span>
              <strong><CountUp :value="audit.summary.earned" :decimals="1" /></strong>
            </div>
            <div>
              <span>缺口</span>
              <strong class="warn"><CountUp :value="audit.summary.gap" :decimals="1" /></strong>
            </div>
            <div>
              <span>在修</span>
              <strong><CountUp :value="audit.summary.studying" :decimals="1" /></strong>
            </div>
          </div>
          <div class="health-line" :title="healthExplain">
            <span>学业健康度</span>
            <strong>{{ healthScore }}</strong>
            <span class="health-tag" :class="healthTone">{{ healthLabel }}</span>
          </div>
          <p class="health-explain">{{ healthExplain }}</p>
        </div>
      </section>

      <section class="grid g4 stats reveal reveal-2">
        <article v-for="stat in statCards" :key="stat.label" class="stat-card card card-hover" :class="[stat.tone, { highlight: stat.tone === 'amber' }]">
          <div class="stat-icon" :class="stat.tone">
            <UiIcon :name="stat.icon" :size="18" />
          </div>
          <div class="stat-meta">
            <span>{{ stat.label }}</span>
            <strong>
              <CountUp :value="stat.value" :decimals="1" />
              <i>{{ stat.unit }}</i>
            </strong>
            <small>{{ stat.hint }}</small>
          </div>
          <div class="stat-bar"><i :style="{ width: `${stat.progress}%`, background: stat.color }" /></div>
        </article>
      </section>

      <div class="dash-grid reveal reveal-3">
        <div class="dash-main">
          <section class="card card-pad module-card">
            <div class="card-head">
              <div class="row">
                <h3>七个模块的进度</h3>
                <span class="chip chip-line">{{ moduleStats }}</span>
              </div>
              <router-link to="/plan" class="btn btn-sm btn-ghost">
                查看方案树
                <UiIcon name="arrow-right" :size="14" />
              </router-link>
            </div>

            <div class="module-list">
              <button
                v-for="(module, index) in audit.modules"
                :key="module.id"
                class="module-row"
                :style="{ animationDelay: `${index * 45}ms` }"
                @click="openModule(module.id)"
              >
                <div class="module-main">
                  <div class="module-top">
                    <div class="module-name">
                      <span class="module-dot" :class="moduleTone(module)" />
                      <strong>{{ module.name }}</strong>
                      <span v-if="module.mode === 'any_of' && module.picked_name" class="mode-tag">
                        {{ module.picked_name }}
                      </span>
                      <span v-else-if="module.mode === 'free'" class="mode-tag">复合约束</span>
                      <span v-else-if="module.mode === 'any_of'" class="mode-tag">三选一</span>
                    </div>
                    <div class="module-num">
                      <strong>{{ module.earned.toFixed(1) }}</strong>
                      <span>/ {{ module.require.toFixed(1) }}</span>
                    </div>
                  </div>
                  <div class="module-progress">
                    <i
                      :style="{ width: `${Math.min(100, (module.earned / module.require) * 100)}%` }"
                      :class="moduleTone(module)"
                    />
                  </div>
                  <div class="module-foot">
                    <span v-if="module.gap > 0" class="gap-text">缺 {{ module.gap.toFixed(1) }} 学分</span>
                    <span v-if="module.over > 0" class="over-text">超修 {{ module.over.toFixed(1) }}（封顶不计）</span>
                    <span v-if="structureNote(module)" class="structure-text">{{ structureNote(module) }}</span>
                    <span class="module-status"><StatusPill :status="module.status" /></span>
                  </div>
                </div>
                <UiIcon name="chevron" :size="16" class="module-arrow" />
              </button>
            </div>
          </section>

          <div class="charts-grid">
            <section class="card card-pad chart-card">
              <div class="card-head">
                <h3>学期缺口变化</h3>
                <span class="hint">快照 diff</span>
              </div>
              <EChart :option="trendOption" height="212px" />
            </section>
            <section class="card card-pad chart-card">
              <div class="card-head">
                <h3>学业结构雷达</h3>
                <span class="hint">六维自检</span>
              </div>
              <EChart :option="radarOption" height="212px" />
            </section>
          </div>
        </div>

        <aside class="dash-side">
          <section class="card card-pad grad-card">
            <div class="card-head">
              <h3>毕业三条件</h3>
              <span class="chip" :class="audit.graduation.ok ? 'chip-ok' : 'chip-warn'">
                {{ audit.graduation.ok ? '全部通过' : '尚未全部满足' }}
              </span>
            </div>
            <div class="grad-list">
              <div v-for="item in graduationItems" :key="item.key" class="grad-item" :class="item.state">
                <span class="grad-ic"><UiIcon :name="item.icon" :size="15" /></span>
                <div class="grad-meta">
                  <strong>{{ item.label }}</strong>
                  <span>{{ item.detail }}</span>
                </div>
                <span class="grad-state" :class="item.state">
                  {{ item.state === 'ok' ? '已完成' : item.state === 'warn' ? '待确认' : '未完成' }}
                </span>
              </div>
            </div>
            <router-link to="/report" class="grad-link">
              展开完整报告与第二课堂明细
              <UiIcon name="arrow-right" :size="14" />
            </router-link>
          </section>

          <section class="card card-pad risk-card">
            <div class="card-head">
              <h3>风险雷达</h3>
              <span class="chip chip-danger">
                {{ riskCounts.high }} 高 · {{ riskCounts.medium }} 中
              </span>
            </div>
            <div class="risk-list">
              <div v-for="(risk, index) in audit.risks.slice(0, 5)" :key="index" class="risk-item" :class="risk.level">
                <span class="risk-dot" />
                <div>
                  <p>{{ risk.msg }}</p>
                  <span class="risk-type">{{ riskType(risk.type) }}</span>
                  <span class="risk-severity">{{ risk.level === 'high' ? '高风险' : '需关注' }}</span>
                </div>
              </div>
              <div v-if="!audit.risks.length" class="empty" style="padding: 24px">
                <UiIcon name="shield" :size="22" />
                暂无风险项
              </div>
            </div>
            <router-link v-if="audit.risks.length" to="/report" class="risk-link">
              查看全部 {{ audit.risks.length }} 项风险与处理建议
              <UiIcon name="arrow-right" :size="13" />
            </router-link>
          </section>

          <section class="card card-pad todo-card">
            <div class="card-head">
              <h3>本学期待办</h3>
              <span class="hint">{{ todos.filter((t) => !t.done).length }} 项未完成</span>
            </div>
            <div class="todo-list">
              <button
                v-for="todo in todos"
                :key="todo.id"
                class="todo-item"
                :class="{ done: todo.done }"
                @click="toggleTodo(todo)"
              >
                <span class="todo-check">
                  <UiIcon v-if="todo.done" name="check" :size="11" />
                </span>
                <span class="todo-body">
                  <strong>{{ todo.title }}</strong>
                  <span>{{ todo.detail }}</span>
                </span>
                <span class="todo-tag" :class="todo.tone">{{ todo.tag }}</span>
              </button>
              <div v-if="!todos.length" class="empty" style="padding: 22px">
                <UiIcon name="check" :size="20" />
                本学期待办已清空
              </div>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <div v-else class="empty card" style="padding: 60px">
      <UiIcon name="alert" :size="28" />
      <p>暂时无法读取学业数据，请稍后刷新或重新导入成绩。</p>
      <button class="btn btn-primary" @click="load()">重试</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import CountUp from '@/components/CountUp.vue'
import CreditRing from '@/components/CreditRing.vue'
import EChart from '@/components/EChart.vue'
import StatusPill from '@/components/StatusPill.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const toast = useToastStore()

const loading = ref(true)
const refreshing = ref(false)
const report = ref(null)
const audit = computed(() => report.value?.audit || null)
const diff = computed(() => report.value?.diff || null)
const doneTodos = reactive(new Set())

const programTermLabel = computed(() => {
  const term = audit.value?.program_term
  const map = {
    '1-1': '大一秋', '1-2': '大一春', '2-1': '大二秋', '2-2': '大二春',
    '3-1': '大三秋', '3-2': '大三春', '4-1': '大四秋', '4-2': '大四春',
  }
  return term ? `${term} · ${map[term] || ''}` : ''
})

const moduleStats = computed(() => {
  if (!audit.value) return ''
  const ok = audit.value.modules.filter((m) => m.ok).length
  return `${ok} / ${audit.value.modules.length} 达标`
})

const healthScore = computed(() => {
  if (!audit.value) return 0
  const a = audit.value
  const structure = (a.modules.filter((m) => m.ok).length / a.modules.length) * 100
  const sc = a.graduation.second_classroom.ok === true ? 100 : a.graduation.second_classroom.ok === null ? 55 : 15
  const thesis = a.graduation.thesis.ok ? 100 : 12
  const direction = a.direction?.locked ? 100 : 45
  const load = Math.max(0, 100 - (a.summary.studying / 30) * 100 * 0.65)
  return Math.round(a.summary.percent * 0.46 + structure * 0.2 + sc * 0.13 + thesis * 0.1 + direction * 0.06 + load * 0.05)
})

const healthLabel = computed(() => {
  if (healthScore.value >= 80) return '良好'
  if (healthScore.value >= 60) return '可控'
  if (healthScore.value >= 40) return '偏低'
  return '高风险'
})

const healthTone = computed(() => {
  if (healthScore.value >= 60) return 'ok'
  if (healthScore.value >= 40) return 'warn'
  return 'danger'
})

const statCards = computed(() => {
  if (!audit.value) return []
  const s = audit.value.summary
  return [
    {
      label: '已获学分',
      value: s.earned,
      unit: '分',
      hint: `封顶后计入 ${s.require.toFixed(0)} 分总额`,
      progress: s.percent,
      color: 'var(--grad)',
      icon: 'book',
      tone: 'violet',
    },
    {
      label: '在修学分',
      value: s.studying,
      unit: '分',
      hint: '不计入已获，单独口径',
      progress: Math.min(100, (s.studying / 28) * 100),
      color: 'linear-gradient(90deg,#2f66e8,#0b8f7b)',
      icon: 'clock',
      tone: 'blue',
    },
    {
      label: '学分缺口',
      value: s.gap,
      unit: '分',
      hint: `剩余 ${remainingTerms.value} 学期 · 每学期 ${(s.gap / remainingTerms.value).toFixed(1)} 分`,
      progress: Math.min(100, (s.gap / s.require) * 100),
      color: 'linear-gradient(90deg,#f59e0b,#f43f5e)',
      icon: 'target',
      tone: 'amber',
    },
    {
      label: '超修学分',
      value: s.over,
      unit: '分',
      hint: '按模块封顶，不计入总学分',
      progress: Math.min(100, s.over * 25),
      color: 'linear-gradient(90deg,#10b981,#0b8f7b)',
      icon: 'arrow-up',
      tone: 'green',
    },
  ]
})

const remainingTerms = computed(() => {
  if (!audit.value) return 3
  const map = { '1-1': 7, '1-2': 6, '2-1': 5, '2-2': 4, '3-1': 3, '3-2': 2, '4-1': 1, '4-2': 1 }
  return map[audit.value.program_term] || 2
})

const riskCounts = computed(() => {
  const risks = audit.value?.risks || []
  return {
    high: risks.filter((risk) => risk.level === 'high').length,
    medium: risks.filter((risk) => risk.level === 'medium').length,
  }
})

const structureRisks = computed(() => (audit.value?.risks || []).filter((risk) => risk.type?.includes('structure')))

const riskGrade = computed(() => {
  if (!audit.value) return { tone: 'info', dot: '', label: '待评估', title: '' }
  const perTerm = audit.value.summary.gap / Math.max(1, remainingTerms.value)
  if (riskCounts.value.high > 0 || perTerm > 20 || healthScore.value < 45) {
    return {
      tone: 'danger',
      dot: 'danger',
      label: '高风险',
      title: '存在硬缺口，需要优先处理',
      summary: `总要求 ${audit.value.summary.require.toFixed(0)} 学分，已获 ${audit.value.summary.earned.toFixed(1)}，缺口 ${audit.value.summary.gap.toFixed(1)}；剩余 ${remainingTerms.value} 个学期，平均每学期需修 ${perTerm.toFixed(1)} 学分。`,
    }
  }
  if (audit.value.summary.gap > 0 || riskCounts.value.medium > 0) {
    return {
      tone: 'warn',
      dot: 'warn',
      label: '中风险',
      title: '缺口可控，但结构仍需补齐',
      summary: `总要求 ${audit.value.summary.require.toFixed(0)} 学分，已获 ${audit.value.summary.earned.toFixed(1)}，缺口 ${audit.value.summary.gap.toFixed(1)}；剩余 ${remainingTerms.value} 个学期，平均每学期需修 ${perTerm.toFixed(1)} 学分。`,
    }
  }
  return {
    tone: 'ok',
    dot: '',
    label: '低风险',
    title: '学分与毕业条件保持正常',
    summary: `总要求 ${audit.value.summary.require.toFixed(0)} 学分，已获 ${audit.value.summary.earned.toFixed(1)}；当前没有需要优先处理的硬缺口。`,
  }
})

const riskSummary = computed(() => {
  if (!audit.value) return ''
  const sc = audit.value.graduation.second_classroom
  const blockers = []
  if (sc.ok === false) {
    const unmet = (sc.items || []).filter((item) => item.status === 'unmet')
    blockers.push(`第二课堂仍有 ${unmet.length || 1} 项未达标`)
  } else if (sc.ok === null) {
    blockers.push('第二课堂数据待确认')
  }
  if (!audit.value.graduation.thesis.ok) blockers.push('毕业论文尚未启动')
  const tail = blockers.length ? `非学分卡点：${blockers.join('，')}。` : '非学分条件暂未发现阻塞。'
  return `${riskGrade.value.summary}${tail}`
})

const healthExplain = computed(() => {
  if (!audit.value) return ''
  if (structureRisks.value.length) {
    return '存在结构缺口，不只是学分数量问题；补课时先补子项，否则总量补满结构仍不合格。'
  }
  if (audit.value.summary.gap > 0) {
    return '主要差距在学分总量，结构暂未发现硬缺口；按学期均摊推进即可。'
  }
  return '学分总量与模块结构均正常，继续保持当前节奏。'
})

const signals = computed(() => {
  if (!audit.value) return []
  const perTerm = audit.value.summary.gap / Math.max(1, remainingTerms.value)
  const structure = structureRisks.value[0]
  const sc = audit.value.graduation.second_classroom
  return [
    {
      label: '学分压力',
      value: `${perTerm.toFixed(1)} 分/学期`,
      hint: `剩余 ${remainingTerms.value} 个学期`,
      tone: perTerm > 20 ? 'danger' : perTerm > 15 ? 'warn' : 'ok',
    },
    {
      label: '结构缺口',
      value: structure ? '存在' : '暂未发现',
      hint: structure ? riskType(structure.type) : '模块子项均满足',
      tone: structure ? 'warn' : 'ok',
    },
    {
      label: '非学分卡点',
      value: sc.ok === true && audit.value.graduation.thesis.ok ? '已清空' : '需处理',
      hint: sc.ok === true ? '第二课堂已达标' : '第二课堂 / 论文',
      tone: sc.ok === true && audit.value.graduation.thesis.ok ? 'ok' : 'warn',
    },
  ]
})


const graduationItems = computed(() => {
  if (!audit.value) return []
  const g = audit.value.graduation
  const scItems = g.second_classroom.items || []
  const unmet = scItems.filter((i) => i.status === 'unmet')
  return [
    {
      key: 'credits',
      label: '修满 169 学分',
      detail: `${g.credits.earned.toFixed(1)} / ${g.credits.require.toFixed(0)}，缺口 ${g.credits.gap.toFixed(1)}`,
      state: g.credits.ok ? 'ok' : 'bad',
      icon: 'book',
    },
    {
      key: 'sc',
      label: '第二课堂合格',
      detail: g.second_classroom.ok === true ? '四类周期要求均已达标' : unmet.length ? `${unmet.length} 项未达标：${unmet[0].category}` : '数据待确认（未接入书院系统）',
      state: g.second_classroom.ok === true ? 'ok' : g.second_classroom.ok === null ? 'warn' : 'bad',
      icon: 'medal',
    },
    {
      key: 'thesis',
      label: '毕业论文（设计）答辩',
      detail: g.thesis.label,
      state: g.thesis.ok ? 'ok' : 'bad',
      icon: 'shield',
    },
  ]
})

const todos = computed(() => {
  if (!audit.value) return []
  const a = audit.value
  const actions = []
  const courseItems = []
  const seen = new Set()

  if (a.direction && !a.direction.locked) {
    actions.push({ id: 'direction', title: '确定专业方向', detail: '三选一，同时决定 2 学分创新实践内容', tag: '决策', tone: 'warn' })
  }
  const unmet = (a.graduation.second_classroom.items || []).filter((i) => i.status === 'unmet')
  for (const item of unmet.slice(0, 2)) {
    actions.push({
      id: `sc-${item.category}-${item.period_label}`,
      title: `第二课堂 · ${item.category}`,
      detail: item.message,
      tag: '毕业条件',
      tone: 'danger',
    })
  }
  if (!a.graduation.thesis.ok) {
    actions.push({ id: 'thesis', title: '毕业设计（论文）', detail: '当前未通过，关注开题与答辩节点', tag: '毕业条件', tone: 'warn' })
  }

  for (const module of a.modules) {
    for (const miss of module.missing || []) {
      if (seen.has(miss.code)) continue
      const isCurrent = miss.plan_term === a.program_term || miss.status === 'studying'
      if (!isCurrent) continue
      if (!(miss.nature === '必修' || miss.required_child || module.id === 'M5')) continue
      seen.add(miss.code)
      courseItems.push({
        id: `course-${miss.code}`,
        title: miss.name,
        detail: `${miss.credit.toFixed(1)} 学分 · ${miss.assessment} · ${miss.status === 'studying' ? '在修' : '待修'}`,
        tag: miss.status === 'studying' ? '在修' : '课程',
        tone: miss.status === 'studying' ? 'info' : 'warn',
      })
    }
  }

  return [...actions, ...courseItems.slice(0, 4)]
    .slice(0, 6)
    .map((item) => ({ ...item, done: doneTodos.has(item.id) }))
})

function toggleTodo(todo) {
  if (doneTodos.has(todo.id)) doneTodos.delete(todo.id)
  else doneTodos.add(todo.id)
}

function moduleTone(module) {
  if (module.ok) return 'ok'
  if (module.own_ok && !module.child_ok) return 'structure'
  return 'gap'
}

function structureNote(module) {
  if (module.child_ok) return ''
  const child = (module.children || []).find((c) => c.require > 0 && !c.ok)
  if (!child) return ''
  if (module.own_ok) return `${child.name}仍差 ${child.gap.toFixed(1)}，结构未达标`
  if (child.gap > module.gap) return `${child.name}差 ${child.gap.toFixed(1)}，优先补`
  return ''
}

function riskType(type) {
  const map = {
    credit_gap: '学分缺口',
    structure_gap: '结构缺口',
    structure_priority: '补课优先级',
    second_classroom: '第二课堂',
    thesis: '毕业答辩',
    direction_undecided: '方向决策',
    last_offering: '最后一次开课',
  }
  return map[type] || type
}

function openModule(id) {
  router.push({ path: '/plan', query: { module: id } })
}

const trendOption = computed(() => {
  const rows = report.value?.snapshots || []
  const points = rows.length
    ? rows.map((s) => ({
        term: s.semester,
        earned: Number(s.summary?.earned || 0),
        gap: Number(s.summary?.gap || 0),
      }))
    : []
  if (audit.value) {
    const last = points[points.length - 1]
    if (!last || last.term !== audit.value.as_of) {
      points.push({ term: audit.value.as_of, earned: audit.value.summary.earned, gap: audit.value.summary.gap })
    }
  }
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11,18,38,.94)',
      borderWidth: 0,
      textStyle: { color: '#e8eeff', fontSize: 11 },
      padding: [8, 12],
    },
    legend: {
      right: 0,
      top: 0,
      itemWidth: 8,
      itemHeight: 8,
      icon: 'circle',
      textStyle: { color: '#8b94aa', fontSize: 10 },
      data: ['已获', '缺口'],
    },
    grid: { left: 4, right: 8, top: 30, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: points.map((p) => p.term),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#8b94aa', fontSize: 9.5 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(15,26,54,.06)', type: 'dashed' } },
      axisLabel: { color: '#8b94aa', fontSize: 9.5 },
    },
    series: [
      {
        name: '已获',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: points.map((p) => p.earned),
        lineStyle: { width: 2.5, color: '#2f66e8' },
        itemStyle: { color: '#2f66e8', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79,124,255,.24)' },
              { offset: 1, color: 'rgba(79,124,255,0)' },
            ],
          },
        },
      },
      {
        name: '缺口',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: points.map((p) => p.gap),
        lineStyle: { width: 2.5, color: '#f59e0b', type: 'dashed' },
        itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
      },
    ],
  }
})

const radarOption = computed(() => {
  if (!audit.value) return {}
  const a = audit.value
  const structure = (a.modules.filter((m) => m.ok).length / a.modules.length) * 100
  const sc = a.graduation.second_classroom.ok === true ? 100 : a.graduation.second_classroom.ok === null ? 55 : 20
  const thesis = a.graduation.thesis.ok ? 100 : 12
  const direction = a.direction?.locked ? 100 : 45
  const load = Math.max(10, 100 - (a.summary.studying / 28) * 60)
  return {
    tooltip: {
      backgroundColor: 'rgba(11,18,38,.94)',
      borderWidth: 0,
      textStyle: { color: '#e8eeff', fontSize: 11 },
    },
    radar: {
      center: ['50%', '54%'],
      radius: '64%',
      indicator: [
        { name: '学分进度', max: 100 },
        { name: '模块结构', max: 100 },
        { name: '方向明确', max: 100 },
        { name: '第二课堂', max: 100 },
        { name: '毕业设计', max: 100 },
        { name: '负载控制', max: 100 },
      ],
      axisName: { color: '#66708a', fontSize: 9.5 },
      splitLine: { lineStyle: { color: 'rgba(15,26,54,.08)' } },
      splitArea: { areaStyle: { color: ['rgba(108,92,231,.025)', 'rgba(23,195,178,.02)'] } },
      axisLine: { lineStyle: { color: 'rgba(15,26,54,.08)' } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 4,
        data: [
          {
            value: [a.summary.percent, structure, direction, sc, thesis, load].map((v) => Math.round(v)),
            name: '当前',
            lineStyle: { color: '#1e4ed8', width: 2 },
            itemStyle: { color: '#1e4ed8' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 1, y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(108,92,231,.35)' },
                  { offset: 1, color: 'rgba(23,195,178,.12)' },
                ],
              },
            },
          },
        ],
      },
    ],
  }
})

async function load(isRefresh = false) {
  if (isRefresh) refreshing.value = true
  else loading.value = true
  try {
    report.value = await api.report()
  } catch (error) {
    toast.error(getErrorMessage(error))
    report.value = null
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dashboard {
  padding-top: 26px;
}

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.65fr);
  gap: 30px;
  padding: 30px 34px;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.58));
}

.hero-glow {
  position: absolute;
  right: -80px;
  top: -120px;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(30, 78, 216, 0.18), transparent 65%);
  pointer-events: none;
}

.hero-left {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.hero-topline {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-title {
  margin: 17px 0 10px;
  font-size: clamp(28px, 3vw, 40px);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.hero-desc {
  color: var(--muted);
  font-size: 14.5px;
  line-height: 1.75;
  max-width: 630px;
}

.hero-desc strong {
  color: var(--ink);
}

.hero-gap {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--rose) !important;
}

.diff-pill {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-top: 16px;
  padding: 8px 12px 8px 9px;
  border-radius: 11px;
  background: rgba(18, 131, 111, 0.07);
  border: 1px solid rgba(18, 131, 111, 0.14);
  color: #0b6b5b;
  font-size: 11.5px;
}

.diff-icon {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: rgba(18, 131, 111, 0.12);
}

.diff-tag {
  color: var(--muted-2);
  font-size: 10px;
  border-left: 1px solid rgba(18, 131, 111, 0.2);
  padding-left: 9px;
}

.condition-row {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 20px;
}

.condition {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 128px;
  padding: 9px 12px 9px 9px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.62);
}

.condition-ic {
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border-radius: 8px;
  background: rgba(21, 32, 43, 0.05);
  color: var(--muted);
  flex: none;
}

.condition.ok .condition-ic {
  background: rgba(18, 131, 111, 0.1);
  color: #0b6b5b;
}

.condition.bad .condition-ic {
  background: rgba(184, 69, 63, 0.09);
  color: #96332e;
}

.condition.warn .condition-ic {
  background: rgba(178, 106, 27, 0.12);
  color: #94530f;
}

.condition div {
  display: grid;
  gap: 1px;
}

.condition strong {
  font-size: 11.5px;
}

.condition span:last-child {
  font-size: 10px;
  color: var(--muted-2);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-top: 24px;
}

.hero-right {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding-left: 24px;
  border-left: 1px solid var(--line);
}

.ring-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  width: 100%;
}

.ring-stats div {
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 7px 4px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.5);
}

.ring-stats span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.ring-stats strong {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
}

.ring-stats strong.warn {
  color: #94530f;
}

.health-line {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10.5px;
  color: var(--muted-2);
}

.health-line strong {
  font-size: 15px;
  color: var(--ink);
  font-family: var(--font-display);
}

.health-tag {
  padding: 2px 7px;
  border-radius: 99px;
  background: rgba(30, 78, 216, 0.08);
  color: var(--violet);
  font-weight: 600;
}

.stats {
  margin-top: 18px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  overflow: hidden;
}

.stat-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 13px;
  flex: none;
}

.stat-icon.violet {
  color: #1e4ed8;
  background: rgba(30, 78, 216, 0.1);
}

.stat-icon.blue {
  color: #2f66e8;
  background: rgba(47, 102, 232, 0.1);
}

.stat-icon.amber {
  color: #94530f;
  background: rgba(178, 106, 27, 0.12);
}

.stat-icon.green {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.1);
}

.stat-meta {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.stat-meta > span {
  font-size: 10.5px;
  color: var(--muted-2);
  letter-spacing: 0.04em;
}

.stat-meta strong {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.stat-meta strong i {
  font-style: normal;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  margin-left: 2px;
}

.stat-meta small {
  font-size: 9.5px;
  color: var(--muted-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2.5px;
  background: rgba(21, 32, 43, 0.04);
}

.stat-bar i {
  display: block;
  height: 100%;
  border-radius: 0 99px 99px 0;
  transition: width 1.2s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.dash-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(340px, 0.78fr);
  gap: 20px;
  margin-top: 18px;
  align-items: start;
}

.dash-main,
.dash-side {
  display: grid;
  gap: 18px;
}

.module-card {
  padding-bottom: 12px;
}

.module-list {
  display: grid;
}

.module-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 10px;
  border-radius: 13px;
  text-align: left;
  border-bottom: 1px solid var(--line);
  transition: background 0.2s ease, transform 0.2s ease;
  animation: revealUp 0.5s ease both;
}

.module-row:last-child {
  border-bottom: 0;
}

.module-row:hover {
  background: rgba(30, 78, 216, 0.035);
  transform: translateX(2px);
}

.module-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 7px;
}

.module-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.module-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.module-name strong {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.module-dot {
  width: 8px;
  height: 8px;
  border-radius: 3px;
  flex: none;
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(18, 131, 111, 0.1);
}

.module-dot.gap {
  background: var(--amber);
  box-shadow: 0 0 0 3px rgba(178, 106, 27, 0.12);
}

.module-dot.structure {
  background: var(--rose);
  box-shadow: 0 0 0 3px rgba(184, 69, 63, 0.1);
}

.mode-tag {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(30, 78, 216, 0.07);
  color: var(--violet);
  white-space: nowrap;
}

.module-num {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted-2);
  white-space: nowrap;
}

.module-num strong {
  font-size: 14px;
  color: var(--ink);
  font-weight: 600;
}

.module-progress {
  height: 5px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.055);
  overflow: hidden;
}

.module-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--grad);
  transition: width 1.1s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.module-progress i.gap {
  background: linear-gradient(90deg, #f59e0b, #fb923c);
}

.module-progress i.structure {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
}

.module-foot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.gap-text {
  font-size: 10px;
  color: #94530f;
}

.over-text {
  font-size: 10px;
  color: #0b6b5b;
}

.structure-text {
  font-size: 10px;
  color: #96332e;
  background: rgba(184, 69, 63, 0.06);
  padding: 2px 7px;
  border-radius: 5px;
}

.module-arrow {
  color: var(--muted-2);
  flex: none;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.chart-card {
  min-width: 0;
}

.grad-list {
  display: grid;
  gap: 8px;
}

.grad-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid var(--line);
}

.grad-item .grad-ic {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  flex: none;
  background: rgba(184, 69, 63, 0.08);
  color: #96332e;
}

.grad-item.ok .grad-ic {
  background: rgba(18, 131, 111, 0.1);
  color: #0b6b5b;
}

.grad-item.warn .grad-ic {
  background: rgba(178, 106, 27, 0.12);
  color: #94530f;
}

.grad-meta {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}

.grad-meta strong {
  font-size: 11.5px;
}

.grad-meta span {
  font-size: 10px;
  color: var(--muted-2);
  line-height: 1.4;
}

.grad-item > svg {
  color: #96332e;
  flex: none;
}

.grad-item.ok > svg {
  color: #0b6b5b;
}

.grad-item.warn > svg {
  color: #94530f;
}

.grad-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 13px;
  padding-top: 13px;
  border-top: 1px dashed var(--line);
  font-size: 11px;
  color: var(--violet);
  font-weight: 600;
}

.risk-list {
  display: grid;
  gap: 10px;
}

.risk-item {
  display: flex;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 10px;
  background: rgba(21, 32, 43, 0.025);
  border-left: 3px solid var(--muted-2);
}

.risk-item.high {
  border-left-color: var(--rose);
  background: rgba(184, 69, 63, 0.04);
}

.risk-item.medium {
  border-left-color: var(--amber);
  background: rgba(178, 106, 27, 0.04);
}

.risk-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
  flex: none;
  background: var(--muted-2);
}

.risk-item.high .risk-dot {
  background: var(--rose);
}

.risk-item.medium .risk-dot {
  background: var(--amber);
}

.risk-item p {
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--ink-2);
}

.risk-type {
  font-size: 9.5px;
  color: var(--muted-2);
  letter-spacing: 0.03em;
}

.todo-list {
  display: grid;
  gap: 6px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 10px;
  text-align: left;
  transition: background 0.2s ease;
}

.todo-item:hover {
  background: rgba(21, 32, 43, 0.03);
}

.todo-check {
  width: 17px;
  height: 17px;
  border-radius: 5px;
  border: 1.5px solid var(--line-strong);
  display: grid;
  place-items: center;
  flex: none;
  color: #fff;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.todo-item.done .todo-check {
  background: var(--grad);
  border-color: transparent;
}

.todo-body {
  display: grid;
  gap: 1px;
  flex: 1;
  min-width: 0;
}

.todo-body strong {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todo-item.done .todo-body strong {
  text-decoration: line-through;
  color: var(--muted-2);
}

.todo-body span {
  font-size: 10px;
  color: var(--muted-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todo-tag {
  font-size: 8.5px;
  padding: 2px 6px;
  border-radius: 5px;
  flex: none;
  background: rgba(21, 32, 43, 0.05);
  color: var(--muted);
}

.todo-tag.warn {
  background: rgba(178, 106, 27, 0.1);
  color: #94530f;
}

.todo-tag.danger {
  background: rgba(184, 69, 63, 0.08);
  color: #96332e;
}

.todo-tag.info {
  background: rgba(47, 102, 232, 0.08);
  color: #3730a3;
}

@media (max-width: 1200px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .hero-right {
    flex-direction: row;
    justify-content: space-around;
    padding-left: 0;
    padding-top: 22px;
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .ring-stats {
    max-width: 260px;
  }

  .dash-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero {
    padding: 22px;
  }

  .hero-right {
    flex-direction: column;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .condition {
    flex: 1;
  }
}

/* ---- editorial dashboard overrides ---- */
.dashboard {
  padding-top: 22px;
}

.hero {
  grid-template-columns: minmax(0, 1.6fr) minmax(240px, 0.55fr);
  gap: 48px;
  padding: 6px 2px 34px;
  overflow: visible;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
}

.hero-glow {
  display: none;
}

.hero-topline {
  gap: 7px;
}

.hero-title {
  margin: 18px 0 12px;
  font-size: clamp(30px, 3.2vw, 40px);
  font-weight: 600;
  letter-spacing: -0.035em;
}

.hero-desc {
  font-size: 14.5px;
  line-height: 1.8;
  max-width: 570px;
}

.hero-gap {
  font-family: var(--font-serif);
  font-size: 21px;
  font-weight: 500;
}

.diff-pill {
  margin-top: 18px;
  padding: 7px 10px 7px 7px;
  border-radius: 8px;
  background: rgba(18, 131, 111, 0.06);
  border: 1px solid rgba(18, 131, 111, 0.16);
  color: #0b6b5b;
  font-size: 11px;
}

.diff-icon {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: transparent;
}

.diff-tag {
  border-left-color: rgba(18, 131, 111, 0.24);
  font-size: 9.5px;
}

.condition-row {
  gap: 20px;
  margin-top: 24px;
  padding-top: 17px;
  border-top: 1px solid var(--line);
}

.condition {
  min-width: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  gap: 8px;
}

.condition-ic {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: transparent;
  border: 1px solid var(--line-strong);
}

.condition.ok .condition-ic {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.07);
  border-color: rgba(18, 131, 111, 0.2);
}

.condition.bad .condition-ic {
  color: #96332e;
  background: rgba(184, 69, 63, 0.06);
  border-color: rgba(184, 69, 63, 0.2);
}

.condition.warn .condition-ic {
  color: #94530f;
  background: rgba(178, 106, 27, 0.07);
  border-color: rgba(178, 106, 27, 0.2);
}

.condition strong {
  font-size: 11px;
  font-weight: 600;
}

.condition span:last-child {
  font-size: 9.5px;
}

.hero-actions {
  margin-top: 22px;
}

.hero-right {
  gap: 11px;
  padding-left: 30px;
}

.ring-stats {
  gap: 10px;
}

.ring-stats div {
  gap: 2px;
  padding: 9px 0 0;
  border-radius: 0;
  border-top: 1px solid var(--line);
  background: transparent;
}

.ring-stats span {
  font-size: 9px;
  letter-spacing: 0.03em;
}

.ring-stats strong {
  font-size: 13px;
}

.health-tag {
  border-radius: 5px;
  background: rgba(30, 78, 216, 0.08);
  color: var(--violet);
  font-size: 9.5px;
}

.health-tag.warn {
  background: var(--warning-bg);
  color: var(--warning);
}

.health-tag.danger {
  background: var(--danger-bg);
  color: var(--danger);
}

.health-tag.ok {
  background: var(--success-bg);
  color: var(--success);
}

.stats {
  margin-top: 0;
  gap: 0;
  overflow: hidden;
  background: var(--card-solid);
  border: 1px solid var(--line);
  border-radius: 14px;
}

.stat-card {
  position: relative;
  gap: 12px;
  padding: 17px 19px;
  border-radius: 0;
  border: 0;
  border-right: 1px solid var(--line);
  box-shadow: none;
  background: transparent;
}

.stat-card:last-child {
  border-right: 0;
}

.stat-card:hover {
  transform: none;
  background: rgba(30, 78, 216, 0.025);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: 7px;
}

.stat-icon.violet {
  color: var(--violet);
  background: rgba(30, 78, 216, 0.08);
}

.stat-icon.blue {
  color: #2f66e8;
  background: rgba(47, 102, 232, 0.08);
}

.stat-icon.amber {
  color: #94530f;
  background: rgba(178, 106, 27, 0.08);
}

.stat-icon.green {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.08);
}

.stat-meta strong {
  font-size: 21px;
  font-weight: 650;
}

.stat-meta small {
  font-size: 9.5px;
}

.stat-bar {
  height: 2px;
  background: transparent;
}

.dash-grid {
  grid-template-columns: minmax(0, 1.6fr) minmax(326px, 0.74fr);
  gap: 24px;
  margin-top: 24px;
}

.dash-main,
.dash-side {
  gap: 24px;
}

.module-card {
  padding: 22px 24px 8px;
}

.module-list {
  gap: 0;
  margin-top: 4px;
}

.module-row {
  padding: 15px 0;
  border-radius: 0;
  border-bottom: 1px solid var(--line);
}

.module-row:last-child {
  border-bottom: 0;
}

.module-row:hover {
  background: transparent;
  padding-left: 0;
}

.module-name strong {
  font-size: 13px;
}

.module-num strong {
  font-size: 15px;
  font-weight: 600;
}

.module-progress {
  height: 4px;
  background: rgba(21, 32, 43, 0.07);
}

.module-progress i {
  background: var(--violet);
}

.module-progress i.gap {
  background: var(--amber);
}

.module-progress i.structure {
  background: var(--rose);
}

.module-dot {
  width: 6px;
  height: 6px;
}

.mode-tag {
  border-radius: 4px;
  font-size: 8.5px;
}

.charts-grid {
  gap: 24px;
}

.grad-item {
  padding: 12px 0;
  border-radius: 0;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
}

.grad-item:last-child {
  border-bottom: 0;
}

.grad-item .grad-ic {
  border-radius: 0;
  background: transparent;
}

.grad-item.ok .grad-ic,
.grad-item.warn .grad-ic {
  background: transparent;
}

.risk-item {
  padding: 10px 0 10px 12px;
  border-radius: 0;
  border: 0;
  border-left: 2px solid var(--line-strong);
  background: transparent;
}

.risk-item.high {
  border-left-color: var(--rose);
  background: transparent;
}

.risk-item.medium {
  border-left-color: var(--amber);
  background: transparent;
}

.risk-dot {
  display: none;
}

.risk-item p {
  font-size: 11.5px;
  line-height: 1.7;
}

.todo-item {
  padding: 11px 0;
  border-radius: 0;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
}

.todo-item:last-child {
  border-bottom: 0;
}

.todo-item:hover {
  background: transparent;
}

.todo-body strong {
  font-size: 12px;
}

.todo-body span {
  font-size: 10px;
}

.todo-tag {
  border-radius: 4px;
  font-size: 8.5px;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
    padding: 4px 0 26px;
  }

  .hero-title {
    font-size: 30px;
    letter-spacing: -0.03em;
  }

  .hero-desc {
    font-size: 14px;
  }

  .hero-right {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-start;
    align-items: center;
    gap: 18px;
    padding: 20px 0 0;
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .ring-stats {
    width: auto;
    min-width: 150px;
    flex: 1;
  }

  .condition-row {
    gap: 14px;
  }

  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-card {
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    padding: 14px 16px;
  }

  .stat-card:nth-child(2n) {
    border-right: 0;
  }

  .stat-card:nth-last-child(-n + 2) {
    border-bottom: 0;
  }

  .stat-icon {
    display: none;
  }

  .stat-meta strong {
    font-size: 19px;
  }

  .dash-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .charts-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 520px) {
  .hero-right {
    flex-direction: column;
    align-items: flex-start;
  }

  .ring-stats {
    width: 100%;
  }

  .stats {
    grid-template-columns: minmax(0, 1fr);
  }

  .stat-card {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .stat-card:last-child {
    border-bottom: 0;
  }
}

/* ---- enterprise risk-summary pass ---- */
.dashboard {
  padding-top: 24px;
}

.dash-head {
  margin-bottom: 18px;
}

.dash-head .head-actions {
  align-items: center;
  gap: 8px;
}

.head-sep {
  margin: 0 5px;
  color: var(--line-strong);
}

.dashboard .hero {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(230px, 0.55fr);
  gap: 30px;
  padding: 22px 24px;
  overflow: hidden;
  background: var(--card-solid);
  border: 1px solid var(--line);
  border-left: 3px solid var(--line-strong);
  border-radius: var(--r-lg);
  box-shadow: 0 2px 12px rgba(21, 32, 43, 0.045);
}

.dashboard .hero-danger {
  border-left-color: var(--danger);
  background: linear-gradient(100deg, rgba(178, 59, 54, 0.055), transparent 42%), var(--card-solid);
}

.dashboard .hero-warn {
  border-left-color: var(--warning);
  background: linear-gradient(100deg, rgba(164, 90, 18, 0.05), transparent 42%), var(--card-solid);
}

.dashboard .hero-ok {
  border-left-color: var(--success);
}

.hero-kicker {
  margin: 17px 0 8px;
  color: var(--muted);
  font-family: var(--font-serif);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.dashboard .hero-title {
  margin: 0 0 9px;
  font-size: 25px;
  font-weight: 620;
  letter-spacing: -0.03em;
  line-height: 1.3;
}

.hero-danger .hero-title {
  color: var(--danger);
}

.hero-warn .hero-title {
  color: var(--warning);
}

.dashboard .hero-desc {
  max-width: 640px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.75;
}

.hero-signals {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin-top: 18px;
  padding-top: 13px;
  border-top: 1px solid var(--line);
}

.hero-signal {
  min-width: 0;
  padding: 0 16px;
  border-left: 1px solid var(--line);
}

.hero-signal:first-child {
  padding-left: 0;
  border-left: 0;
}

.hero-signal span,
.hero-signal small {
  display: block;
  color: var(--muted-2);
  font-size: 10px;
  line-height: 1.5;
}

.hero-signal strong {
  display: block;
  margin: 2px 0;
  font-size: 13px;
  font-weight: 650;
}

.hero-signal strong.ok {
  color: var(--success);
}

.hero-signal strong.warn {
  color: var(--warning);
}

.hero-signal strong.danger {
  color: var(--danger);
}

.dashboard .health-line {
  width: 100%;
  justify-content: center;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}

.health-explain {
  max-width: 230px;
  color: var(--muted);
  font-size: 10.5px;
  line-height: 1.55;
  text-align: center;
}

.dashboard .stats {
  margin-top: 16px;
  border-radius: var(--r-lg);
}

.dashboard .stat-card.highlight {
  background: var(--warning-bg);
  box-shadow: inset 0 2px 0 rgba(178, 106, 27, 0.55);
}

.dashboard .stat-card.highlight .stat-meta strong {
  color: var(--warning);
}

.module-status {
  margin-left: auto;
  flex: none;
}

.grad-state {
  flex: none;
  padding: 3px 6px;
  border-radius: var(--r-xs);
  font-size: 9.5px;
  font-weight: 600;
}

.grad-state.ok {
  color: var(--success);
  background: var(--success-bg);
}

.grad-state.warn {
  color: var(--warning);
  background: var(--warning-bg);
}

.grad-state.bad {
  color: var(--danger);
  background: var(--danger-bg);
}

.risk-severity {
  margin-left: 6px;
  color: var(--muted-2);
  font-size: 9px;
}

.risk-item.high .risk-severity {
  color: var(--danger);
}

.risk-item.medium .risk-severity {
  color: var(--warning);
}

.risk-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  padding-top: 11px;
  border-top: 1px solid var(--line);
  color: var(--violet);
  font-size: 11.5px;
  font-weight: 600;
}

.risk-link:hover {
  color: var(--indigo);
}

@media (max-width: 900px) {
  .dashboard .hero {
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
    padding: 18px;
  }

  .hero-signals {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .hero-signal {
    padding: 0 8px;
    border-left: 1px solid var(--line);
    border-top: 0;
  }

  .hero-signal:first-child {
    padding-left: 0;
    border-left: 0;
  }

  .hero-signal small {
    display: none;
  }

  .dashboard .hero-right {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-start;
    align-items: center;
    padding: 16px 0 0;
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .health-explain {
    max-width: 100%;
    text-align: left;
  }
}

@media (max-width: 520px) {
  .dashboard .hero-title {
    font-size: 22px;
  }

  .hero-actions {
    align-items: stretch;
  }

  .hero-actions .btn {
    flex: 1 1 auto;
  }
}

</style>
