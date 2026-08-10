<template>
  <div class="dashboard">

    <div class="glass-card search-card no-print">
      <div class="search-row">
        <svg class="search-icon" viewBox="0 0 24 24" width="18" height="18">
          <circle cx="10" cy="10" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M14.5 14.5L20 20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span class="search-label">我的成长档案</span>
        <el-input :model-value="`${profile ? profile.name : myName}（学号 ${myStudentId}）`"
                  class="glass-input student-search" style="flex:1; min-width:200px" disabled />
        <el-button class="btn-secondary" :loading="loading" @click="loadData">刷新</el-button>
        <el-button v-if="profile" class="btn-secondary no-print" @click="printReport">打印成绩单</el-button>
      </div>
    </div>

    <PageSkeleton v-if="loading && !profile" :kpis="4" :charts="4" />

    <transition name="rise" appear>
    <template v-if="profile">
      <div class="profile-wrap" :class="{ 'is-refreshing': loading }">
      <div class="kpi-grid">
        <div class="glass-card kpi-card" v-reveal="{ delay: 0 }"><div class="kpi-label">综合成长指数<GrowthIndexTip /></div><div class="kpi-value"><CountUp :value="profile.growth_index" :decimals="1" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 60 }"><div class="kpi-label">姓名</div><div class="kpi-name">{{ profile.name }}</div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 120 }"><div class="kpi-label">年级</div><div class="kpi-name">{{ profile.grade }}</div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 180 }"><div class="kpi-label">班级</div><div class="kpi-name">{{ profile.class }}</div></div>
      </div>

      <div v-if="profile.warnings?.length" class="glass-card warning-card">
        <div class="warning-icon">
          <svg viewBox="0 0 24 24" width="18" height="18">
            <path d="M12 2L2 22h20L12 2z" fill="none" stroke="#e6a23c" stroke-width="1.5"/>
            <circle cx="12" cy="16" r="0.8" fill="#e6a23c"/>
            <rect x="11.2" y="9" width="1.6" height="5" rx="0.5" fill="#e6a23c"/>
          </svg>
        </div>
        <span>{{ profile.warnings.join('; ') }}</span>
      </div>

      <AiReport scope="student" :student-id="myStudentId" />


      <div class="full-grid">
        <div class="glass-card chart-card" v-reveal="{ delay: 120 }">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 3v18h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="15" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="10" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="13" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <path d="M7 15L12 10L17 13" stroke="var(--accent)" stroke-width="1" fill="none"/>
            </svg>
            成绩趋势
            <span style="flex:1"></span>
            <el-select v-model="currentSemester" placeholder="选择学期" size="small" class="glass-select" style="width:180px"
                       @change="onSemesterChange">
              <el-option-group v-for="g in semesterGroupOptions" :key="g.label" :label="g.label">
                <el-option v-for="s in g.options" :key="s" :label="s" :value="s" />
              </el-option-group>
            </el-select>
          </div>
          <ScoreChart :scores="scores" :default-subject="weakestSubject" @exam-click="showExamReview" />
        </div>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 12h4l2-3 3 4 3-5 2 3 4-1" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="17" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
            </svg>
            音体美信素质评估
        </div>
        <QualityChart :subjects="quality" />
      </div>

      <div class="half-grid">
        <div class="glass-card chart-card" v-reveal="{ delay: 60 }">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 12h4l2-3 3 4 3-5 2 3 4-1" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="17" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
            </svg>
            成长画像
          </div>
          <RadarChart :data="profile.aspects" />
        </div>
        <div class="glass-card chart-card">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M12 2C8 2 4 5 4 10c0 5 8 12 8 12s8-7 8-12c0-5-4-8-8-8z" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
              <circle cx="12" cy="10" r="2" fill="var(--accent)" opacity="0.6"/>
            </svg>
             情绪曲线
              <span class="card-hint" v-if="emotionStreak > 1">连续记录 <b>{{ emotionStreak }}</b> 天</span>
          </div>
          <div class="mood-bar">
            <span class="mood-label">今日心情</span>
            <el-date-picker v-model="moodDate" type="date" size="small" class="glass-select"
                            style="width:150px" :disabled-date="disableFuture" value-format="YYYY-MM-DD"
                            placeholder="选择日期" />
            <div class="mood-options">
              <button v-for="m in moodOptions" :key="m.value" type="button"
                      :class="['mood-btn', { active: moodLevel === m.value }]"
                      :style="moodLevel === m.value ? { borderColor: m.color, color: m.color, background: m.bg } : {}"
                      @click="moodLevel = m.value">
                {{ m.label }}
              </button>
            </div>
            <el-select v-model="moodTags" multiple size="small" class="glass-select" style="width:190px"
                       placeholder="心情标签（最多3个）" :multiple-limit="3" collapse-tags clearable>
              <el-option v-for="t in moodTagOptions" :key="t" :label="t" :value="t" />
            </el-select>
            <el-button size="small" class="btn-primary mood-submit" :loading="moodSaving" @click="submitMood">记录</el-button>
          </div>
          <EmotionChart :emotions="emotions" />
        </div>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <rect x="3" y="5" width="18" height="16" rx="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M8 3v4M16 3v4M3 10h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M8 15h2M14 15h2M12 15v2" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
          </svg>
          情绪日历
          <span class="card-hint">点击任意一天记录 / 修改心情</span>
        </div>
        <div class="cal-layout">
          <div class="cal-main">
            <MoodCalendar :emotions="emotions" @select="onCalSelect" />
          </div>
          <div class="cal-side">
            <div class="cal-side-label">所选日期</div>
            <div class="cal-date">{{ calSelected || '—' }}</div>
            <div class="mood-options">
              <button v-for="m in moodOptions" :key="m.value" type="button"
                      :class="['mood-btn', { active: calLevel === m.value }]"
                      :style="calLevel === m.value ? { borderColor: m.color, color: m.color, background: m.bg } : {}"
                      @click="calLevel = m.value">
                {{ m.label }}
              </button>
            </div>
            <el-select v-model="calTags" multiple size="small" class="glass-select" style="width:100%;margin-top:10px"
                       placeholder="心情标签（最多3个）" :multiple-limit="3" collapse-tags clearable>
              <el-option v-for="t in moodTagOptions" :key="t" :label="t" :value="t" />
            </el-select>
            <el-button size="small" class="btn-primary" style="margin-top:12px;width:100%"
                       :loading="calSaving" @click="saveCalMood">记录该日心情</el-button>
          </div>
        </div>
      </div>

      <CompanionChat :student-id="myStudentId" />

      <GrowthNarrative :student-id="myStudentId" />
      <TalentDiscovery :student-id="myStudentId" />

      <div class="glass-card chart-card" v-reveal="{ delay: 60 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M3 17l5-5 4 4 8-8" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M15 8h5v5" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          本班位次
          <span class="card-hint">{{ rank.class_name }}</span>
        </div>
        <div v-if="rank.semesters.length || rank.growth_rank" class="rank-wrap">
          <div class="rank-growth" v-if="rank.growth_rank">
            <span class="rank-growth-label">成长指数</span>
            <span class="rank-growth-value">第 {{ rank.growth_rank.rank }} / {{ rank.growth_rank.total_students }} 名</span>
            <span class="rank-growth-sub">{{ rank.growth_rank.growth_index }} 分 · 超过 {{ 100 - rank.growth_rank.percentile }}% 同学</span>
          </div>
          <table v-if="rank.semesters.length" class="rank-table">
            <thead><tr><th>学期</th><th>总分</th><th>名次</th><th>进步</th></tr></thead>
            <tbody>
              <tr v-for="(s, i) in rank.semesters" :key="s.semester">
                <td>{{ s.semester }}</td>
                <td>{{ s.total_score }}</td>
                <td>{{ s.rank }} / {{ s.total_students }}</td>
                <td>
                  <span v-if="i > 0" :class="deltaClass(rank.semesters[i-1].rank - s.rank)">
                    {{ rank.semesters[i-1].rank - s.rank > 0 ? '↑' : rank.semesters[i-1].rank - s.rank < 0 ? '↓' : '—' }} {{ Math.abs(rank.semesters[i-1].rank - s.rank) }}
                  </span>
                  <span v-else class="delta-0">—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!rank.semesters.length && rank.growth_rank" class="no-data">暂无成绩排名</div>
        </div>
        <div v-else class="no-data">暂无位次数据</div>
      </div>

      <div class="glass-card chart-card" v-reveal="{ delay: 60 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <circle cx="12" cy="8" r="4" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
          </svg>
          出勤情况
          <span class="card-hint">累计出勤率 {{ attendance.rate }}% · 缺勤 {{ attendance.absent }} 天</span>
        </div>
        <div class="attendance-grid">
          <div v-for="m in attendance.monthly" :key="m.month" class="attendance-month">
            <div class="attendance-month-title">{{ m.month }}</div>
            <div class="attendance-rate" :class="{ warn: m.rate < 90 }">{{ m.rate }}%</div>
            <div class="attendance-detail">出勤 {{ m.present }} / {{ m.total }}</div>
          </div>
          <div v-if="!attendance.monthly.length" class="no-data">暂无考勤记录</div>
        </div>
        <div v-if="attendance.absences.length" class="attendance-absences">
          最近缺勤：<span v-for="d in attendance.absences" :key="d" class="absence-chip">{{ d }}</span>
        </div>
      </div>

      <div class="glass-card chart-card" v-reveal="{ delay: 60 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M21 13a9 9 0 1 1-9-9" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 8v4l3 2" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          成长足迹
          <span class="card-hint">期中/期末 · 获奖 · 活动 · 素质</span>
        </div>
        <Timeline :scores="allScores" :emotions="emotions" :activities="summary.activities" :awards="summary.awards" :quality="quality" />
      </div>

      <div class="glass-card chart-card" v-reveal="{ delay: 60 }">
        <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="9" cy="10" r="0.5" fill="var(--accent)"/>
              <circle cx="12" cy="10" r="0.5" fill="var(--accent)"/>
              <circle cx="15" cy="10" r="0.5" fill="var(--accent)"/>
            </svg>
            AI 学习路径
        </div>
        <LearningPath :student-id="myStudentId" />

      </div>
      </div>
    </template>
    </transition>

    <FailCard v-if="!loading && !profile && error" :message="error" @retry="loadData" />

    <EmptyState v-if="!loading && !profile && !error" type="search" title="正在加载我的成长档案" hint="请稍候…" />

    <ExamReview v-model="reviewVisible" :exam="selectedExam" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudentProfile, getStudentScores, getStudentEmotions, getStudentSemesters, getStudentSummary, getStudentQuality, submitEmotion, getStudentAttendance, getStudentRank, requestErrorText } from '../utils/api'
