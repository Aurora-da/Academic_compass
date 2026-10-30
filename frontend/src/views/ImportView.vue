<template>
  <div class="page import-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">数据导入</h1>
        <p class="page-sub">四级接入：浏览器插件 → 文件导入 → 开放 API → 服务端代取。能从页面抓就别解析 PDF。</p>
      </div>
      <div class="row">
        <button class="btn btn-sm" @click="downloadTemplate">
          <UiIcon name="download" :size="14" />
          下载示例模板
        </button>
      </div>
    </div>

    <section class="import-steps card reveal">
      <div v-for="(step, idx) in steps" :key="step.title" class="import-step" :class="{ active: stepIdx >= idx, current: stepIdx === idx }">
        <span class="step-no">{{ String(idx + 1).padStart(2, '0') }}</span>
        <div>
          <strong>{{ step.title }}</strong>
          <span>{{ step.desc }}</span>
        </div>
      </div>
    </section>

    <div class="import-layout">
      <div class="import-main">
        <section class="card card-pad upload-card reveal reveal-2">
          <div class="tabs">
            <button :class="{ active: mode === 'file' }" @click="mode = 'file'">
              <UiIcon name="upload" :size="14" />文件导入
            </button>
            <button :class="{ active: mode === 'plugin' }" @click="mode = 'plugin'">
              <UiIcon name="database" :size="14" />插件同步
            </button>
          </div>

          <div v-if="mode === 'file'">
            <div
              class="dropzone"
              :class="{ dragging, parsing }"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="onDrop"
              @click="picker.click()"
            >
              <input ref="picker" type="file" accept=".pdf,.xlsx,.docx,.csv,.json" hidden @change="onPick" />
              <div class="drop-icon">
                <UiIcon :name="parsing ? 'refresh' : 'upload'" :size="24" />
              </div>
              <strong>{{ parsing ? '正在解析…' : '拖入成绩单，或点击选择文件' }}</strong>
              <span>支持 PDF 表格 / Excel / Word / CSV / JSON，单文件 ≤ 20MB</span>
              <div class="drop-formats">
                <span>教务导出</span>
                <span>插件 JSON</span>
                <span>扫描件 OCR 兜底</span>
              </div>
            </div>
            <div class="upload-hint">
              <UiIcon name="shield" :size="13" />
              文件只在服务端解析后立即删除，保留结构化结果与置信度；不保存原始证件与敏感字段。
            </div>
          </div>

          <div v-else class="plugin-panel">
            <div class="plugin-head">
              <div>
                <strong>粘贴 Canonical JSON</strong>
                <p>浏览器插件只上传结构化数据，凭据不出本机，准确率接近 100%。</p>
              </div>
              <button class="btn btn-sm" @click="fillPluginExample">填入示例</button>
            </div>
            <textarea v-model="pluginText" class="textarea mono" rows="9" placeholder='{"courses":[...]}' />
            <div class="row" style="justify-content: flex-end; margin-top: 10px">
              <button class="btn btn-sm btn-primary" :disabled="parsing" @click="submitPlugin">
                <UiIcon name="upload" :size="14" />
                {{ parsing ? '同步中…' : '同步并预览' }}
              </button>
            </div>
          </div>
        </section>

        <section v-if="rows.length" class="card card-pad review-card reveal reveal-3">
          <div class="card-head">
            <div>
              <h3>解析结果校对</h3>
              <p class="hint">
                共 {{ rows.length }} 条 · 已匹配 {{ matchedCount }} 条 · 需人工确认 {{ confirmCount }} 条
              </p>
            </div>
            <div class="row">
              <span v-if="job?.filename" class="chip chip-line">{{ job.filename }}</span>
              <button class="btn btn-sm btn-primary" :disabled="applying" @click="apply">
                <span v-if="applying" class="spinner" />
                {{ applying ? '入库中…' : '确认入库' }}
              </button>
            </div>
          </div>

          <div class="table-wrap">
            <table class="table review-table">
              <thead>
                <tr>
                  <th>原文</th>
                  <th>匹配课程</th>
                  <th>学期</th>
                  <th>状态</th>
                  <th>学分</th>
                  <th>成绩</th>
                  <th>置信度</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.index" :class="{ low: row.need_confirm }">
                  <td>
                    <div class="raw-name">
                      <strong>{{ row.raw_name }}</strong>
                      <span v-if="row.raw_code">{{ row.raw_code }}</span>
                    </div>
                  </td>
                  <td>
                    <input v-model="row.course_code" class="mini-input mono" placeholder="课程编码" />
                    <div v-if="row.course_name" class="matched-name">{{ row.course_name }}</div>
                    <div v-else-if="row.candidates?.length" class="candidate-list">
                      <button
                        v-for="candidate in row.candidates.slice(0, 2)"
                        :key="candidate.code"
                        @click="row.course_code = candidate.code; row.course_name = candidate.name"
                      >
                        {{ candidate.name }} · {{ candidate.score.toFixed(2) }}
                      </button>
                    </div>
                  </td>
                  <td><input v-model="row.raw_term" class="mini-input mono" /></td>
                  <td>
                    <select v-model="row.raw_status" class="mini-input">
                      <option value="passed">通过</option>
                      <option value="studying">在修</option>
                      <option value="failed">未通过</option>
                      <option value="withdrawn">退课</option>
                      <option value="skip">跳过</option>
                    </select>
                  </td>
                  <td><input v-model.number="row.raw_credit" class="mini-input mono" type="number" step="0.5" /></td>
                  <td><input v-model.number="row.raw_score" class="mini-input mono" type="number" /></td>
                  <td>
                    <div class="confidence" :class="confidenceTone(row)">
                      <span>{{ Math.round((row.confidence || 0) * 100) }}%</span>
                      <i><b :style="{ width: `${(row.confidence || 0) * 100}%` }" /></i>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="review-note">
            <UiIcon name="info" :size="13" />
            低置信度行会被标记并写入映射队列；确认后自动沉淀别名，下次直接命中。未匹配的行可在管理员端人工确认。
          </div>
        </section>
      </div>

      <aside class="import-side">
        <section class="card card-pad reveal reveal-3">
          <div class="card-head">
            <h3>导入历史</h3>
            <span class="chip chip-line">{{ jobs.length }} 次</span>
          </div>
          <div v-if="jobs.length" class="job-list">
            <button v-for="j in jobs" :key="j.id" class="job-item" @click="loadJob(j.id)">
              <div class="job-icon" :class="j.source">
                <UiIcon :name="j.source === 'plugin' ? 'database' : 'upload'" :size="14" />
              </div>
              <div class="job-main">
                <strong>{{ j.filename }}</strong>
                <span>
                  {{ j.created_at?.slice(0, 16).replace('T', ' ') }}
                  · {{ j.summary?.total || 0 }} 条
                  <template v-if="j.applied"> · 入库 {{ j.applied.added + j.applied.updated }}</template>
                </span>
              </div>
              <StatusPill :status="j.status === 'confirmed' ? 'approved' : 'pending'" :label="j.status === 'confirmed' ? '已入库' : '待确认'" />
            </button>
          </div>
          <div v-else class="empty" style="padding: 28px">
            <UiIcon name="upload" :size="20" />
            还没有导入记录
          </div>
        </section>

        <section class="card card-pad reveal reveal-4">
          <div class="card-head">
            <h3>四级接入</h3>
            <span class="hint">合规底线</span>
          </div>
          <div class="access-list">
            <div v-for="item in accessModes" :key="item.name" class="access-item" :class="{ primary: item.primary }">
              <span class="access-tag">{{ item.tag }}</span>
              <div>
                <strong>{{ item.name }}</strong>
                <span>{{ item.desc }}</span>
              </div>
            </div>
          </div>
          <p class="access-note">
            不存明文密码｜显式授权可撤回｜最小字段集｜日志脱敏｜频率限制｜校内私有化部署。
          </p>
        </section>
      </aside>
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

