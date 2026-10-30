<template>
  <div class="page admin-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">教务管理</h1>
        <p class="page-sub">方案校对、映射审核、第二课堂审核、学业大盘与方案试算。管理员端复用同一套确定性引擎，批量审核 0 token。</p>
      </div>
      <div class="row">
        <span class="chip chip-line">
          <UiIcon name="calendar" :size="13" />
          {{ meta.currentTerm }}
        </span>
        <button class="btn btn-sm" :disabled="loading" @click="loadAll">
          <UiIcon name="refresh" :size="14" />
          刷新
        </button>
      </div>
    </div>

    <div v-if="loading" class="skeleton" style="height: 520px" />

    <template v-else>
      <div class="admin-tabs card reveal">
        <button v-for="item in tabs" :key="item.key" :class="{ active: tab === item.key }" @click="tab = item.key">
          <UiIcon :name="item.icon" :size="15" />
          {{ item.label }}
          <span v-if="item.badge" class="tab-badge">{{ item.badge }}</span>
        </button>
      </div>

      <template v-if="tab === 'overview'">
        <div class="grid g4 stats-grid reveal reveal-2">
          <article v-for="stat in stats" :key="stat.label" class="stat card card-hover">
            <div class="stat-icon" :class="stat.tone"><UiIcon :name="stat.icon" :size="18" /></div>
            <div>
              <span>{{ stat.label }}</span>
              <strong>{{ stat.value }}</strong>
              <small>{{ stat.hint }}</small>
            </div>
          </article>
        </div>

        <div class="admin-grid">
          <div class="admin-main">
            <section class="card card-pad students-card reveal reveal-3">
            <div class="card-head">
              <div>
                <h3>学业大盘</h3>
                <p class="hint">按学号排序 · 点击行查看风险摘要</p>
              </div>
              <span class="chip chip-line">{{ dashboard?.summary.students || 0 }} 名学生</span>
            </div>
            <div class="table-wrap">
              <table class="table">
                <thead>
                  <tr>
                    <th>学生</th>
                    <th>年级</th>
                    <th>进度</th>
                    <th>已获 / 缺口</th>
                    <th>风险</th>
                    <th>毕业预演</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="student in dashboard?.students || []" :key="student.id">
                    <td>
                      <div class="student-cell">
                        <span class="student-avatar">{{ student.name.slice(0, 1) }}</span>
                        <div>
                          <strong>{{ student.name }}</strong>
                          <span>{{ student.student_no }} · {{ student.class_name }}</span>
                        </div>
                      </div>
                    </td>
                    <td>{{ student.grade }} 级</td>
                    <td>
                      <div class="progress-cell">
                        <div class="progress"><i :style="{ width: `${student.percent}%` }" /></div>
                        <span>{{ student.percent.toFixed(1) }}%</span>
                      </div>
                    </td>
                    <td class="mono">{{ student.earned.toFixed(1) }} / <span class="danger">{{ student.gap.toFixed(1) }}</span></td>
                    <td><span class="chip chip-danger">{{ student.risk_count }}</span></td>
                    <td>
                      <span class="chip" :class="student.graduation_ok ? 'chip-ok' : 'chip-warn'">
                        {{ student.graduation_ok ? '可毕业' : '未满足' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            </section>

            <section class="card card-pad risk-overview reveal reveal-4">
              <div class="card-head">
                <h3>风险摘要</h3>
                <span class="chip chip-danger">{{ dashboard?.summary.at_risk || 0 }} 人有风险</span>
              </div>
              <div class="risk-rows">
                <div v-for="student in (dashboard?.students || []).filter((s) => s.risk_count).slice(0, 4)" :key="student.id" class="risk-row">
                  <span class="student-avatar">{{ student.name.slice(0, 1) }}</span>
                  <div class="risk-main">
                    <strong>{{ student.name }}</strong>
                    <span>{{ student.top_risk || '存在未达标模块' }}</span>
                  </div>
                  <span class="chip chip-warn">缺口 {{ student.gap.toFixed(1) }}</span>
                </div>
              </div>
              <div class="quality-strip">
                <div><span>方案哈希</span><strong>{{ (dashboard?.plan?.hash || '未加载').slice(0, 12) }}{{ dashboard?.plan?.hash ? '…' : '' }}</strong></div>
                <div><span>引擎版本</span><strong>{{ meta.engineVersion || 'audit-engine/1.2.0' }}</strong></div>
                <div><span>待确认映射</span><strong>{{ dashboard?.summary.pending_mappings || 0 }}</strong></div>
                <div><span>待审第二课堂</span><strong>{{ dashboard?.summary.pending_second_classroom || 0 }}</strong></div>
              </div>
            </section>
          </div>

          <aside class="admin-side">
            <section class="card card-pad">
              <div class="card-head">
                <h3>模块缺口分布</h3>
                <span class="hint">平均缺口</span>
              </div>
              <EChart :option="moduleChart" height="250px" />
            </section>

            <section class="card card-pad queue-card">
              <div class="card-head">
                <h3>待处理队列</h3>
                <span class="chip chip-warn">{{ pendingTotal }}</span>
              </div>
              <button class="queue-item" @click="tab = 'mappings'">
                <span class="queue-icon"><UiIcon name="swap" :size="15" /></span>
                <div><strong>课程映射待确认</strong><span>低置信度匹配，确认后沉淀别名</span></div>
                <span class="queue-num">{{ mappings.length }}</span>
              </button>
              <button class="queue-item" @click="tab = 'second'">
                <span class="queue-icon amber"><UiIcon name="medal" :size="15" /></span>
                <div><strong>第二课堂待审核</strong><span>学生登记记录，审核后计入周期</span></div>
                <span class="queue-num">{{ scQueue.length }}</span>
              </button>
              <button class="queue-item" @click="tab = 'trial'">
                <span class="queue-icon blue"><UiIcon name="shield" :size="15" /></span>
                <div><strong>方案试算</strong><span>发布前与教务系统三列数字比对</span></div>
                <span class="queue-num">{{ plans.length }}</span>
              </button>
            </section>
          </aside>
        </div>
      </template>

      <section v-else-if="tab === 'mappings'" class="card card-pad reveal">
        <div class="card-head">
          <div>
            <h3>映射审核队列</h3>
            <p class="hint">置信度 &lt; 0.85 或未匹配的课程名会进入这里；确认后写入别名库，下次 L2 直接命中。</p>
          </div>
          <span class="chip chip-line">{{ mappings.length }} 条</span>
        </div>
        <div v-if="mappings.length" class="mapping-list">
          <div v-for="row in mappings" :key="row.id" class="mapping-row">
            <div class="mapping-raw">
              <strong>{{ row.raw_name }}</strong>
              <span>{{ row.raw_code || '无编码' }} · {{ row.method }} · {{ (row.confidence * 100).toFixed(0) }}%</span>
            </div>
            <UiIcon name="arrow-right" :size="14" class="muted" />
            <div class="mapping-target">
              <input v-model="mappingDraft[row.id]" class="input" placeholder="目标课程编码，如 B113101" />
              <span v-if="row.course_code" class="hint">建议：{{ row.course_code }}</span>
              <div v-if="row.context?.candidates" class="candidate-list">
                <button v-for="c in row.context.candidates" :key="c" @click="mappingDraft[row.id] = c">{{ c }}</button>
              </div>
            </div>
            <button class="btn btn-sm btn-primary" :disabled="!mappingDraft[row.id]" @click="confirmMapping(row)">
              确认并沉淀
            </button>
          </div>
        </div>
        <div v-else class="empty" style="padding: 40px">
          <UiIcon name="check" :size="22" />
          队列已清空
        </div>
      </section>

      <section v-else-if="tab === 'second'" class="card card-pad reveal">
        <div class="card-head">
          <div>
            <h3>第二课堂审核</h3>
            <p class="hint">审核通过后才计入周期达标；竞赛国家级奖励需证书，社会实践需组织单位证明。</p>
          </div>
          <span class="chip chip-line">{{ scQueue.length }} 条</span>
        </div>
        <div v-if="scQueue.length" class="sc-queue">
          <div v-for="row in scQueue" :key="row.id" class="sc-row">
            <div class="sc-row-main">
              <strong>{{ row.title }}</strong>
              <span>{{ row.student_name }}（{{ row.student_no }}） · {{ row.category }} · {{ row.term }} · {{ row.date }}</span>
              <small v-if="row.evidence">材料：{{ row.evidence }}</small>
            </div>
            <div class="row">
              <button class="btn btn-sm" @click="reviewSc(row, 'rejected')">驳回</button>
              <button class="btn btn-sm btn-primary" @click="reviewSc(row, 'approved')">通过</button>
            </div>
          </div>
        </div>
        <div v-else class="empty" style="padding: 40px">
          <UiIcon name="check" :size="22" />
          没有待审核记录
        </div>
      </section>

      <section v-else-if="tab === 'trial'" class="trial-grid reveal">
        <div class="card card-pad">
          <div class="card-head">
            <div>
              <h3>方案试算</h3>
              <p class="hint">选 3–5 个真实学生跑一遍审核，与教务系统“要求/获得/未获得”三列逐项比对，全部一致才允许发布。</p>
            </div>
            <button class="btn btn-sm btn-primary" :disabled="trialLoading" @click="runTrial">
              <UiIcon name="refresh" :size="14" />
              {{ trialLoading ? '试算中…' : '运行试算' }}
            </button>
          </div>

          <div class="plan-pick">
            <div class="plan-item" v-for="plan in plans" :key="plan.id" :class="{ active: selectedPlan === plan.id }" @click="selectedPlan = plan.id">
              <div>
                <strong>{{ plan.name }}</strong>
                <span>{{ plan.id }} · {{ plan.total_credits.toFixed(0) }} 学分 · {{ plan.status }}</span>
              </div>
              <span class="chip" :class="plan.status === 'frozen' ? 'chip-ok' : 'chip-warn'">{{ plan.status === 'frozen' ? '已冻结' : plan.status }}</span>
            </div>
          </div>

          <div v-if="trial" class="trial-results">
            <div class="trial-headline" :class="trial.all_consistent ? 'ok' : 'warn'">
              <UiIcon :name="trial.all_consistent ? 'check' : 'alert'" :size="15" />
              {{ trial.all_consistent ? '全部学生三列数字一致，可发布' : '存在不一致或缺少快照，发布前需人工复核' }}
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>学生</th>
                  <th>实际（引擎）</th>
                  <th>期望（快照）</th>
                  <th>模块缺口</th>
                  <th>结论</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in trial.students" :key="row.student_no">
                  <td><strong>{{ row.name }}</strong><br /><span class="hint">{{ row.student_no }}</span></td>
                  <td class="mono">{{ row.actual.earned.toFixed(1) }} / {{ row.actual.gap.toFixed(1) }}</td>
                  <td class="mono">
                    <template v-if="row.expected">{{ row.expected.earned.toFixed(1) }} / {{ row.expected.gap.toFixed(1) }}</template>
                    <span v-else class="hint">无快照</span>
                  </td>
                  <td>
                    <div class="module-mini">
                      <span v-for="m in row.modules" :key="m.id" :class="{ bad: m.gap > 0 }">{{ m.id }} {{ m.gap.toFixed(1) }}</span>
                    </div>
                  </td>
                  <td>
                    <span class="chip" :class="row.consistent === true ? 'chip-ok' : row.consistent === false ? 'chip-danger' : 'chip-warn'">
                      {{ row.consistent === true ? '一致' : row.consistent === false ? '不一致' : '无法比对' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="trial-actions">
              <span class="hint">{{ trial.note }}</span>
              <button class="btn btn-sm" @click="validatePlan">方案一致性校验</button>
              <button class="btn btn-sm btn-primary" :disabled="publishing" @click="publishPlan">
                {{ publishing ? '发布中…' : '冻结并发布' }}
              </button>
            </div>
            <div v-if="validation" class="validation-box" :class="validation.errors ? 'bad' : 'ok'">
              <strong>{{ validation.errors ? `${validation.errors} 项错误` : '一致性校验通过' }}</strong>
              <span v-if="validation.warnings">{{ validation.warnings }} 项提示</span>
              <ul v-if="validation.issues?.length">
                <li v-for="(issue, idx) in validation.issues.slice(0, 4)" :key="idx">{{ issue.message }}</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="card card-pad">
          <div class="card-head">
            <h3>开课计划</h3>
            <span class="chip chip-line">{{ offerings.length }} 条</span>
          </div>
          <div class="table-wrap">
            <table class="table offering-table">
              <thead>
                <tr>
                  <th>学期</th>
                  <th>课程</th>
                  <th>班级</th>
                  <th>时间</th>
                  <th>容量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in offerings.slice(0, 18)" :key="item.id">
                  <td class="mono">{{ item.semester }}</td>
                  <td>
                    <strong>{{ item.course_name }}</strong>
                    <span class="hint">{{ item.course_code }}</span>
                  </td>
                  <td>{{ item.class_id }} · {{ item.teacher }}</td>
                  <td>{{ item.time_slots.join(' / ') }}</td>
                  <td class="mono">{{ item.enrolled }} / {{ item.capacity }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </template>

      </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import EChart from '@/components/EChart.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useToastStore } from '@/stores/toast'

const meta = useMetaStore()
const toast = useToastStore()

const loading = ref(true)
const tab = ref('overview')
const dashboard = ref(null)
const mappings = ref([])
const scQueue = ref([])
const plans = ref([])
const offerings = ref([])
const selectedPlan = ref('')
const trial = ref(null)
const validation = ref(null)
const trialLoading = ref(false)
const publishing = ref(false)
const mappingDraft = reactive({})

const tabs = computed(() => [
  { key: 'overview', label: '概览', icon: 'chart' },
  { key: 'mappings', label: '映射审核', icon: 'swap', badge: mappings.value.length },
  { key: 'second', label: '第二课堂', icon: 'medal', badge: scQueue.value.length },
  { key: 'trial', label: '方案试算', icon: 'shield' },
])

const pendingTotal = computed(() => mappings.value.length + scQueue.value.length)
const stats = computed(() => {
  const s = dashboard.value?.summary || {}
  return [
    { label: '学生总数', value: s.students ?? '—', hint: '纳入学业大盘', icon: 'user', tone: 'violet' },
    { label: '平均完成度', value: `${(s.avg_percent ?? 0).toFixed(1)}%`, hint: '封顶后已获 / 169', icon: 'chart', tone: 'blue' },
    { label: '风险学生', value: s.at_risk ?? '—', hint: '缺口或第二课堂未达标', icon: 'alert', tone: 'amber' },
    { label: '待处理', value: pendingTotal.value, hint: '映射 + 第二课堂审核', icon: 'sliders', tone: 'green' },
  ]
})

const moduleChart = computed(() => {
  const modules = dashboard.value?.modules || []
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(11,18,38,.94)',
      borderWidth: 0,
      textStyle: { color: '#e8eeff', fontSize: 11 },
    },
    grid: { left: 4, right: 18, top: 10, bottom: 4, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(15,26,54,.06)', type: 'dashed' } },
      axisLabel: { color: '#8b94aa', fontSize: 9 },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: modules.map((m) => m.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#66708a', fontSize: 9 },
    },
    series: [
      {
        type: 'bar',
        data: modules.map((m) => m.avg_gap),
        barWidth: 9,
        itemStyle: {
          borderRadius: [0, 99, 99, 0],
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#1e4ed8' },
              { offset: 1, color: '#f59e0b' },
            ],
          },
        },
        label: { show: true, position: 'right', color: '#8b94aa', fontSize: 8.5, formatter: '{c}' },
      },
    ],
  }
})

async function loadAll() {
  loading.value = true
  try {
    const [dash, maps, sc, planRows, offerRows] = await Promise.all([
      api.adminDashboard(),
      api.adminMappings(),
      api.adminSecondClassroom(),
      api.adminPlans(),
      api.adminOfferings(),
    ])
    dashboard.value = dash
    mappings.value = maps
    scQueue.value = sc
    plans.value = planRows
    offerings.value = offerRows
    if (!selectedPlan.value && planRows.length) selectedPlan.value = planRows[0].id
    for (const row of maps) if (!mappingDraft[row.id]) mappingDraft[row.id] = row.course_code || ''
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    loading.value = false
  }
}

async function confirmMapping(row) {
  try {
    await api.confirmMapping(row.id, mappingDraft[row.id], true)
    toast.success('已确认并写入别名库')
    await loadAll()
  } catch (error) {
    toast.error(getErrorMessage(error))
  }
}

async function reviewSc(row, status) {
  try {
    await api.reviewSecondClassroom(row.id, status)
    toast.success(status === 'approved' ? '已通过，周期进度将更新' : '已驳回')
    await loadAll()
  } catch (error) {
    toast.error(getErrorMessage(error))
  }
}

async function runTrial() {
  if (!selectedPlan.value) return
  trialLoading.value = true
  try {
    trial.value = await api.adminTrial(selectedPlan.value)
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    trialLoading.value = false
  }
}

async function validatePlan() {
  if (!selectedPlan.value) return
  try {
    validation.value = await api.validation(selectedPlan.value)
  } catch (error) {
    toast.error(getErrorMessage(error))
  }
}

async function publishPlan() {
  if (!selectedPlan.value) return
  publishing.value = true
  try {
    await api.adminPublish(selectedPlan.value)
    toast.success('方案已冻结并发布')
    await loadAll()
    await runTrial()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    publishing.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.admin-tabs {
  display: flex;
  gap: 3px;
  padding: 5px;
  border-radius: 13px;
  width: fit-content;
  margin-bottom: 18px;
}

.admin-tabs button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  border-radius: 9px;
  font-size: 11.5px;
  color: var(--muted);
  transition: background 0.2s ease, color 0.2s ease;
}

.admin-tabs button.active {
  background: #fff;
  color: var(--ink);
  font-weight: 600;
  box-shadow: 0 3px 9px rgba(12, 22, 48, 0.07);
}

.tab-badge {
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 99px;
  background: rgba(184, 69, 63, 0.1);
  color: #96332e;
  font-size: 8.5px;
  display: grid;
  place-items: center;
}

.stats-grid {
  margin-bottom: 18px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 17px 18px;
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  flex: none;
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

.stat span {
  font-size: 9.5px;
  color: var(--muted-2);
}

.stat strong {
  display: block;
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.stat small {
  display: block;
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 2px;
}

.admin-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(330px, 0.7fr);
  gap: 18px;
  align-items: start;
}

.admin-main {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.risk-rows {
  display: grid;
  gap: 4px;
}

.risk-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--line);
}

.risk-row:last-child {
  border-bottom: 0;
}

.risk-main {
  display: grid;
  flex: 1;
  min-width: 0;
  gap: 1px;
}

.risk-main strong {
  font-size: 10.5px;
}

.risk-main span {
  font-size: 8.5px;
  color: var(--muted-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quality-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-top: 12px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--line);
  border: 1px solid var(--line);
}

.quality-strip div {
  display: grid;
  gap: 2px;
  padding: 9px 11px;
  background: rgba(255, 255, 255, 0.86);
}

.quality-strip span {
  font-size: 8px;
  color: var(--muted-2);
}

.quality-strip strong {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-side {
  display: grid;
  gap: 18px;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: 9px;
}

.student-avatar {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #fbfaf6;
  background: var(--ink);
  flex: none;
}

.student-cell strong {
  display: block;
  font-size: 11px;
}

.student-cell span {
  display: block;
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 1px;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 110px;
}

.progress-cell .progress {
  flex: 1;
}

.progress-cell span {
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--muted-2);
}

.danger {
  color: #96332e;
}

.queue-card {
  display: grid;
  gap: 4px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 6px;
  border-radius: 10px;
  text-align: left;
  border-bottom: 1px solid var(--line);
}

.queue-item:last-child {
  border-bottom: 0;
}

.queue-item:hover {
  background: rgba(21, 32, 43, 0.025);
}

.queue-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: var(--violet);
  background: rgba(30, 78, 216, 0.08);
  flex: none;
}

.queue-icon.amber {
  color: #94530f;
  background: rgba(178, 106, 27, 0.1);
}

.queue-icon.blue {
  color: #2f66e8;
  background: rgba(47, 102, 232, 0.08);
}

.queue-item div {
  display: grid;
  flex: 1;
  min-width: 0;
}

.queue-item strong {
  font-size: 10.5px;
}

.queue-item span {
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 1px;
}

.queue-num {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted);
  margin-left: auto;
}

.mapping-list,
.sc-queue {
  display: grid;
  gap: 8px;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 11px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.5);
}