import { getStoredUser } from '../utils/auth'
import { semesterGroups } from '../utils/semesters'
import RadarChart from '../components/RadarChart.vue'
import ScoreChart from '../components/ScoreChart.vue'
import EmotionChart from '../components/EmotionChart.vue'
import ExamReview from '../components/ExamReview.vue'
import AiReport from '../components/AiReport.vue'
import LearningPath from '../components/LearningPath.vue'
import CompanionChat from '../components/CompanionChat.vue'
import GrowthNarrative from '../components/GrowthNarrative.vue'
import TalentDiscovery from '../components/TalentDiscovery.vue'
import QualityChart from '../components/QualityChart.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CountUp from '../components/CountUp.vue'
import FailCard from '../components/FailCard.vue'
import EmptyState from '../components/EmptyState.vue'
import GrowthIndexTip from '../components/GrowthIndexTip.vue'
import Timeline from '../components/Timeline.vue'
import MoodCalendar from '../components/MoodCalendar.vue'

const myStudentId = ref(0)
const myName = ref('')
const profile = ref(null)
const scores = ref([])
const allScores = ref([])
const emotions = ref([])
const semesters = ref([])
const summary = ref({ semesterStats: [], awards: [], activities: [] })
const quality = ref([])
const attendance = ref({ total: 0, absent: 0, rate: 0, monthly: [], absences: [] })
const rank = ref({ class_name: '', semesters: [], growth_rank: null })
const currentSemester = ref('')
const reviewVisible = ref(false)
const selectedExam = ref(null)
const loading = ref(false)
const error = ref('')
const moodLevel = ref(2)
const moodSaving = ref(false)
const moodDate = ref(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10))
const moodTags = ref([])
const moodTagOptions = ['开心', '平静', '焦虑', '疲惫', '生气', '悲伤']
const moodOptions = [
  { value: 1, label: '低落', color: 'var(--danger)', bg: 'rgba(248,113,113,0.12)' },
  { value: 2, label: '平静', color: 'var(--text-secondary)', bg: 'rgba(128,128,128,0.12)' },
  { value: 3, label: '开心', color: 'var(--accent)', bg: 'rgba(52,211,153,0.12)' },
]

