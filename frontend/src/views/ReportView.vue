<template>
  <div class="page report-page">
    <div class="page-head no-print">
      <div>
        <h1 class="page-title">学业报告</h1>
        <p class="page-sub">学期汇总 + 毕业三条件 + 快照 diff。可直接打印为 PDF，用于奖学金、保研或家校沟通。</p>
      </div>
      <div class="row">
        <button class="btn btn-sm" :disabled="loading" @click="load">
          <UiIcon name="refresh" :size="14" />
          刷新
        </button>
        <button class="btn btn-sm btn-primary" @click="print">
          <UiIcon name="print" :size="14" />
          导出 / 打印
        </button>
      </div>
    </div>

    <div v-if="loading" class="skeleton" style="height: 640px" />

    <div v-else-if="data" class="report-sheet">
      <header class="report-head">
        <div class="report-brand">
          <div class="report-logo">学</div>
          <div>
            <strong>学业罗盘 · 学业汇总</strong>
            <span>ACADEMIC COMPASS · SEMESTER REPORT</span>
          </div>
        </div>
        <div class="report-id">
          <span>{{ audit.plan.name }}</span>
          <span class="mono">{{ data.meta.generated_at?.slice(0, 10) }}</span>
        </div>
      </header>

      <section class="report-title">
        <div>
          <div class="report-kicker">
            {{ audit.as_of }} · 第 {{ audit.program_term }} 学期
            <span v-if="termLabel">（{{ termLabel }}）</span>
          </div>
          <h2>{{ audit.student.name }} 的学业汇总</h2>
          <p>
            {{ audit.student.major }} · {{ audit.student.grade }} 级
            <template v-if="audit.student.class_name"> · {{ audit.student.class_name }}</template>
            · 学号 {{ audit.student.student_no }}
          </p>
        </div>
        <div class="report-stamp" :class="audit.graduation.ok ? 'ok' : 'warn'">
          <span>{{ audit.graduation.ok ? '三条件满足' : '预演 · 未满足' }}</span>
          <strong>{{ audit.summary.percent.toFixed(1) }}%</strong>
          <small>学分完成度</small>
        </div>
      </section>

      <section class="report-summary">
        <div v-for="item in summaryCards" :key="item.label" class="rs-item">
          <span>{{ item.label }}</span>
          <strong :class="item.tone">{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </section>

      <section v-if="data.diff" class="report-section">
        <div class="section-head">
          <h3><span class="sec-no">01</span>快照变化</h3>
          <span class="sec-tag">较 {{ data.diff.from.semester }}</span>
        </div>
        <div class="diff-headline">
          <UiIcon name="chart" :size="16" />
          {{ data.diff.headline }}
        </div>
        <div class="diff-body">
          <div class="diff-block">
            <strong>新增通过（{{ data.diff.new_passed_count }} 门 / +{{ data.diff.new_passed_credits.toFixed(1) }} 学分）</strong>
            <div class="diff-chips">
              <span v-for="course in data.diff.new_passed" :key="course.code" class="diff-chip">
                {{ course.name }} · {{ course.credit.toFixed(1) }}
              </span>
              <span v-if="!data.diff.new_passed.length" class="muted small">本学期暂无新增通过课程</span>
            </div>
          </div>
          <div class="diff-block" v-if="data.diff.module_changes.length">
            <strong>模块变化</strong>
            <div class="diff-chips">
              <span v-for="change in data.diff.module_changes" :key="change.id" class="diff-chip">
                {{ change.name }}：{{ change.earned_before.toFixed(1) }} → {{ change.earned_after.toFixed(1) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="report-section">
        <div class="section-head">
          <h3><span class="sec-no">02</span>模块明细</h3>
          <span class="sec-tag">要求 / 已获 / 未获得</span>
        </div>
        <table class="report-table">
          <thead>
            <tr>
              <th>模块</th>
              <th>模式</th>
              <th>要求</th>
              <th>已获</th>
              <th>缺口</th>
              <th>结构</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="module in audit.modules" :key="module.id">
              <tr>
                <td>
                  <strong>{{ module.name }}</strong>
                  <span v-if="module.picked_name" class="sub">（{{ module.picked_name }}）</span>
                </td>
                <td>{{ modeLabel(module.mode) }}</td>
                <td class="mono">{{ module.require.toFixed(1) }}</td>
                <td class="mono">{{ module.earned.toFixed(1) }}</td>
                <td class="mono" :class="{ danger: module.gap > 0 }">{{ module.gap.toFixed(1) }}</td>
                <td>
                  <span :class="module.child_ok ? 'ok-text' : 'danger-text'">
                    {{ structureLabel(module) }}
                  </span>
                </td>
                <td><StatusPill :status="module.status" /></td>
              </tr>
              <tr v-for="child in module.children || []" :key="child.id" class="child-row">
                <td><span class="child-line">└</span>{{ child.name }}</td>
                <td>{{ modeLabel(child.mode) }}</td>
                <td class="mono">{{ child.require.toFixed(1) }}</td>
                <td class="mono">{{ child.earned.toFixed(1) }}</td>
                <td class="mono" :class="{ danger: child.gap > 0 }">{{ child.gap.toFixed(1) }}</td>
                <td><span :class="child.child_ok ? 'ok-text' : 'danger-text'">{{ structureLabel(child) }}</span></td>
                <td><StatusPill :status="child.status" /></td>
              </tr>
            </template>
          </tbody>
        </table>
        <p class="table-note">
          总学分按模块封顶：超修 {{ audit.summary.over.toFixed(1) }} 学分不计入 {{ audit.summary.require.toFixed(0) }} 的分子；
          在修 {{ audit.summary.studying.toFixed(1) }} 学分不计入已获。父项缺口不等于子项缺口之和。
        </p>
      </section>

      <section class="report-section print-break">
        <div class="section-head">
          <h3><span class="sec-no">03</span>毕业三条件</h3>
          <span class="sec-tag">学分 ∧ 第二课堂 ∧ 答辩</span>
        </div>
        <div class="grad-grid">
          <div class="grad-box" :class="audit.graduation.credits.ok ? 'ok' : 'bad'">
            <div class="grad-box-head">
              <UiIcon name="book" :size="17" />
              <strong>修满 169 学分</strong>
              <span>{{ audit.graduation.credits.ok ? '通过' : '未通过' }}</span>
            </div>
            <div class="grad-num">
              {{ audit.graduation.credits.earned.toFixed(1) }}
              <span>/ {{ audit.graduation.credits.require.toFixed(0) }}</span>
            </div>
            <div class="grad-mini-bar"><i :style="{ width: `${audit.summary.percent}%` }" /></div>
            <p>缺口 {{ audit.graduation.credits.gap.toFixed(1) }} 学分</p>
          </div>

          <div class="grad-box" :class="scState">
            <div class="grad-box-head">
              <UiIcon name="medal" :size="17" />
              <strong>第二课堂合格</strong>
              <span>{{ audit.graduation.second_classroom.ok === true ? '通过' : audit.graduation.second_classroom.ok === null ? '待确认' : '未通过' }}</span>
            </div>
            <ul class="sc-list">
              <li v-for="item in scSummary" :key="item.category">
                <span>{{ item.category }}</span>
                <strong :class="item.status">{{ item.text }}</strong>
              </li>
            </ul>
            <p>数据来源：学生登记 + 教学秘书审核；未接入书院系统时标记为“待确认”。</p>
          </div>

          <div class="grad-box" :class="audit.graduation.thesis.ok ? 'ok' : 'bad'">
            <div class="grad-box-head">
              <UiIcon name="shield" :size="17" />
              <strong>毕业论文答辩</strong>
              <span>{{ audit.graduation.thesis.ok ? '通过' : '未通过' }}</span>
            </div>
            <div class="thesis-state">{{ audit.graduation.thesis.label }}</div>
            <p>毕业论文（设计）答辩合格是毕业的必要条件，不能由学分替代。</p>
          </div>
        </div>
      </section>

      <section class="report-section">
        <div class="section-head">
          <h3><span class="sec-no">04</span>第二课堂周期明细</h3>
          <span class="sec-tag">事件 + 周期合规</span>
        </div>
        <table class="report-table compact">
          <thead>
            <tr>
              <th>类别</th>
              <th>周期</th>
              <th>要求</th>
              <th>已完成</th>
              <th>状态</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in audit.graduation.second_classroom.items" :key="idx">
              <td>{{ item.category }}</td>
              <td>{{ item.period_label }}</td>
              <td class="mono">{{ item.require }}</td>
              <td class="mono">{{ item.done }}</td>
              <td><StatusPill :status="item.status" /></td>
              <td class="muted">{{ item.message }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="report-section">
        <div class="section-head">
          <h3><span class="sec-no">05</span>风险与下一步</h3>
          <span class="sec-tag">{{ audit.risks.length }} 项风险</span>
        </div>
        <div v-for="group in riskGroups" :key="group.key" class="risk-group">
          <div class="risk-group-head">
            <span class="rg-dot" :class="group.key" />
            <strong>{{ group.label }}</strong>
            <span class="rg-count">{{ group.items.length }}</span>
            <small>{{ group.hint }}</small>
          </div>
          <div class="report-risks">
            <div v-for="(risk, idx) in group.items" :key="`${group.key}-${idx}`" class="report-risk" :class="risk.level">
              <span class="rr-dot" />
              <div>
                <strong>{{ risk.msg }}</strong>
                <span>{{ riskType(risk.type) }}</span>
              </div>
              <button v-if="riskTarget(risk)" class="rr-action no-print" type="button" @click="router.push(riskTarget(risk))">
                去处理
              </button>
            </div>
          </div>
        </div>
        <div class="next-steps">
          <strong>下一步</strong>
          <ol>
            <li v-for="step in nextSteps" :key="step">{{ step }}</li>
          </ol>
        </div>
      </section>

      <footer class="report-foot">
        <div>
          <strong>证据与口径</strong>
          <p>
            数字由 {{ data.meta.engine_version }} 计算，可追溯到培养方案模块、课程编码与修读状态；
            方案版本 {{ audit.plan.id }}。{{ data.meta.disclaimer }}。
          </p>
        </div>
        <div class="foot-mark">
          <span>学业罗盘</span>
          <small>ACADEMIC COMPASS</small>
        </div>
      </footer>
    </div>

    <div v-else class="empty card" style="padding: 60px">
      <UiIcon name="alert" :size="26" />
      <p>报告加载失败</p>
      <button class="btn" @click="load">重试</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StatusPill from '@/components/StatusPill.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const router = useRouter()
const loading = ref(true)
const data = ref(null)
const audit = computed(() => data.value?.audit || null)

const termLabel = computed(() => {
  const map = { '1-1': '大一秋', '1-2': '大一春', '2-1': '大二秋', '2-2': '大二春', '3-1': '大三秋', '3-2': '大三春', '4-1': '大四秋', '4-2': '大四春' }
  return map[audit.value?.program_term] || ''
})

const summaryCards = computed(() => {
  if (!audit.value) return []
  const s = audit.value.summary
  return [
    { label: '总要求', value: s.require.toFixed(0), hint: '学分', tone: '' },
    { label: '已获', value: s.earned.toFixed(1), hint: '封顶后有效学分', tone: 'blue' },
    { label: '缺口', value: s.gap.toFixed(1), hint: '距离毕业', tone: 'danger' },
    { label: '在修', value: s.studying.toFixed(1), hint: '不计入已获', tone: 'amber' },
    { label: '超修', value: s.over.toFixed(1), hint: '封顶不计入', tone: 'green' },
  ]
})

const scState = computed(() => {
  const ok = audit.value?.graduation.second_classroom.ok
  return ok === true ? 'ok' : ok === null ? 'warn' : 'bad'
})

const scSummary = computed(() => {
  if (!audit.value) return []
  const items = audit.value.graduation.second_classroom.items || []
  const grouped = new Map()
  for (const item of items) {
    if (!grouped.has(item.category)) grouped.set(item.category, [])
    grouped.get(item.category).push(item)
  }
  return Array.from(grouped.entries()).map(([category, rows]) => {
    const unmet = rows.filter((r) => r.status === 'unmet')
    const missing = rows.filter((r) => r.status === 'missing')
    const last = rows[rows.length - 1]
    return {
      category,
      status: unmet.length ? 'unmet' : missing.length ? 'missing' : 'met',
      text: unmet.length ? `${unmet[0].message}` : missing.length ? '待确认' : '已达标',
    }
  })
})

const riskGroups = computed(() => {
  const risks = audit.value?.risks || []
  return [
    { key: 'high', label: '高风险', hint: '优先处理，可能影响按期毕业', items: risks.filter((risk) => risk.level === 'high') },
    { key: 'medium', label: '中风险', hint: '需要在本学期或下学期补齐', items: risks.filter((risk) => risk.level === 'medium') },
    { key: 'low', label: '低风险', hint: '持续关注即可', items: risks.filter((risk) => !['high', 'medium'].includes(risk.level)) },
  ].filter((group) => group.items.length)
})

const nextSteps = computed(() => {
  if (!audit.value) return []
  const steps = []
  const structure = audit.value.modules.find((m) => !m.child_ok)
  if (structure) steps.push(`优先补「${structure.name}」中带下限的子项，避免总量补满、结构仍不达标`)
  const sc = audit.value.graduation.second_classroom.items.filter((i) => i.status === 'unmet')
  for (const item of sc.slice(0, 2)) steps.push(`完成第二课堂「${item.category}」：${item.message}`)
  if (!audit.value.direction.locked) steps.push('锁定专业方向，并同步确定 2 学分创新实践选题')
  if (!audit.value.graduation.thesis.ok) steps.push('关注毕业设计（论文）开题、中期与答辩节点')
  steps.push('每学期出分后重新导入成绩，生成新的快照 diff')
  return steps.slice(0, 5)
})

function modeLabel(mode) {
  return { all_of: '全部满足', any_of: '任选其一', free: '总量约束' }[mode] || mode
}

function structureLabel(module) {
  if (module.child_ok) return '达标'
  if (module.mode === 'any_of') return '方向未修完'
  return '未达标'
}

function riskType(type) {
  return {
    credit_gap: '学分缺口',
    structure_gap: '结构缺口',
    structure_priority: '补课优先级',
    second_classroom: '第二课堂',
    thesis: '毕业答辩',
    direction_undecided: '方向决策',
    last_offering: '最后一次开课',
  }[type] || type
}

function riskTarget(risk) {
  if (risk.type === 'second_classroom') return '/second-classroom'
  if (risk.type === 'direction_undecided') return '/recommend'
  if (risk.type === 'thesis') return ''
  if (risk.type === 'last_offering') return '/recommend'
  return '/plan'
}

function print() {
  window.print()
}

async function load() {
  loading.value = true
  try {
    data.value = await api.report()
  } catch (error) {
    toast.error(getErrorMessage(error))
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.report-sheet {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 26px;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
  padding: 32px 38px 28px;
}

.report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}

.report-brand {
  display: flex;
  align-items: center;
  gap: 11px;
}

.report-logo {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 800;
  background: var(--grad);
}

.report-brand strong {
  display: block;
  font-size: 13px;
}

.report-brand span {
  display: block;
  font-size: 8px;
  letter-spacing: 0.16em;
  color: var(--muted-2);
  margin-top: 2px;
}

.report-id {
  display: grid;
  justify-items: end;
  gap: 2px;
  font-size: 9.5px;
  color: var(--muted-2);
}

.report-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  padding: 26px 0 22px;
}

.report-kicker {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted-2);
  margin-bottom: 7px;
}

.report-title h2 {
  font-size: 30px;
  letter-spacing: -0.035em;
}

.report-title p {
  margin-top: 7px;
  font-size: 11px;
  color: var(--muted);
}

.report-stamp {
  display: grid;
  justify-items: center;
  gap: 1px;
  padding: 12px 20px;
  border-radius: 16px;
  border: 1px solid rgba(18, 131, 111, 0.16);
  background: rgba(18, 131, 111, 0.04);
  flex: none;
}

.report-stamp.warn {
  border-color: rgba(178, 106, 27, 0.18);
  background: rgba(178, 106, 27, 0.04);
}

.report-stamp span {
  font-size: 9px;
  color: var(--muted);
}

.report-stamp strong {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #0b6b5b;
}

.report-stamp.warn strong {
  color: #94530f;
}

.report-stamp small {
  font-size: 8.5px;
  color: var(--muted-2);
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1px;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--line);
}

.rs-item {
  display: grid;
  gap: 2px;
  padding: 13px 16px;
  background: rgba(255, 255, 255, 0.86);
}

.rs-item span {
  font-size: 8.5px;
  color: var(--muted-2);
  letter-spacing: 0.06em;
}

.rs-item strong {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.rs-item strong.blue {
  color: var(--indigo);
}

.rs-item strong.danger {
  color: var(--rose);
}

.rs-item strong.amber {
  color: var(--amber);
}

.rs-item strong.green {
  color: var(--green);
}

.rs-item small {
  font-size: 8.5px;
  color: var(--muted-2);
}

.report-section {
  margin-top: 26px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head h3 {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 14px;
}

.sec-no {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--violet);
  background: rgba(30, 78, 216, 0.08);
  padding: 3px 6px;
  border-radius: 5px;
}

.sec-tag {
  font-size: 8.5px;
  color: var(--muted-2);
  letter-spacing: 0.04em;
}

.diff-headline {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 11px 13px;
  border-radius: 10px;
  background: rgba(18, 131, 111, 0.055);
  color: #0b6b5b;
  font-size: 11px;
  font-weight: 600;
}

.diff-body {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.diff-block {
  display: grid;
  gap: 6px;
}

.diff-block > strong {
  font-size: 10px;
  color: var(--muted);
}

.diff-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.diff-chip {
  font-size: 9px;
  padding: 3px 7px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted);
}

.report-table {
  font-size: 10.5px;
}

.report-table th {
  font-size: 8px;
  padding: 8px 10px;
}

.report-table td {
  padding: 9px 10px;
}

.report-table td strong {
  font-size: 10.5px;
}

.report-table .sub {
  font-size: 9px;
  color: var(--muted-2);
}

.child-row td {
  background: rgba(21, 32, 43, 0.018);
  color: var(--muted);
  font-size: 9.5px;
}

.child-line {
  color: var(--muted-2);
  margin-right: 5px;
}

.danger {
  color: #96332e !important;
}

.ok-text {
  color: #0b6b5b;
}

.danger-text {
  color: #96332e;
}

.table-note {
  margin-top: 8px;
  font-size: 8.5px;
  color: var(--muted-2);
  line-height: 1.6;
}

.grad-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.grad-box {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 13px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.55);
}

.grad-box.ok {
  border-color: rgba(18, 131, 111, 0.16);
  background: rgba(18, 131, 111, 0.03);
}

.grad-box.bad {
  border-color: rgba(184, 69, 63, 0.14);
  background: rgba(184, 69, 63, 0.025);
}

.grad-box.warn {
  border-color: rgba(178, 106, 27, 0.16);
  background: rgba(178, 106, 27, 0.03);
}

.grad-box-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.grad-box-head strong {
  font-size: 10.5px;
}

.grad-box-head span {
  margin-left: auto;
  font-size: 8px;
  font-weight: 700;
  color: #96332e;
  background: rgba(184, 69, 63, 0.08);
  padding: 2px 6px;
  border-radius: 99px;
}

.grad-box.ok .grad-box-head span {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.1);
}

.grad-box.warn .grad-box-head span {
  color: #94530f;
  background: rgba(178, 106, 27, 0.12);
}

.grad-num {
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.grad-num span {
  font-size: 10px;
  font-family: var(--font-sans);
  color: var(--muted-2);
  font-weight: 500;
}

.grad-mini-bar {
  height: 5px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.06);
  overflow: hidden;
}

.grad-mini-bar i {
  display: block;
  height: 100%;
  background: var(--grad);
}

.grad-box p {
  font-size: 8.5px;
  color: var(--muted-2);
  line-height: 1.55;
}

.sc-list {
  display: grid;
  gap: 3px;
}

.sc-list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 8.5px;
  color: var(--muted);
  padding-bottom: 3px;
  border-bottom: 1px dashed var(--line);
}