.mapping-raw {
  min-width: 180px;
  display: grid;
  gap: 2px;
}

.mapping-raw strong {
  font-size: 11.5px;
}

.mapping-raw span {
  font-size: 8.5px;
  color: var(--muted-2);
}

.mapping-target {
  flex: 1;
  display: grid;
  gap: 3px;
}

.mapping-target .input {
  height: 34px;
  font-size: 10.5px;
  font-family: var(--font-mono);
}

.candidate-list {
  display: flex;
  gap: 5px;
}

.candidate-list button {
  font-size: 8.5px;
  color: var(--violet);
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(30, 78, 216, 0.06);
}

.mapping-row > .btn {
  flex: none;
}

.sc-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 13px;
  border-radius: 11px;
  border: 1px solid var(--line);
}

.sc-row-main {
  display: grid;
  gap: 3px;
  flex: 1;
}

.sc-row-main strong {
  font-size: 11.5px;
}

.sc-row-main span {
  font-size: 9px;
  color: var(--muted-2);
}

.sc-row-main small {
  font-size: 8.5px;
  color: var(--muted);
}

.trial-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(360px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.plan-pick {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
}

.plan-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  cursor: pointer;
}

.plan-item.active {
  border-color: rgba(30, 78, 216, 0.32);
  background: rgba(30, 78, 216, 0.045);
}

