<template>
  <div class="quality-container">
    <div class="quality-toolbar">
      <div class="subject-pills">
        <button v-for="s in subjectList" :key="s" :class="['pill', { active: selectedSubject === s }]"
                :style="selectedSubject === s ? { background: subjectColorOf(s), borderColor: subjectColorOf(s) } : {}"
                @click="selectSubject(s)">
          <span v-html="subjectIcon(s)"></span>
          {{ s }}
        </button>
      </div>
      <span style="flex:1"></span>
      <el-select v-model="selectedSemester" placeholder="全部学期" size="small" class="glass-select" style="width:170px">
        <el-option label="全部学期" value="" />
        <el-option v-for="s in semesterList" :key="s" :label="s" :value="s" />
      </el-select>
    </div>

    <div class="quality-body">
      <div class="quality-chart">
        <v-chart v-if="radarHasData" ref="chartRef" :option="radarOption" style="height:300px" autoresize />
        <div v-else class="chart-empty" style="height:300px">暂无素质数据</div>
      </div>
      <div class="quality-table" :style="{ '--qtable-w': qualityTableWidth + 'px' }">
        <div class="quality-table-title">{{ selectedSubject }} · 各维度等级</div>
        <div class="table-scroll" v-snap>
          <table class="quality-grid">
            <thead>
              <tr>
                <th class="q-corner">维度</th>
                <th v-for="col in gradeColumns" :key="col" class="q-head"
                    :style="{ width: qColWidth + 'px', minWidth: qColWidth + 'px', maxWidth: qColWidth + 'px' }">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(dim, dimIdx) in dimensionList" :key="dim" :class="{ 'row-hover': hoveredDim === dim }" class="anim-row"
                  :style="{ animationDelay: dimIdx * 40 + 'ms' }"
                  @mouseenter="rowEnter(dim)" @mouseleave="rowLeave">
                <td class="q-row-label">{{ dim }}</td>
                <td v-for="col in gradeColumns" :key="col" class="q-cell"
                    :class="{ highlight: hoveredCell === dim + '|' + col }"
                    :style="{ color: gradeColor(cellGrade(dim, col)), width: qColWidth + 'px', minWidth: qColWidth + 'px', maxWidth: qColWidth + 'px' }">
                  <el-tooltip v-if="cellGrade(dim, col)" placement="top" effect="dark" :hide-after="0" :enterable="false">
                    <template #content>
                      <div class="q-tip-title">{{ dim }} · {{ col }}</div>
                      <div class="q-tip-row">等级: <b :style="{ color: gradeColor(cellGrade(dim, col)) }">{{ cellGrade(dim, col) }}</b></div>
                      <div class="q-tip-row">得分: <b>{{ cellScore(dim, col) }}</b></div>
                      <div v-if="cellDist(dim, col)" class="q-tip-row q-tip-dist">班级分布: {{ cellDist(dim, col) }}</div>
                    </template>
                    <span class="q-cell-text" @mouseenter="hoveredCell = dim + '|' + col"
                          @mouseleave="hoveredCell = ''">{{ cellGrade(dim, col) }}</span>
                  </el-tooltip>
                  <span v-else class="q-cell-text q-cell-empty">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="quality-note">等级按 9 档评定（A+ ~ C-），悬浮单元格查看分数与班级分布</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { themeKey, readCSSVar } from '../utils/colors'

const props = defineProps({
  subjects: { type: Array, default: () => [] },
})

const SUBJECT_COLORS = { 音乐: '#ec4899', 体育: '#34d399', 美术: '#f97316', 信息技术: '#0ea5e9' }
const GRADE_ORDER = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-']

const selectedSubject = ref('')
const selectedSemester = ref('')
const hoveredCell = ref('')
const hoveredDim = ref('')
const chartRef = ref(null)

const subjectList = computed(() => props.subjects.map((s) => s.subject))
const semesterList = computed(() => {
  const set = new Set()
  for (const s of props.subjects) for (const sem of s.semesters) set.add(sem.semester)
  return [...set]
})