.sc-list strong {
  font-size: 8.5px;
  font-weight: 600;
}

.sc-list strong.met {
  color: #0b6b5b;
}

.sc-list strong.unmet {
  color: #96332e;
}

.sc-list strong.missing {
  color: var(--muted-2);
}

.thesis-state {
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 800;
  color: #96332e;
}

.grad-box.ok .thesis-state {
  color: #0b6b5b;
}

.risk-group + .risk-group {
  margin-top: 13px;
}

.risk-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}

.risk-group-head strong {
  font-size: 10px;
  font-weight: 650;
}

.rg-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted-2);
}

.rg-dot.high {
  background: var(--danger);
}

.rg-dot.medium {
  background: var(--warning);
}

.rg-count {
  min-width: 17px;
  padding: 1px 5px;
  border-radius: 8px;
  background: var(--surface-3);
  color: var(--muted);
  font-size: 8.5px;
  text-align: center;
}

.risk-group-head small {
  margin-left: auto;
  color: var(--muted-2);
  font-size: 8.5px;
}

.report-risks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
}

.report-risk {
  display: flex;
  gap: 8px;
  padding: 9px 11px;
  border-radius: 7px;
  background: rgba(21, 32, 43, 0.025);
  border-left: 3px solid var(--amber);
}

.report-risk.high {
  border-left-color: var(--rose);
  background: rgba(184, 69, 63, 0.035);
}