.plan-item strong {
  display: block;
  font-size: 11px;
}

.plan-item span {
  font-size: 8.5px;
  color: var(--muted-2);
}

.trial-headline {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 10.5px;
  margin-bottom: 10px;
}

.trial-headline.ok {
  background: rgba(18, 131, 111, 0.07);
  color: #0b6b5b;
}

.trial-headline.warn {
  background: rgba(178, 106, 27, 0.08);
  color: #92400e;
}

.module-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.module-mini span {
  font-family: var(--font-mono);
  font-size: 8px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(18, 131, 111, 0.07);
  color: #0b6b5b;
}

.module-mini span.bad {
  background: rgba(184, 69, 63, 0.07);
  color: #96332e;
}

.trial-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 9px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.validation-box {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 9.5px;
  line-height: 1.55;
}

.validation-box.ok {
  background: rgba(18, 131, 111, 0.05);
  color: #0b6b5b;
}

.validation-box.bad {
  background: rgba(184, 69, 63, 0.05);
  color: #96332e;
}

.validation-box strong {
  font-size: 10px;
  margin-right: 8px;
}

.validation-box span {
  font-size: 8.5px;
  color: var(--muted-2);
}

.validation-box ul {
  margin-top: 5px;
  padding-left: 14px;
  list-style: disc;
}

.validation-box li {
  font-size: 8.5px;
  color: var(--muted);
}

.offering-table strong {
  display: block;
  font-size: 10px;
}

.offering-table .hint {
  display: block;
  font-size: 8.5px;
}

@media (max-width: 1200px) {
  .admin-grid,
  .trial-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .mapping-row,
  .sc-row {
    flex-direction: column;
    align-items: stretch;
  }

  .admin-tabs {
    width: 100%;
    overflow-x: auto;
  }
}
</style>

