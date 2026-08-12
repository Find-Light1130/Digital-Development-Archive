<template>
  <div class="dashboard" :class="{ 'is-refreshing': loading && overview }">
    <div class="admin-toolbar no-print">
      <span class="admin-title">本年级工作台<span v-if="myGrade" class="grade-chip">{{ myGrade }}</span></span>
      <div class="toolbar-actions">
        <el-select v-model="jumpClass" placeholder="选择班级" size="default" class="glass-select" style="width:150px">
          <el-option v-for="c in myClasses" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button class="btn-primary" :disabled="!jumpClass" @click="enterClass">进入班级面板</el-button>
        <el-button class="btn-secondary" :loading="loading" @click="load">刷新</el-button>
        <el-button class="btn-primary" @click="router.push('/grade-leader/review')">教师审核</el-button>
      </div>
    </div>

    <transition name="rise" appear>
    <div v-if="overview" class="content-wrap">
      <div class="kpi-grid">
        <div class="glass-card kpi-card" v-reveal="{ delay: 0 }"><div class="kpi-label">本年级学生数</div><div class="kpi-value"><CountUp :value="overview.total_students" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 60 }"><div class="kpi-label">年级平均成长指数<GrowthIndexTip /></div><div class="kpi-value"><CountUp :value="overview.avg_growth_index" :decimals="2" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 120 }"><div class="kpi-label">班级数</div><div class="kpi-value"><CountUp :value="classData.length" /></div></div>
      </div>

      <div class="half-grid">
        <div class="glass-card chart-card">
          <div class="card-header">本年级各班平均成长指数</div>
          <v-chart :option="classOption" style="height:300px" autoresize />
        </div>
        <div class="glass-card chart-card">
          <div class="card-header">各科平均掌握率<span class="card-hint">文化课</span></div>
          <v-chart :option="masteryOption" style="height:300px" autoresize />
        </div>
      </div>

      <div class="half-grid">
        <WarningBoard :grade="myGrade" />
        <AiAsk />
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          本年级数据分布
          <span style="flex:1"></span>
          <div class="metric-pills">
            <button :class="['pill', { active: distMetric === 'growth' }]" @click="switchMetric('growth')">成长指数</button>
            <button :class="['pill', { active: distMetric === 'score' }]" @click="switchMetric('score')">各科平均分</button>
          </div>
          <el-select v-if="distMetric === 'score'" v-model="distSubject" placeholder="科目" size="small" class="glass-select" style="width:120px;margin-left:8px" @change="loadDist">
            <el-option v-for="s in masterySubjects" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
        <DistributionChart :buckets="distribution.buckets" :counts="distribution.counts" :color="distColor" />
        <div v-if="distribution.total" class="dist-total">共 {{ distribution.total }} 名</div>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          本年级考试
          <span class="card-hint">规划中考试到日可进行 · 进行后教师批阅自动录入</span>
          <span style="flex:1"></span>
          <el-button size="small" class="btn-secondary" :loading="examLoading" @click="loadExamPlans">刷新</el-button>
        </div>
        <div class="table-scroll" style="padding:8px 0 0">
          <table class="user-grid">
            <thead>
              <tr>
                <th>考试</th>
                <th>科目</th>
                <th>考试日期</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in examPlans" :key="p.id">
                <td>{{ p.exam_type }}</td>
                <td>{{ p.subject }}</td>
                <td class="user-cell-dim">{{ p.exam_date }}</td>
                <td>
                  <span class="status-badge" :class="`exam-${p.status}`">{{ examStatusText(p.status) }}</span>
                  <span v-if="p.status === 'planned' && examReady(p)" class="status-badge exam-planned"
                        style="margin-left:6px;color:#34d399;background:rgba(52, 211, 153, 0.15);border-color:transparent">可进行</span>
                </td>
                <td>
                  <el-button v-if="p.status === 'planned'" size="small" class="btn-primary"
                             style="padding:3px 12px;font-size:12px"
                             :disabled="!examReady(p)"
                             :title="examReady(p) ? '' : '未到考试日期，暂不能进行'"
                             @click="conduct(p)">进行考试</el-button>
                  <span v-else class="user-cell-dim">—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!examPlans.length" class="no-data">暂无考试规划</div>
        </div>
      </div>

      </div>
    </transition>

    <PageSkeleton v-if="!overview && !error" :kpis="3" :charts="2" :table="true" />

    <FailCard v-if="error" :message="error" @retry="load" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { getSchoolOverview, getGradeComparison, getSubjectMastery, getSchoolDistribution, getExamPlans, conductExam, requestErrorText } from '../utils/api'
