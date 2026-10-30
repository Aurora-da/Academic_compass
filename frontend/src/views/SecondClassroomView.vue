<template>
  <div class="page sc-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">第二课堂</h1>
        <p class="page-sub">毕业条件之二。它不是一次性学分，而是“事件 + 周期”的合规检查：每学年、每学期分别判定。</p>
      </div>
      <div class="row">
        <span class="chip" :class="okClass">
          <span class="dot" :class="okDot" />
          {{ okLabel }}
        </span>
        <button class="btn btn-sm btn-primary" @click="openModal">
          <UiIcon name="plus" :size="14" />
          登记活动
        </button>
      </div>
    </div>

    <div v-if="loading" class="grid g4">
      <div v-for="i in 4" :key="i" class="skeleton" style="height: 190px" />
    </div>

    <template v-else-if="data">
      <div v-if="pendingItems.length" class="sc-reminder reveal">
        <span class="alert-ic"><UiIcon name="alert" :size="15" /></span>
        <div class="sc-reminder-body">
          <strong>{{ data.current_term }} 仍需完成 {{ pendingItems.length }} 项</strong>
          <span>{{ pendingItems.map((item) => `${item.category}（${item.period_label}）`).join('、') }} · 审核通过后才计入周期达标</span>
        </div>
        <button class="btn btn-sm" @click="focusDetails">查看明细</button>
      </div>

      <div class="sc-grid reveal">
        <article v-for="group in groups" :key="group.category" class="sc-card card card-hover">
          <div class="sc-card-top">
            <div class="sc-icon" :class="group.tone">
              <UiIcon :name="group.icon" :size="19" />
            </div>
            <StatusPill :status="group.status" />
          </div>
          <h3>{{ group.category }}</h3>
          <p class="sc-period">{{ group.rule }}</p>
          <div class="sc-donut-row">
            <div
              class="sc-donut"
              :style="{
                background: `conic-gradient(${group.color} ${group.percent}%, rgba(15,26,54,.06) ${group.percent}% 100%)`,
              }"
            >
              <span>{{ group.percent }}<i>%</i></span>
            </div>
            <div class="sc-donut-meta">
              <span>{{ group.met }} 项达标</span>
              <span v-if="group.unmet">{{ group.unmet }} 项未达标</span>
              <span v-else-if="group.missing">{{ group.missing }} 项待确认</span>
              <span v-else>全部周期已满足</span>
            </div>
          </div>
          <div class="sc-items">
            <div v-for="item in group.items" :key="item.period_label" class="sc-item">
              <span class="sc-item-period">{{ item.period_label }}</span>
              <span class="sc-item-num">{{ item.done }} / {{ item.require }}</span>
              <span class="sc-item-status" :class="item.status">{{ statusText(item.status) }}</span>
            </div>
          </div>
        </article>
      </div>

      <div class="sc-layout">
        <section class="card card-pad sc-detail reveal reveal-2">
          <div class="card-head">
            <div>
              <h3>周期判定明细</h3>
              <p class="hint">{{ data.current_term }} · 当前学年进行中的项目不作最终判定</p>
            </div>
            <span class="chip chip-line">{{ data.items.length }} 个周期</span>
          </div>
          <div class="period-list">
            <div v-for="item in data.items" :key="`${item.category}-${item.period_label}`" class="period-row">
              <div class="period-main">
                <div class="period-title">
                  <span class="period-cat">{{ item.category }}</span>
                  <span class="period-label">{{ item.period_label }}</span>
                </div>
                <div class="period-bar">
                  <i
                    :style="{ width: `${Math.min(100, (item.done / Math.max(1, item.require)) * 100)}%` }"
                    :class="item.status"
                  />
                </div>
                <span class="period-msg">{{ item.message }}</span>
              </div>
              <div class="period-right">
                <strong>{{ item.done }}<i>/{{ item.require }}</i></strong>
                <StatusPill :status="item.status" />
              </div>
            </div>
          </div>
          <div class="period-note">
            <UiIcon name="info" :size="14" />
            <p>
              “数据缺失”既不算过也不算不过：未接入书院系统时，学生手动登记 + 教学秘书审核是唯一可行路径。
              只有审核通过的记录才计入达标次数。
            </p>
          </div>
        </section>

        <section class="card card-pad sc-records reveal reveal-3">
          <div class="card-head">
            <h3>登记记录</h3>
            <span class="chip chip-line">{{ data.records.length }} 条</span>
          </div>
          <div v-if="data.records.length" class="record-list">
            <div v-for="record in data.records" :key="record.id" class="record">
              <div class="record-dot" :class="record.status" />
              <div class="record-main">
                <strong>{{ record.title }}</strong>
                <span>{{ record.category }} · {{ record.term }}<template v-if="record.date"> · {{ record.date }}</template></span>
              </div>
              <StatusPill :status="record.status" />
            </div>
          </div>
          <div v-else class="empty" style="padding: 34px">
            <UiIcon name="medal" :size="22" />
            还没有登记记录
          </div>
          <div class="record-tip">
            待审核记录不会计入达标次数。教学秘书审核通过后，周期进度会自动更新。
          </div>
        </section>
      </div>
    </template>

    <div v-else class="empty card" style="padding: 60px">
      <UiIcon name="alert" :size="26" />
      <p>第二课堂数据加载失败</p>
      <button class="btn" @click="load">重试</button>
    </div>

    <AppModal :open="modalOpen" title="登记第二课堂活动" subtitle="提交后由教学秘书审核，通过后计入周期达标" @close="modalOpen = false">
      <div class="form-grid">
        <div class="field">
          <label>类别</label>
          <select v-model="form.category" class="select">
            <option v-for="req in requirements" :key="req.category" :value="req.category">{{ req.category }}</option>
          </select>
        </div>
        <div class="field">
          <label>学期</label>
          <input v-model="form.term" class="input" placeholder="2025-2026-2" />
        </div>
        <div class="field">
          <label>日期</label>
          <input v-model="form.date" class="input" type="date" />
        </div>
        <div class="field" style="grid-column: 1 / -1">
          <label>活动 / 成果名称</label>
          <input v-model="form.title" class="input" placeholder="如：暑期三下乡社会实践、国家级竞赛获奖" />
        </div>
        <div class="field" style="grid-column: 1 / -1">
          <label>证明材料（可选）</label>
          <input v-model="form.evidence" class="input" placeholder="文件名或链接，便于审核" />
        </div>
      </div>
      <div class="modal-note">
        <UiIcon name="info" :size="13" />
        竞赛国家级奖励需上传证书；社会实践需提供组织单位证明。审核通过前不计入达标。
      </div>
      <template #footer>
        <button class="btn" @click="modalOpen = false">取消</button>
        <button class="btn btn-primary" :disabled="submitting || !form.title" @click="submit">
          <span v-if="submitting" class="spinner" />
          {{ submitting ? '提交中…' : '提交审核' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppModal from '@/components/AppModal.vue'
import StatusPill from '@/components/StatusPill.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useToastStore } from '@/stores/toast'

const meta = useMetaStore()
const toast = useToastStore()

const loading = ref(true)
const data = ref(null)
const modalOpen = ref(false)
const submitting = ref(false)

const form = reactive({
  category: '主题社会实践',
  term: meta.currentTerm,
  date: new Date().toISOString().slice(0, 10),
  title: '',
  evidence: '',
})

const CATEGORY_META = {
  主题社会实践: { icon: 'compass', tone: 'violet', color: '#1e4ed8', rule: '每学年 ≥ 1 次' },
  创新实践: { icon: 'sparkles', tone: 'blue', color: '#2f66e8', rule: '每学年 ≥ 1 项总结报告' },
  学科竞赛与项目: { icon: 'medal', tone: 'amber', color: '#f59e0b', rule: '至少 1 项国家级奖励' },
  学术交流研讨: { icon: 'user', tone: 'green', color: '#0b8f7b', rule: '每学期 ≥ 2 次' },
}

const requirements = computed(() => data.value?.requirements || [])

const okClass = computed(() => (data.value?.ok === true ? 'chip-ok' : data.value?.ok === null ? 'chip-warn' : 'chip-danger'))
const okDot = computed(() => (data.value?.ok === true ? '' : data.value?.ok === null ? 'warn' : 'danger'))
const okLabel = computed(() =>
  data.value?.ok === true ? '第二课堂已达标' : data.value?.ok === null ? '第二课堂待确认' : '存在未达标项',
)

const groups = computed(() => {
  if (!data.value) return []
  const items = data.value.items || []
  const categories = requirements.value.map((r) => r.category)
  for (const item of items) if (!categories.includes(item.category)) categories.push(item.category)
  return categories.map((category) => {
    const rows = items.filter((i) => i.category === category)
    const met = rows.filter((r) => r.status === 'met').length
    const unmet = rows.filter((r) => r.status === 'unmet').length
    const missing = rows.filter((r) => r.status === 'missing').length
    const total = rows.length || 1
    const percent = Math.round(
      (rows.reduce((sum, r) => sum + Math.min(1, r.done / Math.max(1, r.require)), 0) / total) * 100,
    )
    const metaItem = CATEGORY_META[category] || { icon: 'medal', tone: 'violet', color: '#1e4ed8', rule: '周期要求' }
    return {
      category,
      items: rows,
      met,
      unmet,
      missing,
      percent,
      status: unmet ? 'unmet' : missing ? 'missing' : 'met',
      ...metaItem,
      rule: metaItem.rule,
    }
  })
})

const pendingItems = computed(() =>
  (data.value?.items || []).filter((item) => item.status !== 'met' && item.done < item.require).slice(0, 4),
)

function focusDetails() {
  document.querySelector('.sc-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function statusText(status) {
  return { met: '达标', unmet: '未达标', missing: '待确认' }[status] || status
}

function openModal() {
  form.category = requirements.value[0]?.category || '主题社会实践'
  form.term = data.value?.current_term || meta.currentTerm
  form.title = ''
  form.evidence = ''
  modalOpen.value = true
}

async function submit() {
  if (!form.title.trim()) return
  submitting.value = true
  try {
    const result = await api.addSecondClassroom({ ...form })
    toast.success(result.message)
    modalOpen.value = false
    await load()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function load() {
  loading.value = true
  try {
    data.value = await api.secondClassroom()
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
.sc-reminder {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 13px 15px;
  border: 1px solid var(--warning-line);
  border-radius: var(--r-md);
  background: var(--warning-bg);
}

.sc-reminder .alert-ic {
  flex: none;
  color: var(--warning);
  background: rgba(178, 106, 27, 0.1);
}

.sc-reminder-body {
  display: grid;
  flex: 1;
  gap: 2px;
  min-width: 0;
}

.sc-reminder-body strong {
  color: var(--warning);
  font-size: 12.5px;
  font-weight: 650;
}

.sc-reminder-body span {
  overflow: hidden;
  color: var(--ink-2);
  font-size: 11px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-reminder .btn {
  flex: none;
}

.sc-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.sc-card {
  padding: 18px;
  display: grid;
  gap: 9px;
}

.sc-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sc-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #1e4ed8;
  background: rgba(30, 78, 216, 0.1);
}

.sc-icon.blue {
  color: #2f66e8;
  background: rgba(47, 102, 232, 0.1);
}

.sc-icon.amber {
  color: #94530f;
  background: rgba(178, 106, 27, 0.12);
}

.sc-icon.green {
  color: #0b6b5b;
  background: rgba(11, 143, 123, 0.12);
}

.sc-card h3 {
  font-size: 14px;
}

.sc-period {
  font-size: 9.5px;
  color: var(--muted-2);
}

.sc-donut-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.sc-donut {
  width: 62px;
  height: 62px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  flex: none;
  position: relative;
  transition: background 0.8s ease;
}

.sc-donut::after {
  content: "";
  position: absolute;
  inset: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
}

.sc-donut span {
  position: relative;
  z-index: 1;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 800;
}

.sc-donut i {
  font-style: normal;
  font-size: 8px;
  color: var(--muted-2);
}

.sc-donut-meta {
  display: grid;
  gap: 2px;
  font-size: 9px;
  color: var(--muted-2);
}

.sc-items {
  display: grid;
  gap: 3px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
}

.sc-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
}

.sc-item-period {
  color: var(--muted-2);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sc-item-num {
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--muted);
}

.sc-item-status {
  font-size: 8px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted-2);
}

.sc-item-status.met {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.08);
}

.sc-item-status.unmet {
  color: #96332e;
  background: rgba(184, 69, 63, 0.08);
}

.sc-item-status.missing {
  color: #94530f;
  background: rgba(178, 106, 27, 0.1);
}

.sc-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  gap: 18px;
  margin-top: 18px;
  align-items: start;
}

.sc-detail {
  min-width: 0;
}

.period-list {
  display: grid;
  gap: 4px;
}

.period-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 10px;
  border-radius: 10px;
  border-bottom: 1px solid var(--line);
}

.period-row:last-child {
  border-bottom: 0;
}

.period-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 5px;
}

.period-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.period-cat {
  font-size: 10.5px;
  font-weight: 600;
}

.period-label {
  font-size: 8.5px;
  color: var(--muted-2);
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(21, 32, 43, 0.04);
}

.period-bar {
  height: 4px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.05);
  overflow: hidden;
}

