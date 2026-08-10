<template>
  <div class="score-container">
    <div class="score-toolbar">
      <span class="toolbar-label">科目</span>
      <div class="subject-pills">
        <button v-for="s in allSubjects" :key="s" :class="['pill', { active: selectedSubject === s }]"
                :style="selectedSubject === s ? { background: colorOf(s), borderColor: colorOf(s) } : {}"
                @click="selectSubject(s)">
          {{ s }}
        </button>
      </div>
    </div>
    <div class="split-layout">
      <div class="chart-area">
        <v-chart ref="chartRef" :option="option" style="height: 400px; width: 100%" autoresize />
        <div class="chart-footer">悬停图表任意位置或点击某一列查看测评详细总结</div>
      </div>
      <div class="table-area">
        <div class="table-header">成绩对照表</div>
        <div class="table-scroll" ref="tableScrollRef" v-snap>
          <table class="score-grid">
            <colgroup>
              <col class="col-corner" />
              <col v-for="col in columns" :key="col.key" class="col-data"
                   :style="{ width: colWidth + 'px', minWidth: colWidth + 'px', maxWidth: colWidth + 'px' }" />
            </colgroup>
            <thead>
              <tr>
                <th class="corner" rowspan="2">科目</th>
                <th v-for="g in columnGroups" :key="g.label" class="year-head" :colspan="g.cols.length">{{ g.label }}</th>
              </tr>
              <tr>
                <th v-for="col in columns" :key="col.key" class="col-head" :class="{ highlight: hoveredColumn === col.key }">{{ col.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIdx) in tableRows" :key="row.subject" class="anim-row"
                  :style="{ animationDelay: rowIdx * 40 + 'ms' }">
                <td class="row-label">{{ row.subject }}</td>
                <td v-for="col in columns" :key="col.key" class="cell"
                    :class="{ highlight: hoveredColumn === col.key }"
                    :style="{ color: colorOf(row.subject), fontWeight: row.values[col.key]?.exam_type === '期末' ? 700 : row.values[col.key]?.exam_type === '期中' ? 600 : 400 }">
                  {{ row.values[col.key] && row.values[col.key].score !== null ? row.values[col.key].score + '/' + row.values[col.key].max_score : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="subjectFootnotes.length" class="table-note">
          <span class="note-sign">*</span>
          <span>— 表示该学年未测评：{{ subjectFootnotes.join('、') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { subjectColor, themeKey, themeTooltip, readCSSVar } from '../utils/colors'
import { semesterSchoolYear } from '../utils/semesters'

const props = defineProps({ scores: Array, defaultSubject: String })
const emit = defineEmits(['exam-click'])

const chartRef = ref(null)
const hoveredColumn = ref('')

const allSubjects = computed(() => {
  if (!props.scores || !props.scores.length) return []
  return [...new Set(props.scores.map((s) => s.subject))]
})

function colorOf(s) {
  return subjectColor(s, allSubjects.value)
}

const selectedSubject = ref('')
function initSelected() {
  if (selectedSubject.value) return
  if (props.defaultSubject && allSubjects.value.includes(props.defaultSubject)) {
    selectedSubject.value = props.defaultSubject
  } else if (allSubjects.value.length) {
    selectedSubject.value = allSubjects.value[0]
  }
}
initSelected()
watch(allSubjects, () => {
  if (!allSubjects.value.length) {
    selectedSubject.value = ''
    return
  }
  if (!selectedSubject.value || !allSubjects.value.includes(selectedSubject.value)) {
    if (props.defaultSubject && allSubjects.value.includes(props.defaultSubject)) {
      selectedSubject.value = props.defaultSubject
    } else {
      selectedSubject.value = allSubjects.value[0]
    }
  }
})
function selectSubject(s) { selectedSubject.value = s }

const selectedRaw = computed(() => {
  if (!props.scores || !selectedSubject.value) return []
  return props.scores.filter((s) => s.subject === selectedSubject.value)
})

function baseLabel(s) {
  const base = s.exam_type === '期中' ? '期中综评'
    : s.exam_type === '期末' ? '期末综评'
    : parseInt(s.date.slice(5, 7)) + '月小测验'
  return s.semester ? `${s.semester}·${base}` : base
}

function uniqueLabelMap(list) {
  const dateSets = new Map()
  for (const s of list) {
    const b = baseLabel(s)
    if (!dateSets.has(b)) dateSets.set(b, new Set())
    dateSets.get(b).add(s.date)
  }
  const map = new Map()
  for (const s of list) {
    const b = baseLabel(s)
    map.set(s, dateSets.get(b).size > 1 ? `${b}·${s.date.slice(5, 10)}` : b)
  }
  return map
}

const labelMap = computed(() => (props.scores ? uniqueLabelMap(props.scores) : new Map()))

const chartData = computed(() => {
  if (!selectedRaw.value.length) return []
  const sorted = [...selectedRaw.value].sort((a, b) => a.date.localeCompare(b.date))
  const result = []
  for (const s of sorted) {
    if (s.score === null) continue
    result.push({ label: labelMap.value.get(s), score: s.score, raw: s })
  }
  return result
})

function columnAt(x) {
  const chart = chartRef.value && chartRef.value.chart
  const cd = chartData.value
  if (!chart || !cd.length) return ''
  let best = -1
  let bestDiff = Infinity
  for (let i = 0; i < cd.length; i++) {
    const cx = chart.convertToPixel({ xAxisIndex: 0 }, i)
    if (cx == null || Number.isNaN(cx)) continue
    const d = Math.abs(cx - x)
    if (d < bestDiff) { bestDiff = d; best = i }
  }
  return best >= 0 ? cd[best].label : ''
}

function onChartMove(e) {
  const col = columnAt(e.offsetX)
  if (col !== hoveredColumn.value) hoveredColumn.value = col
}

function onChartOut() {
  hoveredColumn.value = ''
}

const tableScrollRef = ref(null)
function scrollTableToCol() {
  const el = tableScrollRef.value
  const col = hoveredColumn.value
  if (!el || !col) return
  const heads = el.querySelectorAll('th.col-head')
  const idx = columns.value.findIndex((c) => c.key === col)
  if (idx < 0 || idx >= heads.length) return
  const cont = el.getBoundingClientRect()
  const th = heads[idx].getBoundingClientRect()
  const corner = el.querySelector('.corner')
  const stickyW = corner ? corner.getBoundingClientRect().width : 76
  const contentX = th.left - cont.left + el.scrollLeft
  const viewStart = el.scrollLeft + stickyW
  const viewEnd = el.scrollLeft + el.clientWidth
  if (contentX >= viewStart && contentX + th.width <= viewEnd) return
  const maxScroll = el.scrollWidth - el.clientWidth
  let target = contentX - stickyW - (el.clientWidth - stickyW - th.width) / 2
  target = Math.max(0, Math.min(target, maxScroll))
  el.scrollTo({ left: target, behavior: 'smooth' })
}
watch(hoveredColumn, scrollTableToCol)
watch(() => props.scores, () => { hoveredColumn.value = '' })

function onZrClick(e) {
  const chart = chartRef.value && chartRef.value.chart
  if (!chart || !chartData.value.length) return
  const [x, y] = [e.offsetX, e.offsetY]
  const pts = chartData.value.map((d, idx) => ({ d, px: chart.convertToPixel('grid', [idx, d.score]) }))
  let halfBand = 40
  const xs = pts.filter((p) => p.px).map((p) => p.px[0])
  if (xs.length > 1) {
    const sorted = [...xs].sort((a, b) => a - b)
    let minGap = Infinity
    for (let i = 1; i < sorted.length; i++) minGap = Math.min(minGap, sorted[i] - sorted[i - 1])
    if (Number.isFinite(minGap)) halfBand = Math.min(45, minGap / 2)
  }
  let best = null
  let bestDist = Infinity
  let bestX = null
  let bestXDist = Infinity
  for (const { d, px } of pts) {
    if (!px) continue
    const dist = Math.hypot(px[0] - x, px[1] - y)
    if (dist < bestDist) { bestDist = dist; best = d }
    const adx = Math.abs(px[0] - x)
    if (adx < bestXDist) { bestXDist = adx; bestX = d }
  }
  if (best && bestDist <= 45) emit('exam-click', best.raw)
  else if (bestX && bestXDist <= halfBand) emit('exam-click', bestX.raw)
}

let zrBound = false

/* ---- Table ---- */

const columns = computed(() => {
  if (!props.scores) return []
  const seen = new Set()
  const list = []
  const sorted = [...props.scores].sort((a, b) => a.date.localeCompare(b.date))
  for (const s of sorted) {
    const label = labelMap.value.get(s)
    if (!seen.has(label)) {
      seen.add(label)
      list.push({ key: label, label, date: s.date })
    }
  }
  return list
})

const colWidth = 76

const columnGroups = computed(() => {
  const groups = []
  let current = null
  for (const col of columns.value) {
    const sem = col.label.split('·')[0]
    const year = semesterSchoolYear(sem)
    const label = year ? `${year} 学年` : '其他'
    if (!current || current.label !== label) {
      current = { label, cols: [] }
      groups.push(current)
    }
    current.cols.push(col)
  }
  return groups
})

const tableRows = computed(() => {
  if (!props.scores || !columns.value.length) return []
  const rows = {}
  for (const s of props.scores) {
    if (!rows[s.subject]) rows[s.subject] = {}
    const key = labelMap.value.get(s)
    rows[s.subject][key] = s
  }
  return allSubjects.value.map((subj) => ({
    subject: subj,
    values: rows[subj] || {},
  }))
})

const subjectFootnotes = computed(() => {
  if (!columns.value.length) return []
  const notes = []
  for (const row of tableRows.value) {
    const has = (c) => !!row.values[c.key] && row.values[c.key].score !== null
    const idx = columns.value.findIndex(has)
    const lastIdx = columns.value.map(has).lastIndexOf(true)
    if (idx < 0) continue
    const startLabel = columns.value[idx].label.split('·')[0]
    const endLabel = columns.value[lastIdx].label.split('·')[0]
    const parts = []
    if (idx > 0) parts.push(`${startLabel}起测评`)
    if (lastIdx < columns.value.length - 1) parts.push(`${endLabel}后停测`)
    if (parts.length) notes.push(`${row.subject}（${parts.join('、')}）`)
  }
  return notes
})

/* ---- Chart Option ---- */

const option = computed(() => {
  const cd = chartData.value
  if (!cd.length || !selectedSubject.value) return {}
  void themeKey.value

  const maxScore = cd.length && cd[0].raw.max_score ? cd[0].raw.max_score : 100
  const color = colorOf(selectedSubject.value)
  const tooltipTheme = themeTooltip()
  const light = document.documentElement.getAttribute('data-theme') === 'light'
  const textPrimary = light ? '#1a202c' : '#e2e8f0'
  const textSecondary = light ? '#2d3748' : '#c8d0d8'
  const textMuted = light ? '#718096' : '#8899aa'
  const tagFinal = readCSSVar('--tag-final')
  const tagMidterm = readCSSVar('--tag-midterm')

  return {
    tooltip: {
      trigger: 'axis',
      triggerOn: 'mousemove|click',
      confine: true,
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
      axisPointer: { ...tooltipTheme.axisPointer, snap: true },
      formatter: (p) => {
        const point = p[0]
        if (!point) return ''
        const d = cd.find((x) => x.label === point.name)
        if (!d) return ''
        const s = d.raw
        const tag = (s.exam_type === '期中' || s.exam_type === '期末')
          ? `<span style="color:${s.exam_type === '期末' ? tagFinal : tagMidterm};font-weight:700;font-size:11px;margin-left:4px">${s.exam_type === '期末' ? '期末综评' : '期中综评'}</span>`
          : ''
        return `<div style="font-weight:600;margin-bottom:4px;color:${textPrimary}">${selectedSubject.value}${tag}</div>`
          + `<div style="color:${textSecondary}">得分: <b>${s.score}/${s.max_score}</b></div>`
          + `<div style="font-size:11px;color:${textMuted};border-top:1px solid ${light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.06)'};padding-top:4px;margin-top:4px">点击查看详细总结</div>`
      },
    },
    grid: { left: 56, right: 20, bottom: 40, top: 28 },
    xAxis: {
      type: 'category',
      data: cd.map((d) => d.label),
      axisLabel: {
        fontSize: 10,
        interval: 0,
        color: (value) => value.includes('期中综评') ? tagMidterm
          : value.includes('期末综评') ? tagFinal
          : (light ? '#718096' : '#a3b1c1'),
      },
      axisLine: { lineStyle: { color: light ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)' } },
      axisTick: { alignWithLabel: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: maxScore,
      name: `分值`,
      nameTextStyle: { fontSize: 11, color: light ? '#718096' : '#a3b1c1' },
      splitLine: { lineStyle: { color: light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.04)', type: 'dashed' } },
      axisLabel: { fontSize: 10, color: light ? '#718096' : '#a3b1c1' },
    },
    series: [{
      type: 'line',
      smooth: false,
      symbol: 'circle',
      symbolSize: 14,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      connectNulls: false,
      emphasis: { scale: 22 / 14, itemStyle: { color, shadowBlur: 16, shadowColor: color } },
      animationDelay: (i) => i * 50,
      data: cd.map((d) => ({
        id: d.label,
        value: d.score,
      })),
    }],
    animationDuration: 900,
    animationDurationUpdate: 800,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
    stateAnimation: { duration: 300, easing: 'cubicOut' },
  }
})

watch(option, () => {
  const chart = chartRef.value && chartRef.value.chart
  if (!zrBound && chart) {
    zrBound = true
    const zr = chart.getZr()
    zr.on('click', onZrClick)
    zr.on('mousemove', onChartMove)
    zr.on('mouseout', onChartOut)
    zr.on('globalout', onChartOut)
  }
})
</script>

<style scoped>
.score-container { width: 100%; display: flex; flex-direction: column; gap: 16px; }
.score-toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 0 6px; }
.toolbar-label { font-size: 12px; color: var(--text-label); font-weight: 500; flex-shrink: 0; }
.subject-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.pill {
  font-size: 11px; padding: 2px 10px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: var(--pill-active-text); }
.split-layout { display: flex; flex-direction: column; gap: 16px; }
.chart-area { width: 100%; }
.chart-footer { text-align: center; font-size: 11px; color: var(--text-label); padding: 4px 0 0; letter-spacing: 0.3px; }
.table-area {
  width: 100%;
  display: flex; flex-direction: column;
}
.table-header { font-size: 13px; font-weight: 600; color: var(--accent); padding: 10px 14px 6px; border-bottom: 1px solid var(--glass-border); }
.table-scroll { overflow-x: auto; flex: 1; padding: 0 4px 8px 0; scrollbar-width: thin; scrollbar-color: var(--text-label) transparent; }
.score-grid { border-collapse: collapse; font-size: 11px; table-layout: fixed; }
.score-grid th,
.score-grid td {
  box-sizing: border-box;
  height: 38px;
  padding: 0 4px;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score-grid .corner { text-align: left; padding-left: 14px; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; color: var(--text-secondary); }
.score-grid .col-corner { width: 76px; min-width: 76px; max-width: 76px; }
.score-grid .col-data { width: 76px; min-width: 76px; max-width: 76px; }
.score-grid .year-head { font-size: 10px; color: var(--text-muted); font-weight: 600; border-bottom: 2px solid var(--glass-border); }
.score-grid td { border-bottom: 1px solid var(--glass-border); transition: background 0.15s; color: var(--text-secondary); }
.score-grid .row-label { text-align: left; padding-left: 14px; font-weight: 600; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; }
.score-grid td.highlight { background: rgba(var(--accent-rgb), 0.10) !important; }
.score-grid th.highlight { background: rgba(var(--accent-rgb), 0.14) !important; }
.score-grid tr:hover td:not(.highlight):not(.row-label) { background: rgba(var(--accent-rgb), 0.06); }
.score-grid tr:hover .row-label,
.score-grid tr:hover .corner { background: linear-gradient(rgba(var(--accent-rgb), 0.06), rgba(var(--accent-rgb), 0.06)), linear-gradient(var(--glass-bg-solid), var(--glass-bg-solid)); }
.table-note { display: flex; gap: 4px; padding: 8px 10px 2px; font-size: 10px; line-height: 1.5; color: var(--text-label); }
.table-note .note-sign { color: var(--accent); }

.table-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
.table-scroll::-webkit-scrollbar-track { background: transparent; }
.table-scroll::-webkit-scrollbar-thumb { background: var(--text-label); border-radius: 3px; }
.table-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

@keyframes table-row-in {
  from { opacity: 0; transform: translateX(10px); }
  to { opacity: 1; transform: translateX(0); }
}
.score-grid tbody tr { animation: table-row-in 0.45s cubic-bezier(0.22, 0.61, 0.36, 1) both; }

@media (max-width: 768px) {
  .split-layout { flex-direction: column; }
  .table-area { width: 100%; flex-shrink: 1; }
}
</style>