const mode = ref('file')
const dragging = ref(false)
const parsing = ref(false)
const applying = ref(false)
const picker = ref(null)
const rows = ref([])
const job = ref(null)
const jobs = ref([])
const pluginText = ref('')
const appliedInfo = ref(null)

const steps = [
  { title: '上传 / 同步', desc: 'PDF、Excel、Word 或插件 JSON' },
  { title: '逐字段校对', desc: '保留原文与置信度，低置信度人工确认' },
  { title: '入库并重算', desc: '写入修读记录，审核引擎立即重算' },
]

const stepIdx = computed(() => (appliedInfo.value ? 2 : rows.value.length ? 1 : 0))
const matchedCount = computed(() => rows.value.filter((r) => r.course_code).length)
const confirmCount = computed(() => rows.value.filter((r) => r.need_confirm || !r.course_code).length)

const accessModes = [
  { tag: 'M0', name: '浏览器插件抓取', desc: '读当前页 DOM / 接口 JSON，不传账号密码', primary: true },
  { tag: 'M3', name: '文件导入', desc: 'PDF / Excel / Word 兜底，逐字段校对' },
  { tag: 'M1', name: '开放 API', desc: '校方数据中台，OAuth2 只读，需学校配合' },
  { tag: 'M2', name: '服务端代取', desc: 'CAS 登录后抓页，需明确授权与频率限制' },
]