const todayStr = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const calSelected = ref(todayStr)
const calLevel = ref(2)
const calTags = ref([])
const calSaving = ref(false)
let requestSeq = 0

const emotionStreak = computed(() => {
  if (!emotions.value.length) return 0
  const dates = new Set(emotions.value.map((e) => e.date))
  const sorted = [...dates].sort()
  let cur = sorted[sorted.length - 1]
  let count = 0
  while (dates.has(cur)) {
    count++
    const d = new Date(cur + 'T00:00:00')
    d.setDate(d.getDate() - 1)
    cur = d.toISOString().slice(0, 10)
  }
  return count
})

function onCalSelect(date, log) {
  calSelected.value = date
  calLevel.value = log ? log.emotion_level : 2
  calTags.value = log?.tags?.length ? [...log.tags] : []
}

async function saveCalMood() {
  if (!calSelected.value) { ElMessage.warning('请先点击日历中的某一天'); return }
  calSaving.value = true
  try {
    await submitEmotion(myStudentId.value, calSelected.value, calLevel.value, calTags.value)
    ElMessage.success(`${calSelected.value} 的心情已记录`)
    const res = await getStudentEmotions(myStudentId.value)
    emotions.value = res.data
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '记录失败，请稍后再试')
  } finally {
    calSaving.value = false
  }
}