.rr-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--amber);
  margin-top: 5px;
  flex: none;
}

.report-risk.high .rr-dot {
  background: var(--rose);
}

.report-risk strong {
  display: block;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.55;
  color: var(--ink-2);
}

.report-risk span {
  font-size: 8.5px;
  color: var(--muted-2);
}

.rr-action {
  flex: none;
  align-self: flex-start;
  margin-left: auto;
  padding: 2px 4px;
  color: var(--violet);
  font-size: 8px;
  font-weight: 600;
  white-space: nowrap;
}

.rr-action:hover {
  text-decoration: underline;
}

.next-steps {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(30, 78, 216, 0.04);
}

.next-steps strong {
  font-size: 10px;
}

.next-steps ol {
  margin-top: 6px;
  padding-left: 16px;
  list-style: decimal;
  display: grid;
  gap: 3px;
}

.next-steps li {
  font-size: 9px;
  color: var(--muted);
  line-height: 1.55;
}

.next-steps li::marker {
  color: var(--violet);
}

.report-foot {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 26px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.report-foot strong {
  font-size: 9px;
}

.report-foot p {
  margin-top: 4px;
  font-size: 8px;
  color: var(--muted-2);
  line-height: 1.6;
  max-width: 620px;
}

.foot-mark {
  text-align: right;
  flex: none;
}

.foot-mark span {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.foot-mark small {
  font-size: 7px;
  letter-spacing: 0.18em;
  color: var(--muted-2);
}

@media (max-width: 1000px) {
  .grad-grid {
    grid-template-columns: 1fr;
  }

  .report-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .report-sheet {
    padding: 22px;
  }

  .report-title {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media print {
  .report-sheet {
    padding: 0;
    background: #fff;
    box-shadow: none;
    border: 0;
    border-radius: 0;
    backdrop-filter: none;
  }

  .report-section {
    break-inside: avoid;
  }

  .print-break {
    break-before: page;
  }
}
</style>