function parseRows(payload) {
  rows.value = (payload.rows || []).map((row) => ({ ...row }))
  job.value = payload
  appliedInfo.value = null
  if (!rows.value.length) toast.error('没有解析出课程记录')
}

async function onPick(event) {
  const file = event.target.files?.[0]
  if (file) await upload(file)
  event.target.value = ''
}

async function onDrop(event) {
  dragging.value = false
  const file = event.dataTransfer.files?.[0]
  if (file) await upload(file)
}

async function upload(file) {
  parsing.value = true
  try {
    const data = await api.upload(file)
    parseRows(data)
    toast.success(`解析完成：${data.summary.total} 条，匹配 ${data.summary.matched} 条`)
    await loadJobs()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    parsing.value = false
  }
}

function fillPluginExample() {
  pluginText.value = JSON.stringify(
    {
      student: { sid: '2023001', name: '张三' },
      courses: [
        { code: 'B034913', name: '编译原理', credit: 3, term: '2025-2026-2', status: '在修' },
        { code: 'B035013', name: '神经网络与深度学习', credit: 2, term: '2025-2026-1', status: '通过', score: 90 },
        { code: '', name: '高等数学A(上)', credit: 5, term: '2023-2024-1', status: '通过', score: 92 },
      ],
      meta: { source: 'plugin:demo', parser: 'v1.2.0', confidence: 0.99 },
    },
    null,
    2,
  )
}

async function submitPlugin() {
  parsing.value = true
  try {
    const payload = JSON.parse(pluginText.value)
    if (!Array.isArray(payload.courses) || !payload.courses.length) throw new Error('JSON 中缺少 courses 数组')
    const data = await api.pluginImport(payload.courses, false)
    parseRows(data)
    mode.value = 'file'
    toast.success('插件数据已同步，请校对后入库')
    await loadJobs()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    parsing.value = false
  }
}

async function apply() {
  if (!job.value?.job_id && !job.value?.id) return
  const jobId = job.value.job_id || job.value.id
  applying.value = true
  try {
    const items = rows.value.map((row) => ({
      index: row.index,
      course_code: row.course_code || null,
      course_name: row.course_name || row.raw_name,
      credit: Number(row.raw_credit),
      term: row.raw_term,
      status: row.raw_status,
      score: row.raw_score === '' || row.raw_score === null ? null : Number(row.raw_score),
    }))
    const result = await api.reviewDocument(jobId, items, true)
    appliedInfo.value = result
    toast.success(`入库完成：新增 ${result.added} 条，更新 ${result.updated} 条，跳过 ${result.skipped} 条`)
    await loadJobs()
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    applying.value = false
  }
}

async function loadJob(id) {
  try {
    const data = await api.document(id)
    parseRows({ ...data, job_id: data.id })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    toast.error(getErrorMessage(error))
  }
}

async function loadJobs() {
  try {
    jobs.value = await api.documents()
  } catch {
    jobs.value = []
  }
}

function confidenceTone(row) {
  if (row.confidence >= 0.95) return 'high'
  if (row.confidence >= 0.85) return 'mid'
  return 'low'
}

