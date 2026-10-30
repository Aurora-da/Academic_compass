const BASE = '/api/v1'

function token() {
  return localStorage.getItem('ac_token') || ''
}

export function getErrorMessage(error) {
  if (!error) return '未知错误'
  if (typeof error === 'string') return error
  if (typeof error.detail === 'string') return error.detail
  if (Array.isArray(error.detail)) {
    return error.detail.map((d) => d.msg || JSON.stringify(d)).join('；')
  }
  if (error.detail && typeof error.detail === 'object') {
    return error.detail.message || JSON.stringify(error.detail)
  }
  return error.message || '请求失败'
}

async function request(path, { method = 'GET', body, headers = {}, raw = false } = {}) {
  const options = { method, headers: { ...headers } }
  if (token()) options.headers.Authorization = `Bearer ${token()}`
  if (body !== undefined && !(body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  } else if (body instanceof FormData) {
    options.body = body
  }
  const res = await fetch(BASE + path, options)
  if (res.status === 401) {
    localStorage.removeItem('ac_token')
    localStorage.removeItem('ac_user')
  }
  let data = null
  const text = await res.text()
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const err = new Error(getErrorMessage(data))
    err.status = res.status
    err.payload = data
    throw err
  }
  return raw ? res : data
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  me: () => request('/auth/me'),
  demoAccounts: () => request('/auth/demo-accounts'),
  meta: () => request('/meta'),

  plans: () => request('/plans'),
  plan: (planId, q) => request(`/plans/${planId}${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  planByMajor: (major, grade) => request(`/plans/${encodeURIComponent(major)}/${grade}`),
  validation: (planId) => request(`/plans/${planId}/validation`),

  student: () => request('/students/me'),
  audit: (semester, save = false) =>
    request(`/students/me/audit?${semester ? `semester=${semester}&` : ''}save=${save}`),
  recommend: (semester, maxCredits = 28) =>
    request(
      `/students/me/recommend?${semester ? `semester=${semester}&` : ''}max_credits=${maxCredits}`,
    ),
  report: (semester) => request(`/students/me/report${semester ? `?semester=${semester}` : ''}`),
  snapshots: () => request('/students/me/snapshots'),
  diff: () => request('/students/me/diff'),
  secondClassroom: () => request('/students/me/second-classroom'),
  addSecondClassroom: (payload) => request('/students/me/second-classroom', { method: 'POST', body: payload }),
  simulate: (courseCode, semester) =>
    request('/students/me/simulate', { method: 'POST', body: { course_code: courseCode, semester } }),
  lockDirection: (directionId) =>
    request('/students/me/direction', { method: 'POST', body: { direction_id: directionId } }),
  enrollments: () => request('/students/me/enrollments'),

  documents: () => request('/documents'),
  document: (jobId) => request(`/documents/${jobId}`),
  upload: (file, source = 'file') => {
    const form = new FormData()
    form.append('file', file)
    form.append('source', source)
    return request('/documents', { method: 'POST', body: form })
  },
  reviewDocument: (jobId, items, apply = true) =>
    request(`/documents/${jobId}/review`, { method: 'POST', body: { items, apply } }),
  pluginImport: (courses, apply = false) =>
    request('/documents/plugin', { method: 'POST', body: { source: 'plugin', courses, apply } }),

  adminDashboard: () => request('/admin/dashboard'),
  adminMappings: (status = 'pending') => request(`/admin/mappings?status=${status}`),
  confirmMapping: (id, courseCode, createAlias = true) =>
    request(`/admin/mappings/${id}/confirm`, { method: 'POST', body: { course_code: courseCode, create_alias: createAlias } }),
  adminSecondClassroom: (status = 'pending') => request(`/admin/second-classroom?status=${status}`),
  reviewSecondClassroom: (id, status, comment = '') =>
    request(`/admin/second-classroom/${id}/review`, { method: 'POST', body: { status, comment } }),
  adminPlans: () => request('/admin/plans'),
  adminTrial: (planId, studentNos = []) =>
    request(`/admin/plans/${planId}/trial`, { method: 'POST', body: { student_nos: studentNos } }),
  adminPublish: (planId) => request(`/admin/plans/${planId}/publish`, { method: 'POST' }),
  adminOfferings: (semester) => request(`/admin/offerings${semester ? `?semester=${semester}` : ''}`),
}

export async function streamChat({ message, sessionId, semester, signal, onEvent }) {
  const res = await fetch(BASE + '/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId, semester }),
    signal,
  })
  if (!res.ok) {
    const text = await res.text()
    let payload = text
    try {
      payload = JSON.parse(text)
    } catch {}
    throw new Error(getErrorMessage(payload))
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const line = block
        .split('\n')
        .find((l) => l.startsWith('data:'))
      if (!line) continue
      const data = line.slice(5).trim()
      if (data === '[DONE]') return
      try {
        onEvent(JSON.parse(data))
      } catch {
        // 忽略不完整分片
      }
    }
  }
}