.period-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--green);
}

.period-bar i.unmet {
  background: var(--rose);
}

.period-bar i.missing {
  background: var(--amber);
}

.period-msg {
  font-size: 8.5px;
  color: var(--muted-2);
}

.period-right {
  display: grid;
  justify-items: end;
  gap: 4px;
  flex: none;
}

.period-right strong {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 800;
}

.period-right strong i {
  font-style: normal;
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 500;
  color: var(--muted-2);
}

.period-note {
  display: flex;
  gap: 7px;
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 9px;
  background: rgba(21, 32, 43, 0.025);
  color: var(--muted);
}

.period-note p {
  font-size: 9px;
  line-height: 1.6;
}

.sc-records {
  min-width: 0;
}

.record-list {
  display: grid;
  gap: 2px;
  max-height: 430px;
  overflow-y: auto;
}

.record {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--line);
}

.record:last-child {
  border-bottom: 0;
}

.record-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  flex: none;
}

.record-dot.pending {
  background: var(--amber);
}

.record-dot.rejected {
  background: var(--rose);
}

.record-main {
  display: grid;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.record-main strong {
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1.45;
}

.record-main span {
  font-size: 8.5px;
  color: var(--muted-2);
}

.record-tip {
  margin-top: 12px;
  padding: 9px 11px;
  border-radius: 8px;
  background: rgba(178, 106, 27, 0.055);
  color: #92400e;
  font-size: 8.5px;
  line-height: 1.55;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.modal-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 14px;
  padding: 9px 11px;
  border-radius: 9px;
  background: rgba(30, 78, 216, 0.05);
  color: var(--muted);
  font-size: 9.5px;
  line-height: 1.55;
}

@media (max-width: 1200px) {
  .sc-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sc-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .sc-grid {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