import { getStoredUser } from '../utils/auth'
import { themeKey, themeTooltip, themePalette, subjectColor } from '../utils/colors'
import { ElMessage } from 'element-plus'
import PageSkeleton from '../components/PageSkeleton.vue'
import CountUp from '../components/CountUp.vue'
import FailCard from '../components/FailCard.vue'
import DistributionChart from '../components/DistributionChart.vue'
import GrowthIndexTip from '../components/GrowthIndexTip.vue'
import WarningBoard from '../components/WarningBoard.vue'
import AiAsk from '../components/AiAsk.vue'

const router = useRouter()
const myGrade = ref('')
const myClasses = ref([])
const jumpClass = ref('')
const overview = ref(null)
const classData = ref([])
const mastery = ref({ grades: [], subjects: [], rows: [] })
const distribution = ref({ buckets: [], counts: [], total: 0 })
const distMetric = ref('growth')
const distSubject = ref('')
const error = ref('')
const loading = ref(false)
const examPlans = ref([])
const examLoading = ref(false)

const EXAM_STATUS_TEXT = { planned: '待进行', conducted: '已进行', graded: '已批阅' }
const examStatusText = (s) => EXAM_STATUS_TEXT[s] || s || '—'

function examReady(p) {
  if (!p.exam_date) return false
  const d = new Date()
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return p.exam_date <= iso
}
const masterySubjects = computed(() => mastery.value.subjects || [])
const distColor = computed(() =>
  distMetric.value === 'score'
    ? subjectColor(distSubject.value || (masterySubjects.value[0] || ''), masterySubjects.value)
    : ''
)

async function loadDist() {
  const subject = distMetric.value === 'score' ? distSubject.value : undefined
  try {
    const res = await getSchoolDistribution({ metric: distMetric.value, subject })
    distribution.value = res.data
  } catch {
    distribution.value = { buckets: [], counts: [], total: 0 }
  }
}

function switchMetric(m) {
  distMetric.value = m
  if (m === 'score' && !distSubject.value && masterySubjects.value.length) {
    distSubject.value = masterySubjects.value[0]
  }
  loadDist()
}

async function loadExamPlans() {
  examLoading.value = true
  try {
    const res = await getExamPlans()
    const list = (res.data || []).filter((p) => !myGrade.value || p.grade === myGrade.value)
    list.sort((a, b) => {
      const rank = (p) => {
        if (p.status === 'planned' && examReady(p)) return 0
        if (p.status === 'planned') return 1
        if (p.status === 'conducted') return 2
        return 3
      }
      const r = rank(a) - rank(b)
      if (r !== 0) return r
      return new Date(b.exam_date) - new Date(a.exam_date)
    })
    examPlans.value = list
  } catch (e) {
    examPlans.value = []
    ElMessage.error(requestErrorText(e, '暂无考试规划'))
  } finally {
    examLoading.value = false
  }
}

