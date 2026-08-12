<template>
  <div class="dashboard" :class="{ 'is-refreshing': loading && overview }">
    <div class="admin-toolbar no-print">
      <span class="admin-title">全校数据总览</span>
      <el-button class="btn-secondary refresh-btn" :loading="loading" @click="load">
        <svg viewBox="0 0 24 24" width="13" height="13" style="margin-right:5px">
          <path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v4h-4" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        刷新
      </el-button>
    </div>
    <transition name="rise" appear>
    <div v-if="overview" class="content-wrap">
      <div class="kpi-grid">
        <div class="glass-card kpi-card" v-reveal="{ delay: 0 }"><div class="kpi-label">学生总数</div><div class="kpi-value"><CountUp :value="overview.total_students" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 60 }"><div class="kpi-label">全校平均成长指数<GrowthIndexTip /></div><div class="kpi-value"><CountUp :value="overview.avg_growth_index" :decimals="2" /></div></div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 120 }"><div class="kpi-label">年级数</div><div class="kpi-value"><CountUp :value="Object.keys(overview.grades).length" /></div></div>
      </div>

      <div class="half-grid">
        <div class="glass-card chart-card">
          <div class="card-header">年级对比</div>
          <v-chart :option="gradeOption" style="height:300px" autoresize />
        </div>
        <div class="glass-card chart-card">
          <div class="card-header">各班平均成长指数</div>
          <v-chart :option="classOption" style="height:300px" autoresize />
        </div>
      </div>

      <div class="half-grid">
        <WarningBoard />
        <AiAsk />
      </div>

      <div class="glass-card" style="padding:0">
        <div class="table-header">各年级详情</div>
        <el-table :data="gradeTable" highlight-current-row class="glass-table" style="width:100%">
          <el-table-column prop="grade" label="年级" width="120" />
          <el-table-column prop="avg_growth_index" label="平均成长指数" width="160" />
          <el-table-column prop="student_count" label="学生人数" />
        </el-table>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M3 3v18h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M5 16l4-5 3 3 5-7" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
           全校数据分布
          <span class="card-hint">点击柱子查看学生</span>
          <span style="flex:1"></span>
          <el-select v-model="schoolDistGrade" placeholder="全校" size="small" class="glass-select" style="width:120px">
            <el-option label="全校" value="" />
            <el-option v-for="g in gradeOptions" :key="g" :label="g" :value="g" />
          </el-select>
        </div>
        <div class="dist-toolbar">
          <div class="metric-pills">
            <button :class="['pill', { active: schoolMetric === 'growth' }]" @click="schoolMetric = 'growth'">成长指数</button>
            <button :class="['pill', { active: schoolMetric === 'score' }]" @click="schoolMetric = 'score'">各科平均分</button>
          </div>
          <div v-if="schoolMetric === 'score'" class="subject-pills">
            <button v-for="s in schoolSubjects" :key="s" class="pill"
                    :class="{ active: schoolSubject === s }"
                    :style="schoolSubject === s ? { background: schoolSubjectColor(s), borderColor: schoolSubjectColor(s) } : {}"
                    @click="schoolSubject = s">{{ s }}</button>
          </div>
        </div>
        <DistributionChart :buckets="schoolDistribution.buckets" :counts="schoolDistribution.counts"
                           :color="schoolDistColor" @bucket-click="onBucketClick" />
        <div v-if="schoolDistribution.total" class="dist-total">共 {{ schoolDistribution.total }} 名</div>
      </div>

      <div class="glass-card chart-card" id="exams">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <rect x="4" y="3" width="16" height="18" rx="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M8 8h8M8 12h8M8 16h4" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <circle cx="17" cy="17" r="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
          </svg>
          考试规划
          <span class="card-hint">下达考试 → 年级组长进行 → 教师批阅自动录入</span>
          <span style="flex:1"></span>
          <el-button size="small" class="btn-primary" style="margin-right:8px" @click="openCreateExam">下达考试</el-button>
          <el-select v-model="examFilter" placeholder="全部状态" size="small" class="glass-select" style="width:120px"
                     @change="loadExamPlans">
            <el-option label="全部状态" value="" />
            <el-option label="待进行" value="planned" />
            <el-option label="已进行" value="conducted" />
            <el-option label="已批阅" value="graded" />
          </el-select>
          <el-select v-model="examGradeFilter" placeholder="全部年级" size="small" class="glass-select" style="width:110px"
                     @change="loadExamPlans">
            <el-option label="全部年级" value="" />
            <el-option v-for="g in ['初一','初二','初三']" :key="g" :label="g" :value="g" />
          </el-select>
        </div>
        <div class="table-scroll" v-snap="{ columns: 'th' }" style="padding:8px 0 0">
          <table class="user-grid">
            <thead>
              <tr>
                <th>考试</th>
                <th>科目</th>
                <th>年级</th>
                <th>考试日期</th>
                <th>学期</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in examPlans" :key="p.id">
                <td>{{ p.exam_type }}</td>
                <td>{{ p.subject }}</td>
                <td class="user-cell-dim">{{ p.grade }}</td>
                <td class="user-cell-dim">{{ p.exam_date }}</td>
                <td class="user-cell-dim">{{ p.semester }}</td>
                <td><span class="status-badge" :class="`exam-${p.status}`">{{ examStatusText(p.status) }}</span></td>
                <td>
                  <template v-if="p.status === 'planned'">
                    <el-button size="small" class="btn-secondary" style="margin-right:6px"
                               :disabled="!examReady(p)" :title="examReady(p) ? '' : '未到考试日期，暂不能进行'"
                               @click="doConduct(p)">进行</el-button>
                    <el-button size="small" class="btn-danger-ghost" @click="doDeletePlan(p)">删除</el-button>
                  </template>
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

    <el-dialog v-model="examCreateVisible" title="下达考试规划" width="520px" class="glass-dialog">
      <div class="create-form">
        <el-form label-width="86px">
          <el-form-item label="考试类型">
            <el-select v-model="examForm.exam_type" class="glass-select" placeholder="选择类型" style="width:100%">
              <el-option label="月考" value="月考" />
              <el-option label="期中" value="期中" />
              <el-option label="期末" value="期末" />
            </el-select>
          </el-form-item>
          <el-form-item label="年级">
            <el-select v-model="examForm.grade" class="glass-select" placeholder="选择年级" style="width:100%"
                       @change="onExamGradeChange">
              <el-option v-for="g in ['初一','初二','初三']" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
          <el-form-item label="科目">
            <div style="width:100%">
              <el-select v-model="examForm.subjects" multiple collapse-tags collapse-tags-tooltip
                         class="glass-select" placeholder="选择科目" style="width:100%">
                <el-option v-for="s in examSubjectOptions" :key="s" :label="s" :value="s" />
              </el-select>
              <div style="margin-top:6px;display:flex;align-items:center;gap:8px">
                <el-button size="small" class="btn-secondary" style="height:24px" @click="selectAllSubjects">全科</el-button>
                <el-button size="small" class="btn-danger-ghost" style="height:24px" @click="examForm.subjects = []">清空</el-button>
                <span v-if="examForm.subjects.length" class="user-cell-dim" style="font-size:12px">
                  已选 {{ examForm.subjects.length }} 科
                </span>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="考试日期">
            <el-date-picker v-model="examForm.exam_date" type="date" size="default" class="glass-select"
                            value-format="YYYY-MM-DD" placeholder="选择日期"
                            :disabled-date="disabledExamDate" style="width:100%" />
          </el-form-item>
          <el-form-item v-if="examForm.semester" label="对应学期">
            <span class="user-cell-dim">{{ examForm.semester }}</span>
          </el-form-item>
          <el-form-item v-if="selectedExamMax" label="科目满分">
            <span class="user-cell-dim">{{ selectedExamMax }}</span>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button class="btn-secondary" @click="examCreateVisible = false">取消</el-button>
        <el-button class="btn-primary" :loading="examCreating" @click="doCreateExam">下达</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="distDialog" :title="`分布下钻 · ${distBucketLabel} 区间`" width="560px">
      <div v-loading="distLoading" :element-loading-background="readCSSVar('--glass-bg-solid')">
        <el-table :data="distStudents" empty-text="该区间暂无学生" max-height="380" size="small" class="glass-table">
          <el-table-column prop="student_id" label="学号" width="80" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="class_name" label="班级" width="110" />
          <el-table-column prop="value" label="数值" width="90" />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { getSchoolOverview, getGradeComparison, getSubjectMastery, getSchoolDistribution, getSchoolDistributionStudents, getExamPlans, getExamPlanMeta, createExamPlan, deleteExamPlan, conductExam, requestErrorText } from '../utils/api'