function downloadTemplate() {
  const content =
    '课程号,课程名称,学分,学期,修读状态,成绩\n' +
    'B034913,编译原理,3,2025-2026-2,在修,\n' +
    'B035013,神经网络与深度学习,2,2025-2026-1,通过,90\n' +
    'B034910,操作系统,3.5,2025-2026-2,在修,\n'
  const blob = new Blob([`\uFEFF${content}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '成绩单导入模板.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(loadJobs)
</script>

<style scoped>
.import-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  background: var(--line);
}

.import-step {
  display: flex;
  gap: 12px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.8);
  opacity: 0.55;
  transition: background 0.3s ease, opacity 0.3s ease;
}

.import-step.active {
  opacity: 1;
}

.import-step.current {
  background: rgba(30, 78, 216, 0.055);
}

.step-no {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--violet);
  background: rgba(30, 78, 216, 0.08);
  height: 24px;
  padding: 0 6px;
  border-radius: 6px;
  display: grid;
  place-items: center;
}

.import-step strong {
  display: block;
  font-size: 11.5px;
}

.import-step span {
  display: block;
  font-size: 9.5px;
  color: var(--muted-2);
  margin-top: 3px;
}

.import-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.7fr);
  gap: 18px;
  margin-top: 18px;
  align-items: start;
}

.import-main,
.import-side {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 10px;
  background: rgba(21, 32, 43, 0.04);
  width: fit-content;
  margin-bottom: 16px;
}

.tabs button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  font-size: 10.5px;
  color: var(--muted);
}

.tabs button.active {
  background: #fff;
  color: var(--ink);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(12, 22, 48, 0.07);
}

.dropzone {
  display: grid;
  justify-items: center;
  gap: 7px;
  padding: 46px 22px;
  border-radius: 16px;
  border: 1.5px dashed rgba(30, 78, 216, 0.24);
  background: rgba(30, 78, 216, 0.025);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease, transform 0.25s ease;
}

.dropzone:hover,
.dropzone.dragging {
  border-color: rgba(30, 78, 216, 0.5);
  background: rgba(30, 78, 216, 0.055);
  transform: translateY(-1px);
}

.dropzone.parsing {
  pointer-events: none;
  opacity: 0.7;
}

.dropzone.parsing .drop-icon svg {
  animation: spin 1s linear infinite;
}

.drop-icon {
  width: 56px;
  height: 56px;
  border-radius: 17px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--grad);
  box-shadow: 0 14px 30px rgba(47, 102, 232, 0.25);
  margin-bottom: 4px;
}

.dropzone strong {
  font-size: 13px;
}

.dropzone > span {
  font-size: 10px;
  color: var(--muted-2);
}

.drop-formats {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.drop-formats span {
  font-size: 8.5px;
  padding: 2px 7px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted-2);
}

.upload-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 12px;
  font-size: 9px;
  color: var(--muted-2);
  line-height: 1.55;
}

.plugin-panel {
  display: grid;
  gap: 12px;
}

.plugin-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.plugin-head strong {
  font-size: 12px;
}

.plugin-head p {
  font-size: 10px;
  color: var(--muted-2);
  margin-top: 4px;
}

.review-table th {
  padding-top: 6px;
  padding-bottom: 6px;
}

.review-table td {
  padding-top: 8px;
  padding-bottom: 8px;
}

.review-table tr.low {
  background: rgba(178, 106, 27, 0.045);
}

.raw-name {
  display: grid;
  gap: 1px;
}

.raw-name strong {
  font-size: 11px;
  font-weight: 600;
}

.raw-name span {
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--muted-2);
}

.mini-input {
  width: 100%;
  height: 29px;
  padding: 0 7px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
  font-size: 10px;
  outline: 0;
}

.mini-input:focus {
  border-color: rgba(30, 78, 216, 0.45);
  box-shadow: 0 0 0 3px rgba(30, 78, 216, 0.08);
}

.matched-name {
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 2px;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 3px;
}

.candidate-list button {
  font-size: 8px;
  color: var(--violet);
  text-align: left;
}

.candidate-list button:hover {
  text-decoration: underline;
}

.confidence {
  display: grid;
  gap: 3px;
  width: 58px;
}

.confidence span {
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--muted-2);
}

.confidence i {
  height: 3px;
  border-radius: 99px;
  background: rgba(21, 32, 43, 0.06);
  overflow: hidden;
}

.confidence i b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--green);
}

.confidence.mid i b {
  background: var(--amber);
}

.confidence.low i b {
  background: var(--rose);
}

.confidence.low span {
  color: #96332e;
}

.review-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 12px;
  padding: 9px 11px;
  border-radius: 9px;
  background: rgba(21, 32, 43, 0.025);
  color: var(--muted-2);
  font-size: 9px;
  line-height: 1.55;
}

.job-list {
  display: grid;
  gap: 2px;
}

.job-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 4px;
  border-radius: 8px;
  text-align: left;
  border-bottom: 1px solid var(--line);
}

.job-item:last-child {
  border-bottom: 0;
}

.job-item:hover {
  background: rgba(21, 32, 43, 0.025);
}

.job-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(30, 78, 216, 0.08);
  color: var(--violet);
  flex: none;
}

.job-icon.plugin {
  background: rgba(11, 143, 123, 0.1);
  color: #0f766e;
}

.job-main {
  display: grid;
  flex: 1;
  min-width: 0;
}

.job-main strong {
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-main span {
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 2px;
}

.access-list {
  display: grid;
  gap: 7px;
}

.access-item {
  display: flex;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 9px;
  background: rgba(21, 32, 43, 0.025);
}

.access-item.primary {
  background: rgba(30, 78, 216, 0.055);
  border: 1px solid rgba(30, 78, 216, 0.1);
}

.access-tag {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  color: var(--violet);
  background: rgba(255, 255, 255, 0.7);
  height: 18px;
  padding: 0 4px;
  border-radius: 4px;
  display: grid;
  place-items: center;
  flex: none;
}

.access-item strong {
  display: block;
  font-size: 10px;
}

.access-item span:last-child {
  display: block;
  font-size: 8.5px;
  color: var(--muted-2);
  margin-top: 2px;
  line-height: 1.45;
}

.access-note {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  font-size: 8.5px;
  color: var(--muted-2);
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .import-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .import-steps {
    grid-template-columns: 1fr;
  }
}
</style>