watch(subjectList, (list) => {
  if (list.length && !list.includes(selectedSubject.value)) {
    selectedSubject.value = list[0]
  }
})
watch(semesterList, (list) => {
  if (selectedSemester.value && !list.includes(selectedSemester.value)) {
    selectedSemester.value = ''
  }
})
watch(() => props.subjects, () => {
  if (!selectedSubject.value && subjectList.value.length) {
    selectedSubject.value = subjectList.value[0]
  }
}, { deep: true })
if (!selectedSubject.value && subjectList.value.length) {
  selectedSubject.value = subjectList.value[0]
}

const currentSubject = computed(() =>
  props.subjects.find((s) => s.subject === selectedSubject.value) || null
)

const radarHasData = computed(() =>
  dimensionList.value.length > 0 && currentSemesters.value.length > 0
)

const currentSemesters = computed(() => {
  const sems = currentSubject.value?.semesters || []
  if (!selectedSemester.value) return sems
  return sems.filter((s) => s.semester === selectedSemester.value)
})

const dimensionList = computed(() => {
  const set = new Set()
  for (const s of currentSemesters.value) for (const d of s.dimensions) set.add(d.dimension)
  return [...set]
})

const gradeColumns = computed(() => currentSemesters.value.map((s) => s.semester))

const qColWidth = 76

const qualityTableWidth = computed(() => 76 + Math.min(3, gradeColumns.value.length) * qColWidth)

function subjectColorOf(s) {
  return SUBJECT_COLORS[s] || '#34d399'
}

function selectSubject(s) {
  selectedSubject.value = s
}

function subjectIcon(s) {
  const icons = {
    音乐: '<svg viewBox="0 0 24 24" width="12" height="12" style="vertical-align:-1px;margin-right:3px" fill="currentColor"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    体育: '<svg viewBox="0 0 24 24" width="12" height="12" style="vertical-align:-1px;margin-right:3px" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="5" r="2"/><path d="M8 8l3 3 5-1 2 3 3 1M6 10l4 3v6M14 13l2 5"/></svg>',
    美术: '<svg viewBox="0 0 24 24" width="12" height="12" style="vertical-align:-1px;margin-right:3px" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="13.5" cy="6.5" r="2.5"/><path d="M13 9l-6 9h12l-3-5.5"/><path d="M5 21h14"/></svg>',
    信息技术: '<svg viewBox="0 0 24 24" width="12" height="12" style="vertical-align:-1px;margin-right:3px" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M9 10l-2 2 2 2M15 10l2 2-2 2"/></svg>',
  }
  return icons[s] || ''
}

function findCell(dim, sem) {
  const semData = currentSemesters.value.find((s) => s.semester === sem)
  return semData?.dimensions.find((d) => d.dimension === dim) || null
}

function cellGrade(dim, sem) {
  return findCell(dim, sem)?.grade || ''
}

function cellScore(dim, sem) {
  const d = findCell(dim, sem)
  return d ? `${d.score} 分` : ''
}

function cellDist(dim, sem) {
  const d = findCell(dim, sem)
  if (!d || !d.distribution) return ''
  return Object.entries(d.distribution).map(([g, n]) => `${g}×${n}`).join(' ')
}

function cellTitle(dim, sem) {
  const d = findCell(dim, sem)
  if (!d) return ''
  const parts = [`${d.dimension}: ${d.grade} (${d.score}分)`]
  if (props.subjects && d.distribution) {
    parts.push('班级分布: ' + Object.entries(d.distribution).map(([g, n]) => `${g}×${n}`).join(' '))
  }
  return parts.join('\n')
}

function gradeColor(grade) {
  const idx = GRADE_ORDER.indexOf(grade)
  if (idx < 0) return 'var(--text-label)'
  const t = idx / (GRADE_ORDER.length - 1)
  const r = Math.round(52 * (1 - t) + 240 * t)
  const g = Math.round(211 * (1 - t) + 82 * t)
  const b = Math.round(153 * (1 - t) + 82 * t)
  return `rgb(${r},${g},${b})`
}