async function conduct(p) {
  try {
    await conductExam(p.id)
    ElMessage.success(`${p.subject} ${p.exam_type} 考试已进行，等待教师批阅`)
    loadExamPlans()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function load() {
  error.value = ''
  loading.value = true
  try {
    const [oRes, cRes, mRes] = await Promise.all([
      getSchoolOverview(), getGradeComparison(), getSubjectMastery(),
    ])
    overview.value = oRes.data
    classData.value = cRes.data
    mastery.value = mRes.data
    myClasses.value = classData.value.map((c) => c.class_name)
    if (myClasses.value.length && !jumpClass.value) jumpClass.value = myClasses.value[0]
    if (!distSubject.value && masterySubjects.value.length) distSubject.value = masterySubjects.value[0]
    await loadDist()
    loadExamPlans()
  } catch (e) {
    error.value = requestErrorText(e, '数据不存在')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

function enterClass() {
  if (jumpClass.value) router.push({ path: '/teacher', query: { class: jumpClass.value } })
}

const classOption = computed(() => {
  if (!classData.value || !classData.value.length) return {}
  void themeKey.value
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  return {
    tooltip: { trigger: 'axis', backgroundColor: tooltipTheme.backgroundColor, borderColor: tooltipTheme.borderColor, textStyle: tooltipTheme.textStyle },
    grid: { left: 50, right: 20, bottom: 60 },
    xAxis: { type: 'category', data: classData.value.map((c) => c.class_name), axisLabel: { fontSize: 11, interval: 0, color: pal.axisLabel }, axisLine: { lineStyle: { color: pal.axisLine } } },
    yAxis: { type: 'value', min: 0, max: 100, name: '成长指数', nameTextStyle: { color: pal.name }, axisLabel: { color: pal.name }, splitLine: { lineStyle: { color: pal.splitLine } } },
    series: [{
      type: 'bar',
      data: classData.value.map((c) => c.avg_growth_index),
      itemStyle: { borderRadius: [6, 6, 0, 0], color: (p) => ['#34d399', '#fbbf24', '#f87171'][p.dataIndex % 3] || '#60a5fa' },
      barWidth: 44,
      animationDelay: (i) => i * 80,
    }],
    animationDuration: 700,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

const masteryOption = computed(() => {
  const m = mastery.value?.rows || []
  if (!m.length) return {}
  void themeKey.value
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  const subjects = masterySubjects.value
  const data = subjects.map((s) => {
    const row = m.find((r) => r.grade === myGrade.value && r.subject === s)
    return { value: row ? row.avg_rate : 0, itemStyle: { color: subjectColor(s, subjects), borderRadius: [6, 6, 0, 0] } }
  })
  const wrapLabel = (name) => name.length > 2 ? name.slice(0, 2) + '\n' + name.slice(2) : name
  return {
    tooltip: { trigger: 'axis', confine: true, backgroundColor: tooltipTheme.backgroundColor, borderColor: tooltipTheme.borderColor, textStyle: tooltipTheme.textStyle, formatter: (p) => `<b>${p[0].name}</b><br/>掌握率: <b>${p[0].value}%</b>` },
    grid: { left: 50, right: 20, bottom: 96, top: 10 },
    xAxis: { type: 'category', data: subjects, axisLabel: { color: pal.axisLabel, fontSize: 11, interval: 0, lineHeight: 15, align: 'center', formatter: wrapLabel }, axisTick: { alignWithLabel: true }, axisLine: { lineStyle: { color: pal.axisLine } } },
    yAxis: { type: 'value', min: 0, max: 100, name: '掌握率', axisLabel: { color: pal.axisLabel, fontSize: 10, formatter: '{value}%' }, nameTextStyle: { color: pal.name, fontSize: 11 }, splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } } },
    series: [{ type: 'bar', data, barWidth: 36, animationDelay: (i) => i * 70 }],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

onMounted(() => {
  const u = getStoredUser()
  myGrade.value = u?.grade || ''
  load()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.dashboard.is-refreshing { opacity: 0.72; }
.admin-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.admin-title { font-size: 18px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px; }
.grade-chip {
  font-size: 12px; font-weight: 600; color: #a78bfa;
  background: rgba(167, 139, 250, 0.15); border: 1px solid rgba(167, 139, 250, 0.3);
  padding: 2px 10px; border-radius: 10px;
}
.toolbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.kpi-card { padding: 20px; text-align: center; }
.half-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; flex-wrap: wrap; gap: 6px; }
.card-hint { margin-left: 8px; font-size: 11px; color: var(--text-label); font-weight: 400; }
.metric-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.pill {
  font-size: 11px; padding: 2px 10px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: var(--pill-active-text); }
.dist-total { text-align: right; font-size: 11px; color: var(--text-label); padding: 6px 2px 0; }
.table-scroll { overflow-x: auto; }
.user-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-grid th { text-align: left; font-size: 11px; font-weight: 600; color: var(--text-label); padding: 6px 12px; border-bottom: 1px solid var(--glass-border); }
.user-grid td { padding: 10px 12px; color: var(--text-primary); border-bottom: 1px solid var(--glass-border); vertical-align: middle; }
.user-grid tr:last-child td { border-bottom: none; }
.user-cell-dim { color: var(--text-muted); }
.status-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.status-badge.status-pending { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.status-approved { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.status-badge.status-rejected { color: #f87171; background: rgba(248, 113, 113, 0.15); }
.status-badge.exam-planned { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.exam-conducted { color: #60a5fa; background: rgba(96, 165, 250, 0.15); }
.status-badge.exam-graded { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.no-data { text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px 0; }

@media (max-width: 768px) { .kpi-grid, .half-grid { grid-template-columns: 1fr; } }
</style>