import { themeKey, themeTooltip, themePalette, subjectColor, readCSSVar } from '../utils/colors'
import { ElMessage } from 'element-plus'
import PageSkeleton from '../components/PageSkeleton.vue'
import CountUp from '../components/CountUp.vue'
import FailCard from '../components/FailCard.vue'
import DistributionChart from '../components/DistributionChart.vue'
import GrowthIndexTip from '../components/GrowthIndexTip.vue'
import WarningBoard from '../components/WarningBoard.vue'
import AiAsk from '../components/AiAsk.vue'

const overview = ref(null)
const classData = ref([])
const mastery = ref({ grades: [], subjects: [], rows: [] })
const error = ref('')
const loading = ref(false)

/* ---- 考试规划 ---- */

const EXAM_SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '道德与法治', '地理']

const examPlans = ref([])
const examFilter = ref('')
const examGradeFilter = ref('')
const examCreateVisible = ref(false)
const examCreating = ref(false)
const examForm = ref({ exam_type: '月考', grade: '初一', subjects: ['语文'], exam_date: '', semester: '' })
const examPlanMeta = ref(null)

const EXAM_STATUS_TEXT = { planned: '待进行', conducted: '已进行', graded: '已批阅' }
function examStatusText(s) { return EXAM_STATUS_TEXT[s] || s || '—' }