const radarOption = computed(() => {
  void themeKey.value
  const dims = dimensionList.value
  const sems = currentSemesters.value
  if (!dims.length || !sems.length) return {}
  const accent = readCSSVar('--accent')
  const accentRGB = readCSSVar('--accent-rgb')
  const textMuted = readCSSVar('--text-muted')
  const latest = sems[sems.length - 1]
  const rawValues = dims.map((d) => latest.dimensions.find((x) => x.dimension === d)?.score ?? 0)
  const indicators = dims.map((d) => ({ name: d, max: 100 }))
  const graphic = []
  if (hoveredDim.value) {
    const chart = chartRef.value && chartRef.value.chart
    const idx = dims.indexOf(hoveredDim.value)
    if (chart && idx >= 0) {
      const W = chart.getWidth()
      const H = chart.getHeight()
      const cx = W / 2
      const cy = H / 2
      const r = Math.min(W, H) / 2 * 0.58
      const a = (idx * Math.PI * 2) / dims.length
      graphic.push({
        type: 'circle',
        shape: { cx: cx + r * Math.sin(a), cy: cy - r * Math.cos(a), r: 7 },
        style: { fill: accent, shadowBlur: 12, shadowColor: `rgba(${accentRGB},0.8)` },
        z: 100,
      })
    }
  }
  return {
    graphic,
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (p) => `${p.name}: <b>${p.value}</b> 分`,
    },
    radar: {
      indicator: indicators,
      shape: 'circle',
      center: ['50%', '50%'],
      radius: '58%',
      splitArea: { areaStyle: { color: [`rgba(${accentRGB},0.02)`, `rgba(${accentRGB},0.06)`] } },
      axisLine: { lineStyle: { color: `rgba(${accentRGB},0.25)` } },
      axisName: { color: textMuted, fontSize: 12 },
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 6,
      data: [{
        value: rawValues,
        name: latest.semester,
        areaStyle: { color: `rgba(${accentRGB},0.22)` },
        lineStyle: { color: accent, width: 2 },
        itemStyle: { color: accent },
      }],
    }],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

let zrBound = false

function radarGeometry() {
  const chart = chartRef.value && chartRef.value.chart
  const dims = dimensionList.value
  if (!chart || !dims.length) return null
  const W = chart.getWidth()
  const H = chart.getHeight()
  return {
    cx: W / 2,
    cy: H / 2,
    r: Math.min(W, H) / 2 * 0.58,
    n: dims.length,
  }
}

function dimAtPoint(x, y) {
  const dims = dimensionList.value
  const g = radarGeometry()
  if (!g) return ''
  const dx = x - g.cx
  const dy = y - g.cy
  const dist = Math.hypot(dx, dy)
  if (dist > g.r * 1.3) return ''
  let ang = Math.atan2(dx, -dy)
  if (ang < 0) ang += Math.PI * 2
  const step = (Math.PI * 2) / g.n
  let best = 0
  let bestDiff = Infinity
  dims.forEach((d, i) => {
    let diff = Math.abs(ang - i * step)
    if (diff > Math.PI) diff = Math.PI * 2 - diff
    if (diff < bestDiff) { bestDiff = diff; best = i }
  })
  return dims[best]
}

function onRadarMove(e) {
  const dim = dimAtPoint(e.offsetX, e.offsetY)
  if (dim !== hoveredDim.value) hoveredDim.value = dim
}

function onRadarOut() {
  if (hoveredDim.value) hoveredDim.value = ''
}

function rowEnter(dim) {
  hoveredDim.value = dim
}

function rowLeave() {
  hoveredDim.value = ''
}

watch(radarOption, () => {
  const chart = chartRef.value && chartRef.value.chart
  if (!zrBound && chart) {
    zrBound = true
    chart.getZr().on('mousemove', onRadarMove)
    chart.getZr().on('mouseout', onRadarOut)
    chart.getZr().on('globalout', onRadarOut)
  }
})

// 图表随 v-if 卸载后，重置绑定标记，避免数据恢复后雷达联动失效
watch(radarHasData, (has) => {
  if (!has) zrBound = false
})

watch([selectedSubject, selectedSemester], () => {
  hoveredDim.value = ''
})
</script>

<style scoped>
.quality-container { width: 100%; }
.quality-toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 0 6px; flex-wrap: wrap; }
.subject-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.pill {
  font-size: 11px; padding: 3px 10px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-family: inherit;
  display: inline-flex; align-items: center;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: var(--pill-active-text); }

