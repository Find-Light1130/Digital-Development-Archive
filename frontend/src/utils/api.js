import axios from 'axios'
import { getToken, clearAuth } from './auth'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401 && getToken()) {
      clearAuth()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

export function registerAccount({ username, password, role, name, student_id }) {
  return api.post('/auth/register', { username, password, role, name, student_id })
}

export function loginAccount({ username, password }) {
  return api.post('/auth/login', { username, password })
}

export function logoutAccount() {
  return api.post('/auth/logout')
}

export function getMe() {
  return api.get('/auth/me')
}

export function changePassword(oldPassword, newPassword) {
  return api.post('/auth/change_password', { old_password: oldPassword, new_password: newPassword })
}

export function getUsers(status) {
  const params = {}
  if (status) params.status = status
  return api.get('/admin/users', { params })
}

export function approveUser(id) {
  return api.post(`/admin/users/${id}/approve`)
}

export function rejectUser(id) {
  return api.post(`/admin/users/${id}/reject`)
}

export function setUserClass(id, class_name) {
  return api.post(`/admin/users/${id}/class`, { class_name })
}

export function adminCreateUser({ username, password, role, name, class_name, grade }) {
  return api.post('/admin/users', { username, password, role, name, class_name, grade })
}

export function getStudentProfile(studentId) {
  return api.get('/student/profile', { params: { student_id: studentId } })
}

export function getStudentSearch(keyword) {
  return api.get('/student/search', { params: { keyword } })
}

export function getStudentScores(studentId, semester) {
  return api.get('/student/scores', { params: { student_id: studentId, semester } })
}

export function getStudentSemesters(studentId) {
  return api.get('/student/semesters', { params: { student_id: studentId } })
}

export function getStudentEmotions(studentId) {
  return api.get('/student/emotions', { params: { student_id: studentId } })
}

export function submitEmotion(studentId, date, emotionLevel, tags) {
  const params = { student_id: studentId, date, emotion_level: emotionLevel }
  if (tags && tags.length) params.tags = tags.join(',')
  return api.post('/student/emotion', null, { params })
}

export function submitStudentEvent(studentId, type, date, value) {
  return api.post('/teacher/student_event', null, { params: { student_id: studentId, type, date, value } })
}

export function getStudentSummary(studentId) {
  return api.get('/student/summary', { params: { student_id: studentId } })
}

export function getStudentRank(studentId) {
  return api.get('/student/rank', { params: { student_id: studentId } })
}

export function getStudentQuality(studentId, semester) {
  const params = { student_id: studentId }
  if (semester) params.semester = semester
  return api.get('/student/quality', { params })
}

export function getClassOverview(className, semester) {
  const params = { class_name: className }
  if (semester) params.semester = semester
  return api.get('/teacher/class/overview', { params })
}

export function getClassQuality(className, semester) {
  const params = { class_name: className }
  if (semester) params.semester = semester
  return api.get('/teacher/class/quality', { params })
}

export function getClassSemesters(className) {
  return api.get('/teacher/class/semesters', { params: { class_name: className } })
}

export function getClassDistribution(className, metric = 'growth', subject) {
  const params = { class_name: className, metric }
  if (subject) params.subject = subject
  return api.get('/teacher/class/distribution', { params })
}

export function getClassStudents(className) {
  return api.get('/teacher/class/students', { params: { class_name: className } })
}

export function getTeacherExamPlans(className) {
  return api.get('/teacher/exam_plans', { params: { class_name: className } })
}

export function gradeExamPlan(planId, className, scores) {
  return api.post(`/teacher/exam_plans/${planId}/grade`, { class_name: className, scores })
}

export function getExamPlans(status, grade) {
  const params = {}
  if (status) params.status = status
  if (grade) params.grade = grade
  return api.get('/admin/exam_plans', { params })
}

export function getExamPlanMeta() {
  return api.get('/admin/exam_plans/meta')
}

export function createExamPlan({ examType, subject, grade, examDate }) {
  return api.post('/admin/exam_plans', null, {
    params: { exam_type: examType, subject, grade, exam_date: examDate },
  })
}

export function deleteExamPlan(planId) {
  return api.delete(`/admin/exam_plans/${planId}`)
}

export function conductExam(planId) {
  return api.post(`/admin/exam_plans/${planId}/conduct`)
}

export function submitScore({ studentId, subject, examType, date, score }) {
  return api.post('/teacher/scores', null, {
    params: { student_id: studentId, subject, exam_type: examType, date, score },
  })
}

export function submitScoreBatch({ examType, date, scores }) {
  return api.post('/teacher/scores/batch', { exam_type: examType, date, scores })
}

export function deleteScore({ studentId, subject, examType, date }) {
  return api.post('/teacher/scores/delete', null, {
    params: { student_id: studentId, subject, exam_type: examType, date },
  })
}

export function submitAward({ studentId, title, level, date }) {
  return api.post('/teacher/award', null, {
    params: { student_id: studentId, title, level, date },
  })
}

export function deleteAward(awardId) {
  return api.post('/teacher/award/delete', null, { params: { award_id: awardId } })
}

export function getClassDistributionStudents(className, metric = 'growth', subject, bucket) {
  const params = { class_name: className, metric, bucket }
  if (subject) params.subject = subject
  return api.get('/teacher/class/distribution/students', { params })
}

export function getSchoolDistributionStudents(metric = 'growth', subject, grade, bucket) {
  const params = { metric, bucket }
  if (subject) params.subject = subject
  if (grade) params.grade = grade
  return api.get('/admin/distribution/students', { params })
}

export function getStudentDetails(studentId) {
  return api.get(`/teacher/student/${studentId}/details`)
}

export function getStudentAttendance(studentId) {
  return api.get('/student/attendance', { params: { student_id: studentId } })
}

export function getClassAttendance(className, semester, date) {
  const params = { class_name: className }
  if (semester) params.semester = semester
  if (date) params.date = date
  return api.get('/teacher/class/attendance', { params })
}

export function submitAttendance(className, date, students) {
  return api.post('/teacher/attendance', { class_name: className, date, students })
}

export function getClassAwards(className) {
  return api.get('/teacher/class/awards', { params: { class_name: className } })
}

export function getExamPlanStats(planId, className) {
  return api.get(`/teacher/exam_plans/${planId}/stats`, { params: { class_name: className } })
}

export function submitQuality({ studentId, subject, semester, scores }) {
  return api.post('/teacher/quality', { student_id: studentId, subject, semester, scores })
}

export function getSchoolOverview() {
  return api.get('/admin/school/overview')
}

export function getGradeComparison() {
  return api.get('/admin/grade_comparison')
}

export function getSubjectMastery() {
  return api.get('/admin/subject_mastery')
}

export function getSchoolDistribution({ metric = 'growth', subject, grade } = {}) {
  const params = { metric }
  if (subject) params.subject = subject
  if (grade) params.grade = grade
  return api.get('/admin/distribution', { params })
}

export function requestErrorText(err, notFound = '未找到对应数据', fallback = '请求失败，请检查后端是否运行') {
  const status = err?.response?.status
  if (status === 404) return notFound
  if (status === 400) return '请求参数不合法，请检查输入'
  return fallback
}

// ---------------- AI 能力 ----------------

export function getLearningReport({ scope, studentId, className, grade } = {}) {
  const params = { scope }
  if (studentId) params.student_id = studentId
  if (className) params.class_name = className
  if (grade) params.grade = grade
  return api.get('/ai/learning-report', { params })
}

export function getGrowthNarrative(studentId) {
  return api.get('/ai/growth-narrative', { params: { student_id: studentId } })
}

export function getTalent(studentId) {
  return api.get('/ai/talent', { params: { student_id: studentId } })
}

export function getEmotionRisk(studentId) {
  return api.get('/ai/emotion-risk', { params: { student_id: studentId } })
}

export function getCompanionHistory(studentId, limit = 50) {
  return api.get('/ai/companion/history', { params: { student_id: studentId, limit } })
}

export function sendCompanionMessage(studentId, message) {
  return api.post('/ai/companion/chat', { student_id: studentId, message })
}

export function getCompanionAlerts(limit = 20) {
  return api.get('/ai/companion/alerts', { params: { limit } })
}

export function getWarningBoard({ className, grade, level } = {}) {
  const params = {}
  if (className) params.class_name = className
  if (grade) params.grade = grade
  if (level) params.level = level
  return api.get('/ai/warning-board', { params })
}

export function getInterventions(studentId, status) {
  const params = {}
  if (studentId) params.student_id = studentId
  if (status) params.status = status
  return api.get('/ai/interventions', { params })
}

export function createIntervention(studentId) {
  return api.post('/ai/interventions', { student_id: studentId })
}

export function followIntervention(id, note) {
  return api.post(`/ai/interventions/${id}/follow`, { note })
}

export function closeIntervention(id) {
  return api.post(`/ai/interventions/${id}/close`)
}

export function getLearningPath(studentId) {
  return api.get('/ai/learning-path', { params: { student_id: studentId } })
}

export function generateLearningPath(studentId) {
  return api.post('/ai/learning-path/generate', { student_id: studentId })
}

export function toggleLearningItem(planId, itemKey, done) {
  return api.post(`/ai/learning-path/${planId}/toggle`, { item_key: itemKey, done })
}

export function getPaperAnalysis(planId, className) {
  return api.get('/ai/paper-analysis', { params: { plan_id: planId, class_name: className } })
}

export function getGradeHints(planId, className) {
  return api.get('/ai/grade-hints', { params: { plan_id: planId, class_name: className } })
}

export function askAI(query) {
  return api.get('/ai/ask', { params: { q: query } })
}

// ---------------------------------------------------------------- SSE 流式

/**
 * 通用 SSE 消费者：用 fetch 读取 text/event-stream 并分发事件。
 * @param {string} url 相对 /api 的路径（含 query string）
 * @param {object} handlers { onStage(payload), onToken(payload), onDone(payload), onError(payload) }
 * @returns {Promise} resolve 时携带 done payload
 */
export function consumeSSE(url, handlers = {}, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const headers = { ...extraHeaders }
    if (token) headers.Authorization = `Bearer ${token}`

    fetch(`/api${url}`, { headers, method: 'GET' })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((b) => reject(new Error(b?.detail || `HTTP ${res.status}`))).catch(() =>
            reject(new Error(`HTTP ${res.status}`)))
        }
        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buf = ''

        function pump() {
          return reader.read().then(({ done, value }) => {
            if (done) return resolve(null)
            buf += decoder.decode(value, { stream: true })
            // 按双换行切分 SSE 事件块
            const parts = buf.split('\n\n')
            buf = parts.pop()
            for (const part of parts) {
              let event = 'message'
              let data = ''
              for (const line of part.split('\n')) {
                if (line.startsWith('event:')) event = line.slice(6).trim()
                else if (line.startsWith('data:')) data += line.slice(5).trim()
              }
              let payload = null
              try { payload = data ? JSON.parse(data) : null } catch (e) { payload = null }
              if (!payload) continue
              if (event === 'stage' && handlers.onStage) handlers.onStage(payload)
              else if (event === 'token' && handlers.onToken) handlers.onToken(payload)
              else if (event === 'done') {
                if (handlers.onDone) handlers.onDone(payload)
                return resolve(payload)
              } else if (event === 'error') {
                if (handlers.onError) handlers.onError(payload)
                return reject(new Error(payload?.message || '处理出错'))
              }
            }
            return pump()
          })
        }
        pump().catch((e) => reject(e))
      })
      .catch((e) => reject(e))
  })
}

