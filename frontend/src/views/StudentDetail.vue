<template>
  <div class="dashboard" :class="{ 'is-refreshing': loading }">
    <el-button class="btn-secondary back-btn no-print" @click="goBack">
      <svg viewBox="0 0 24 24" width="14" height="14" style="margin-right:4px">
        <path d="M19 12H5M12 19l-7-7 7-7" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      返回班级面板
    </el-button>
    <el-button v-if="profile" class="btn-secondary back-btn no-print" @click="printReport" style="margin-left:8px">打印成绩单</el-button>

    <PageSkeleton v-if="loading && !profile" :kpis="4" :charts="4" />

    <FailCard v-if="!loading && !profile && error" :message="error" @retry="load" />

    <transition name="rise" appear>
    <div v-if="profile" class="profile-wrap">
      <div class="kpi-grid">
        <div class="glass-card kpi-card" v-reveal="{ delay: 0 }"><div class="kpi-label">成长指数<GrowthIndexTip /></div><div class="kpi-value"><CountUp :value="profile.growth_index" :decimals="1" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 60 }"><div class="kpi-label">姓名</div><div class="kpi-name">{{ profile.name }}</div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 120 }"><div class="kpi-label">年级</div><div class="kpi-name">{{ profile.grade }}</div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 180 }"><div class="kpi-label">班级</div><div class="kpi-name">{{ profile.class }}</div></div>
      </div>

      <div v-if="profile.warnings?.length" class="glass-card warning-card">
        <svg viewBox="0 0 24 24" width="18" height="18" style="flex-shrink:0">
          <path d="M12 2L2 22h20L12 2z" fill="none" stroke="#e6a23c" stroke-width="1.5"/>
          <circle cx="12" cy="16" r="0.8" fill="#e6a23c"/>
          <rect x="11.2" y="9" width="1.6" height="5" rx="0.5" fill="#e6a23c"/>
        </svg>
        <span>{{ profile.warnings.join('; ') }}</span>
      </div>

      <AiReport scope="student" :student-id="detailStudentId" />

      <div class="half-grid">
        <GrowthNarrative :student-id="detailStudentId" />
        <TalentDiscovery :student-id="detailStudentId" />
      </div>

      <CompanionChat :student-id="detailStudentId" read-only />

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
          </div>
          <EmotionChart :emotions="emotions" />
        </div>
      </div>

      <ComprehensiveCard :semester-stats="summary.semesterStats" :awards="summary.awards" :activities="summary.activities" />

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
           个性化建议
        </div>
        <TypedSuggestions :suggestions="profile.suggestions || []" />
      </div>
    </div>
    </transition>

    <ExamReview v-model="reviewVisible" :exam="selectedExam" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getStudentDetails, getStudentScores, getStudentEmotions, getStudentSemesters, getStudentSummary, getStudentQuality, requestErrorText } from '../utils/api'
import { semesterGroups } from '../utils/semesters'
import RadarChart from '../components/RadarChart.vue'
import ScoreChart from '../components/ScoreChart.vue'
import EmotionChart from '../components/EmotionChart.vue'
import ExamReview from '../components/ExamReview.vue'
import ComprehensiveCard from '../components/ComprehensiveCard.vue'
import TypedSuggestions from '../components/TypedSuggestions.vue'
import AiReport from '../components/AiReport.vue'
import GrowthNarrative from '../components/GrowthNarrative.vue'
import TalentDiscovery from '../components/TalentDiscovery.vue'
import CompanionChat from '../components/CompanionChat.vue'
import QualityChart from '../components/QualityChart.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CountUp from '../components/CountUp.vue'
import FailCard from '../components/FailCard.vue'
import GrowthIndexTip from '../components/GrowthIndexTip.vue'
import Timeline from '../components/Timeline.vue'

const route = useRoute()
const router = useRouter()
const profile = ref(null)
const scores = ref([])
const allScores = ref([])
const emotions = ref([])
const semesters = ref([])
const summary = ref({ semesterStats: [], awards: [], activities: [] })
const quality = ref([])
const currentSemester = ref('')
const reviewVisible = ref(false)
const selectedExam = ref(null)
const loading = ref(false)
const error = ref('')
let requestSeq = 0
const weakestSubject = computed(() => {
  if (!profile.value?.weakness?.length) return ''
  return profile.value.weakness[0].split('-')[0] || ''
})
const detailStudentId = computed(() => Number(route.params.id) || 0)

const semesterGroupOptions = computed(() => semesterGroups(semesters.value))

async function load() {
  const id = Number(route.params.id)
  if (!id) return
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  try {
    const [pRes, semRes, eRes, sumRes, qRes] = await Promise.all([
      getStudentDetails(id), getStudentSemesters(id), getStudentEmotions(id), getStudentSummary(id), getStudentQuality(id),
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
    const [sRes, aRes] = await Promise.all([
      getStudentScores(id, semRes.data.length ? semRes.data[semRes.data.length - 1] : undefined),
      getStudentScores(id),
    ])
    if (seq !== requestSeq) return
    scores.value = sRes.data
    allScores.value = aRes.data
    if (semRes.data.length) {
      currentSemester.value = semRes.data[semRes.data.length - 1]
    }
  } catch (e) {
    if (seq === requestSeq) {
      error.value = requestErrorText(e, '未找到该学生')
      ElMessage.error(error.value)
    }
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

onMounted(load)

async function onSemesterChange() {
  if (!currentSemester.value) return
  const id = Number(route.params.id)
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

function goBack() {
  const cls = route.query.class || sessionStorage.getItem('teacherClass')
  if (cls) sessionStorage.setItem('teacherClass', cls)
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push({ path: '/teacher', query: cls ? { class: cls } : {} })
  }
}

function printReport() {
  window.print()
}
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; transition: opacity 0.3s ease; }
.dashboard.is-refreshing { opacity: 0.6; }
.back-btn { align-self: flex-start; margin-bottom: 4px; display: flex; align-items: center; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 14px; }
.kpi-card { padding: 20px; text-align: center; }
.kpi-name { font-size: 22px; font-weight: 700; color: var(--accent); }
.warning-card { padding: 14px 20px; border-left: 4px solid var(--warning) !important; display: flex; align-items: center; gap: 10px; }
.half-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.full-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-hint { margin-left: 8px; font-size: 10px; font-weight: 400; color: var(--text-label); background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; padding: 1px 8px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; }
@media (max-width: 768px) { .half-grid { grid-template-columns: 1fr; } }
</style>