.quality-body { display: flex; gap: 16px; align-items: stretch; }
.quality-chart { flex: 1; min-width: 0; }
.quality-table {
  width: var(--qtable-w, 340px); flex-shrink: 0;
  display: flex; flex-direction: column;
}
.quality-table-title { font-size: 13px; font-weight: 600; color: var(--accent); padding: 10px 14px 6px; border-bottom: 1px solid var(--glass-border); }
.table-scroll { overflow-x: auto; flex: 1; padding: 0 4px 8px 0; scrollbar-width: thin; scrollbar-color: var(--text-label) transparent; }
.quality-grid { border-collapse: collapse; font-size: 11px; white-space: nowrap; table-layout: fixed; }
.quality-grid th { height: 38px; padding: 0 4px; text-align: center; color: var(--text-secondary); font-weight: 500; border-bottom: 1px solid var(--glass-border); }
.quality-grid .q-corner { text-align: left; padding-left: 14px; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; width: 76px; min-width: 76px; color: var(--text-secondary); }
.quality-grid .q-head { width: 76px; min-width: 76px; }
.quality-grid td { height: 38px; padding: 0 4px; text-align: center; border-bottom: 1px solid var(--glass-border); color: var(--text-secondary); transition: background 0.15s; }
.quality-grid .q-row-label { text-align: left; padding-left: 14px; font-weight: 600; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; }
.quality-grid .q-cell { width: 76px; min-width: 76px; font-weight: 700; }
.quality-grid td.highlight { background: rgba(var(--accent-rgb), 0.12) !important; }
.quality-grid tr.row-hover td { background: rgba(var(--accent-rgb), 0.10) !important; }
.quality-grid tr.row-hover td.highlight { background: rgba(var(--accent-rgb), 0.16) !important; }
.quality-grid tr.row-hover .q-row-label,
.quality-grid tr.row-hover .q-corner {
  background: linear-gradient(rgba(var(--accent-rgb), 0.10), rgba(var(--accent-rgb), 0.10)),
              linear-gradient(var(--glass-bg-solid), var(--glass-bg-solid));
}
.q-cell-text { display: inline-block; min-width: 16px; cursor: default; }
.q-cell-empty { color: var(--text-label); }
.q-tip-title { font-weight: 600; color: #e2e8f0; margin-bottom: 4px; font-size: 12px; }
.q-tip-row { font-size: 12px; color: #c8d0d8; line-height: 1.7; }
.q-tip-row b { color: #e2e8f0; }
.q-tip-dist { margin-top: 2px; border-top: 1px solid rgba(255,255,255,0.12); padding-top: 3px; color: #94a3b8; font-size: 11px; }
.quality-note { display: flex; gap: 4px; padding: 8px 10px 2px; font-size: 10px; line-height: 1.5; color: var(--text-label); }
.quality-table .table-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
.quality-table .table-scroll::-webkit-scrollbar-track { background: transparent; }
.quality-table .table-scroll::-webkit-scrollbar-thumb { background: var(--text-label); border-radius: 3px; }
.quality-table .table-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

@keyframes table-row-in {
  from { opacity: 0; transform: translateX(10px); }
  to { opacity: 1; transform: translateX(0); }
}
.quality-grid tbody tr { animation: table-row-in 0.45s cubic-bezier(0.22, 0.61, 0.36, 1) both; }

@media (max-width: 768px) {
  .quality-body { flex-direction: column; }
  .quality-table { width: 100%; flex-shrink: 1; }
}
</style>