/** SSE 流式问数 */
export function askAIStream(query, handlers) {
  return consumeSSE(`/ai/ask/stream?q=${encodeURIComponent(query)}`, handlers)
}

/** SSE 流式树洞对话（POST） */
export function companionChatStream(studentId, message, handlers) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    fetch('/api/ai/companion/chat/stream', { method: 'POST', headers, body: JSON.stringify({ student_id: studentId, message }) })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((b) => reject(new Error(b?.detail || `HTTP ${res.status}`))).catch(() =>
            reject(new Error(`HTTP ${res.status}`)))
        }
        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buf = ''
        function pump() {
          return reader.read().then(({ done, value }) => {
            if (done) return resolve(null)
            buf += decoder.decode(value, { stream: true })
            const parts = buf.split('\n\n')
            buf = parts.pop()
            for (const part of parts) {
              let event = 'message'
              let data = ''
              for (const line of part.split('\n')) {
                if (line.startsWith('event:')) event = line.slice(6).trim()
                else if (line.startsWith('data:')) data += line.slice(5).trim()
              }
              let payload = null
              try { payload = data ? JSON.parse(data) : null } catch (e) { payload = null }
              if (!payload) continue
              if (event === 'stage' && handlers.onStage) handlers.onStage(payload)
              else if (event === 'token' && handlers.onToken) handlers.onToken(payload)
              else if (event === 'done') {
                if (handlers.onDone) handlers.onDone(payload)
                return resolve(payload)
              } else if (event === 'error') {
                if (handlers.onError) handlers.onError(payload)
                return reject(new Error(payload?.message || '处理出错'))
              }
            }
            return pump()
          })
        }
        pump().catch((e) => reject(e))
      })
      .catch((e) => reject(e))
  })
}