const weakestSubject = computed(() => {
  if (!profile.value?.weakness?.length) return ''
  const subj = profile.value.weakness[0].split('-')[0]
  return subj || ''
})

const semesterGroupOptions = computed(() => semesterGroups(semesters.value))

async function fetchStudent(id) {
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  currentSemester.value = ''
  profile.value = null
  scores.value = []
  allScores.value = []
  emotions.value = []
  semesters.value = []
  summary.value = { semesterStats: [], awards: [], activities: [] }
  quality.value = []
  attendance.value = { total: 0, absent: 0, rate: 0, monthly: [], absences: [] }
  rank.value = { class_name: '', semesters: [], growth_rank: null }
  try {
    const [pRes, eRes, semRes, sumRes, qRes] = await Promise.all([
      getStudentProfile(id), getStudentEmotions(id), getStudentSemesters(id), getStudentSummary(id), getStudentQuality(id),
    ])
    if (seq !== requestSeq) return
    profile.value = pRes.data
    emotions.value = eRes.data
    semesters.value = semRes.data
    summary.value = {
      semesterStats: sumRes.data?.semester_stats || [],
      awards: sumRes.data?.awards || [],
      activities: sumRes.data?.activities || [],
    }
    quality.value = qRes.data
    const [sRes, aRes, attRes, rankRes] = await Promise.all([
      getStudentScores(id, semRes.data.length ? semRes.data[semRes.data.length - 1] : undefined),
      getStudentScores(id),
      getStudentAttendance(id),
      getStudentRank(id),
    ])
    if (seq !== requestSeq) return
    scores.value = sRes.data
    allScores.value = aRes.data
    attendance.value = attRes.data || { total: 0, absent: 0, rate: 0, monthly: [], absences: [] }
    rank.value = rankRes.data || { class_name: '', semesters: [], growth_rank: null }
    if (semRes.data.length) {
      currentSemester.value = semRes.data[semRes.data.length - 1]
    }
  } catch (e) {
    if (seq !== requestSeq) return
    profile.value = null
    error.value = requestErrorText(e, '未找到该学生，请确认 ID 在 1-1050 之间')
    ElMessage.error(error.value)
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

async function loadData() {
  if (!myStudentId.value) return
  await fetchStudent(myStudentId.value)
}

function onSelectSuggestion(item) {
  if (!item) return
  fetchStudent(Number(item.student_id || myStudentId.value))
}

function deltaClass(delta) {
  return delta > 0 ? 'delta-up' : delta < 0 ? 'delta-down' : 'delta-0'
}

async function onSemesterChange() {
  if (!currentSemester.value) return
  const id = myStudentId.value
  if (!id) return
  const seq = ++requestSeq
  loading.value = true
  try {
    const [sRes] = await Promise.all([getStudentScores(id, currentSemester.value)])
    if (seq !== requestSeq) return
    scores.value = sRes.data
  } catch {
    if (seq === requestSeq) ElMessage.error('成绩加载失败')
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

function showExamReview(exam) {
  selectedExam.value = exam
  reviewVisible.value = true
}

function printReport() {
  window.print()
}

function disableFuture(date) {
  return date.getTime() > Date.now()
}

async function submitMood() {
  const id = myStudentId.value
  if (!id) { ElMessage.warning('未绑定学生证号'); return }
  if (!moodDate.value) { ElMessage.warning('请选择日期'); return }
  moodSaving.value = true
  try {
    await submitEmotion(id, moodDate.value, moodLevel.value, moodTags.value)
    ElMessage.success('今日心情已记录')
    const res = await getStudentEmotions(id)
    emotions.value = res.data
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '记录失败，请稍后再试')
  } finally {
    moodSaving.value = false
  }
}

onMounted(() => {
  const u = getStoredUser()
  myStudentId.value = Number(u?.student_id) || 0
  myName.value = u?.name || u?.username || ''
  if (myStudentId.value) loadData()
  else error.value = '未绑定学生证号，请联系管理员'
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.profile-wrap { display: flex; flex-direction: column; gap: 16px; transition: opacity 0.3s ease; }
.profile-wrap.is-refreshing { opacity: 0.6; }
.search-card { padding: 16px 20px; }
.search-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.search-icon { color: var(--accent); flex-shrink: 0; }
.search-label { font-weight: 600; color: var(--accent); font-size: 15px; white-space: nowrap; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 14px; }
.kpi-card { padding: 20px; text-align: center; }
.kpi-name { font-size: 22px; font-weight: 700; color: var(--accent); }
.warning-card { padding: 14px 20px; border-left: 4px solid var(--warning) !important; display: flex; align-items: center; gap: 10px; }
.warning-icon { flex-shrink: 0; display: flex; }
.half-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.full-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-hint { margin-left: 8px; font-size: 10px; font-weight: 400; color: var(--text-label); background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; padding: 1px 8px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; }
.mood-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 12px; margin: 2px 0 6px; border-radius: 12px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
}
.mood-label { font-size: 13px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
.mood-options { display: flex; gap: 8px; }
.mood-btn {
  padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; cursor: pointer;
  color: var(--text-muted); background: transparent; border: 1px solid var(--glass-border);
  font-family: inherit; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.mood-btn:hover { color: var(--text-primary); border-color: rgba(var(--accent-rgb), 0.4); }
.mood-submit { margin-left: auto; }
.cal-layout { display: flex; gap: 18px; align-items: flex-start; padding: 8px 2px 2px; }
.cal-main { flex: 1; min-width: 0; }
.cal-side {
  width: 250px; flex-shrink: 0; padding: 14px; border-radius: 12px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
}
.cal-side-label { font-size: 12px; color: var(--text-label); }
.cal-date { font-size: 18px; font-weight: 700; color: var(--accent); margin: 4px 0 12px; }
.cal-side .mood-options { margin-top: 6px; }
.attendance-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px;
  padding: 8px 2px 4px;
}
.attendance-month {
  padding: 10px 12px; border-radius: 12px; text-align: center;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
}
.attendance-month-title { font-size: 11px; color: var(--text-label); }
.attendance-rate { font-size: 20px; font-weight: 700; color: var(--accent); margin: 2px 0; }
.attendance-rate.warn { color: var(--danger); }
.attendance-detail { font-size: 11px; color: var(--text-secondary); }
.attendance-absences { margin-top: 6px; font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.absence-chip {
  font-size: 11px; padding: 1px 8px; border-radius: 8px; color: var(--danger);
  background: rgba(248,113,113,0.12); border: 1px solid rgba(248,113,113,0.3);
}
.rank-wrap { padding: 6px 2px; }
.rank-growth {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; border-radius: 12px; margin-bottom: 10px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
}
.rank-growth-label { font-size: 12px; color: var(--text-label); }
.rank-growth-value { font-size: 18px; font-weight: 700; color: var(--accent); }
.rank-growth-sub { font-size: 12px; color: var(--text-secondary); }
.rank-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rank-table th, .rank-table td { padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--glass-border); }
.rank-table th { color: var(--text-label); font-weight: 600; font-size: 11px; }
.rank-table td { color: var(--text-secondary); }
.rank-table tr:last-child td { border-bottom: none; }
.delta-up { color: var(--success); font-weight: 600; }
.delta-down { color: var(--danger); font-weight: 600; }
.delta-0 { color: var(--text-muted); }
@media (max-width: 992px) { .cal-layout { flex-direction: column; } .cal-side { width: 100%; } }
@media (max-width: 768px) {
  .mood-submit { margin-left: 0; }
}
@media (max-width: 1200px) { .kpi-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 768px) { .half-grid { grid-template-columns: 1fr; } .kpi-grid { grid-template-columns: 1fr 1fr; } }
</style>