function examMetaForGrade(g) {
  const grades = examPlanMeta.value?.grades || []
  return grades.find((x) => x.grade === g) || null
}

const examSubjectOptions = computed(() => {
  const meta = examMetaForGrade(examForm.value.grade)
  if (!meta) return EXAM_SUBJECTS
  const set = new Set()
  meta.semesters.forEach((s) => s.subjects.forEach((sub) => set.add(sub)))
  return [...set]
})

const examDateRanges = computed(() => {
  const meta = examMetaForGrade(examForm.value.grade)
  return meta ? meta.semesters : []
})

function dateInRange(dateStr, range) {
  return dateStr >= range.start && dateStr <= range.end
}

function semesterForDate(dateStr) {
  if (!dateStr) return ''
  const ranges = examDateRanges.value
  const hit = ranges.find((r) => dateInRange(dateStr, r))
  return hit ? hit.semester : ''
}

const selectedExamMax = computed(() => {
  const sem = examForm.value.semester
  const ranges = examDateRanges.value
  const meta = ranges.find((r) => r.semester === sem)
  if (!meta) return ''
  const parts = examForm.value.subjects
    .filter((s) => meta.subjects.includes(s))
    .map((s) => `${s} ${meta.max_scores[s]} 分`)
  return parts.length ? parts.join('，') : ''
})

const disabledExamDate = (date) => {
  if (!examForm.value.grade) return false
  const ranges = examDateRanges.value
  if (!ranges.length) return false
  const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  return !ranges.some((r) => dateInRange(iso, r))
}

function selectAllSubjects() {
  examForm.value.subjects = [...examSubjectOptions.value]
}

function onExamGradeChange() {
  examForm.value.exam_date = ''
  examForm.value.semester = ''
  examForm.value.subjects = examSubjectOptions.value.length ? [examSubjectOptions.value[0]] : []
}

watch(() => examForm.value.exam_date, (val) => {
  examForm.value.semester = semesterForDate(val)
  if (examForm.value.semester) {
    const meta = examDateRanges.value.find((r) => r.semester === examForm.value.semester)
    if (meta) {
      examForm.value.subjects = examForm.value.subjects.filter((s) => meta.subjects.includes(s))
    }
  }
})

async function loadExamPlans() {
  try {
    const res = await getExamPlans(examFilter.value || undefined, examGradeFilter.value || undefined)
    examPlans.value = res.data || []
  } catch (e) {
    examPlans.value = []
    ElMessage.error(requestErrorText(e, '暂无考试规划'))
  }
}

function openCreateExam() {
  examForm.value = { exam_type: '月考', grade: '初一', subjects: [], exam_date: '', semester: '' }
  examForm.value.subjects = examSubjectOptions.value.length ? [examSubjectOptions.value[0]] : []
  examCreateVisible.value = true
}

async function doCreateExam() {
  const f = examForm.value
  if (!f.exam_date) { ElMessage.warning('请选择考试日期'); return }
  if (!f.subjects.length) { ElMessage.warning('请至少选择一个科目'); return }
  if (!f.semester) {
    const sem = semesterForDate(f.exam_date)
    if (!sem) { ElMessage.error('所选日期不在该年级学业日历内'); return }
    f.semester = sem
  }
  examCreating.value = true
  let created = 0
  try {
    for (const subject of f.subjects) {
      await createExamPlan({ examType: f.exam_type, subject, grade: f.grade, examDate: f.exam_date })
      created += 1
    }
    ElMessage.success(`已下达 ${f.grade} ${created} 门 ${f.exam_type} 考试`)
    examCreateVisible.value = false
    loadExamPlans()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '下达失败，请检查日期是否在学业日历内')
  } finally {
    examCreating.value = false
  }
}

function examReady(p) {
  if (!p.exam_date) return false
  const d = new Date()
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return p.exam_date <= iso
}

async function doConduct(p) {
  try {
    await conductExam(p.id)
    ElMessage.success(`${p.subject} ${p.exam_type} 已标记为进行中`)
    loadExamPlans()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function doDeletePlan(p) {
  try {
    await deleteExamPlan(p.id)
    ElMessage.success(`已删除 ${p.subject} ${p.exam_type} 考试规划`)
    loadExamPlans()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function load() {
  error.value = ''
  loading.value = true
  try {
    const [oRes, cRes, mRes] = await Promise.all([getSchoolOverview(), getGradeComparison(), getSubjectMastery()])
    overview.value = oRes.data
    classData.value = cRes.data
    mastery.value = mRes.data
    getExamPlanMeta().then((res) => {
      examPlanMeta.value = res.data || null
    }).catch(() => { examPlanMeta.value = null })
    loadDistribution()
    loadExamPlans()
  } catch (e) {
    error.value = requestErrorText(e, '数据不存在')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)

const schoolMetric = ref('growth')
const schoolSubject = ref('')
const schoolDistGrade = ref('')
const schoolDistribution = ref({ buckets: [], counts: [], total: 0 })
let distSeq = 0

const distDialog = ref(false)
const distLoading = ref(false)
const distBucketLabel = ref('')
const distStudents = ref([])

async function onBucketClick(label) {
  distBucketLabel.value = label
  distDialog.value = true
  distLoading.value = true
  distStudents.value = []
  try {
    const subject = schoolMetric.value === 'score' ? schoolSubject.value : undefined
    const grade = schoolDistGrade.value || undefined
    const res = await getSchoolDistributionStudents(schoolMetric.value, subject, grade, label)
    distStudents.value = res.data.students || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '下钻查询失败')
  } finally {
    distLoading.value = false
  }
}

const schoolSubjects = computed(() => mastery.value.subjects || [])
const schoolDistColor = computed(() =>
  schoolMetric.value === 'score'
    ? subjectColor(schoolSubject.value || (schoolSubjects.value[0] || ''), schoolSubjects.value)
    : ''
)
const schoolSubjectColor = (s) => subjectColor(s, schoolSubjects.value)

const gradeOptions = computed(() => {
  const g = overview.value?.grades
  return g ? Object.keys(g) : []
})

async function loadDistribution() {
  const metric = schoolMetric.value
  if (metric === 'score' && !schoolSubject.value) {
    if (!schoolSubjects.value.length) return
    schoolSubject.value = schoolSubjects.value[0]
    return
  }
  const seq = ++distSeq
  const subject = metric === 'score' ? schoolSubject.value : undefined
  const grade = schoolDistGrade.value || undefined
  try {
    const res = await getSchoolDistribution({ metric, subject, grade })
    if (seq !== distSeq) return
    schoolDistribution.value = res.data
  } catch (e) {
    if (seq === distSeq) schoolDistribution.value = { buckets: [], counts: [], total: 0 }
  }
}

watch([schoolMetric, schoolSubject, schoolDistGrade], loadDistribution)

const gradeTable = computed(() => {
  if (!overview.value?.grades) return []
  return Object.entries(overview.value.grades).map(([grade, v]) => ({
    grade, avg_growth_index: v.avg_growth_index, student_count: v.student_count,
  }))
})

const gradeOption = computed(() => {
  if (!overview.value?.grades) return {}
  void themeKey.value
  const entries = Object.entries(overview.value.grades)
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  return {
    tooltip: { trigger: 'axis', backgroundColor: tooltipTheme.backgroundColor, borderColor: tooltipTheme.borderColor, textStyle: tooltipTheme.textStyle },
    grid: { left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: entries.map(([k]) => k), axisLabel: { fontSize: 14, fontWeight: 'bold', color: pal.axisLabel }, axisLine: { lineStyle: { color: pal.axisLine } } },
    yAxis: { type: 'value', min: 0, max: 100, name: '成长指数', nameTextStyle: { color: pal.name }, axisLabel: { color: pal.name }, splitLine: { lineStyle: { color: pal.splitLine } } },
    series: [{
      type: 'bar',
      data: entries.map(([, v]) => v.avg_growth_index),
      itemStyle: { borderRadius: [8,8,0,0], color: (p) => ['#34d399','#fbbf24','#f87171'][p.dataIndex] || '#60a5fa' },
      barWidth: 60,
      universalTransition: true,
      animationDelay: (i) => i * 100,
    }],
    animationDuration: 700,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

const classOption = computed(() => {
  if (!classData.value || !classData.value.length) return {}
  void themeKey.value
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  return {
  tooltip: { trigger: 'axis', backgroundColor: tooltipTheme.backgroundColor, borderColor: tooltipTheme.borderColor, textStyle: tooltipTheme.textStyle },
  grid: { left: 50, right: 20, bottom: 70 },
  xAxis: {
    type: 'category',
    data: classData.value.map((c) => c.class_name),
    axisLabel: { rotate: 45, fontSize: 11, interval: 0, color: pal.axisLabel },
    axisLine: { lineStyle: { color: pal.axisLine } },
  },
  yAxis: { type: 'value', min: 0, max: 100, name: '成长指数', nameTextStyle: { color: pal.name }, axisLabel: { color: pal.name }, splitLine: { lineStyle: { color: pal.splitLine } } },
  series: [{
    type: 'bar',
    data: classData.value.map((c) => c.avg_growth_index),
    itemStyle: {
      borderRadius: [4,4,0,0],
      color: (p) => {
        const cls = classData.value[p.dataIndex]
        if (!cls) return '#60a5fa'
        return cls.grade === '初一' ? '#34d399' : cls.grade === '初二' ? '#fbbf24' : '#f87171'
      },
    },
    animationDelay: (i) => i * 60,
  }],
  animationDuration: 700,
  animationDurationUpdate: 600,
  animationEasing: 'cubicOut',
  animationEasingUpdate: 'cubicOut',
}
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.dashboard.is-refreshing { opacity: 0.72; }
.admin-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.admin-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.refresh-btn { padding: 8px 14px; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.kpi-card { padding: 20px; text-align: center; }
.half-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 12px; flex-wrap: wrap; gap: 6px; }
.table-header { font-weight: 600; font-size: 15px; color: var(--accent); padding: 14px 20px 8px; }
.glass-card .el-table__body tr:last-child td { border-bottom: none !important; }

.dist-toolbar { display: flex; flex-direction: column; gap: 8px; padding: 8px 0 6px; }
.metric-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.subject-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.pill {
  font-size: 11px; padding: 2px 10px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: var(--pill-active-text); }
.dist-total { text-align: right; font-size: 11px; color: var(--text-label); padding: 6px 2px 0; }

.card-hint { margin-left: 8px; font-size: 11px; color: var(--text-label); font-weight: 400; }
.table-scroll { overflow-x: auto; }
.user-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-grid th {
  text-align: left; font-size: 13px; font-weight: 500; color: var(--text-primary);
  padding: 10px 12px; border-bottom: 1px solid var(--glass-border);
}
.user-grid td { padding: 10px 12px; color: var(--text-primary); border-bottom: 1px solid var(--glass-border); vertical-align: middle; }
.user-grid tr:last-child td { border-bottom: none; }
.user-cell-dim { color: var(--text-muted); }
.user-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.user-badge.role-student { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.user-badge.role-teacher { color: #60a5fa; background: rgba(96, 165, 250, 0.15); }
.user-badge.role-grade_leader { color: #a78bfa; background: rgba(167, 139, 250, 0.15); }
.user-badge.role-admin { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.create-form { padding-top: 4px; }
.status-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.status-badge.status-pending { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.status-approved { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.status-badge.status-rejected { color: #f87171; background: rgba(248, 113, 113, 0.15); }
.status-badge.exam-planned { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.exam-conducted { color: #60a5fa; background: rgba(96, 165, 250, 0.15); }
.status-badge.exam-graded { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.btn-danger-ghost {
  font-size: 12px; color: #f87171;
  background: transparent; border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 10px; padding: 3px 12px; cursor: pointer; font-family: inherit; transition: all 0.2s;
}
.btn-danger-ghost:hover { background: rgba(248, 113, 113, 0.12); border-color: #f87171; }
.no-data { text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px 0; }

@media (max-width: 768px) { .kpi-grid, .half-grid { grid-template-columns: 1fr; } }
</style>
