<template>
  <div class="glass-card chart-card comp-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M3 21h18M5 21V10m7 11V5m7 16V8" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <circle cx="12" cy="5" r="1.5" fill="var(--accent)"/>
      </svg>
      综合素质
    </div>

    <div class="comp-stats">
      <div class="comp-stat"><div class="stat-label">活动总时长</div><div class="stat-value"><CountUp :value="stats.totalHours" :decimals="1" />h</div></div>
      <div class="comp-stat"><div class="stat-label">活动次数</div><div class="stat-value"><CountUp :value="stats.activityCount" /></div></div>
      <div class="comp-stat"><div class="stat-label">实践时长</div><div class="stat-value"><CountUp :value="stats.practiceHours" :decimals="1" />h</div></div>
      <div class="comp-stat"><div class="stat-label">获奖</div><div class="stat-value"><CountUp :value="awards.length" /></div></div>
    </div>

    <v-chart v-if="semesterStats.length" :option="option" style="height:220px" autoresize />
    <div v-else class="no-data">暂无活动记录</div>

    <div v-if="awards.length" class="awards-list">
      <div class="awards-title">获奖情况</div>
      <ul class="awards-items">
        <li v-for="a in awards" :key="a.id">
          <span class="award-dot"></span>
          <span class="award-title">{{ a.title }}</span>
          <span class="award-meta">{{ a.level }} · {{ a.date }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { themeKey, themeTooltip, themePalette, readCSSVar } from '../utils/colors'
import CountUp from './CountUp.vue'

const props = defineProps({
  semesterStats: { type: Array, default: () => [] },
  awards: { type: Array, default: () => [] },
  activities: { type: Array, default: () => [] },
})

const stats = computed(() => {
  let totalHours = 0
  let practiceHours = 0
  for (const s of props.semesterStats) {
    totalHours += s.total
    practiceHours += s.practice
  }
  return {
    totalHours: Math.round(totalHours * 10) / 10,
    practiceHours: Math.round(practiceHours * 10) / 10,
    activityCount: props.activities.length,
  }
})

const option = computed(() => {
  if (!props.semesterStats.length) return {}
  void themeKey.value
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  return {
    tooltip: {
      trigger: 'axis', confine: true,
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
    },
    legend: {
      data: ['活动时长', '实践时长'],
      textStyle: { color: pal.name, fontSize: 11 },
      bottom: 0,
    },
    grid: { left: 44, right: 16, top: 24, bottom: 44 },
    xAxis: {
      type: 'category',
      data: props.semesterStats.map((s) => s.semester),
      axisLabel: { fontSize: 10, color: pal.axisLabel },
      axisLine: { lineStyle: { color: pal.axisLine } },
    },
    yAxis: {
      type: 'value', name: '小时',
      nameTextStyle: { fontSize: 10, color: pal.name },
      axisLabel: { fontSize: 10, color: pal.axisLabel },
      splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } },
    },
    series: [
      {
        name: '活动时长', type: 'bar', barWidth: 16,
        data: props.semesterStats.map((s) => s.total),
        itemStyle: { color: readCSSVar('--success'), borderRadius: [4, 4, 0, 0] },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(52,211,153,0.4)' } },
        universalTransition: true,
      },
      {
        name: '实践时长', type: 'bar', barWidth: 16,
        data: props.semesterStats.map((s) => s.practice),
        itemStyle: { color: readCSSVar('--level-3'), borderRadius: [4, 4, 0, 0] },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(251,191,36,0.4)' } },
        universalTransition: true,
      },
    ],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})
</script>

<style scoped>
.comp-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 6px 0 10px; }
.comp-stat { text-align: center; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 10px; padding: 10px 6px; }
.stat-label { font-size: 11px; color: var(--text-muted); }
.stat-value { font-size: 18px; font-weight: 700; color: var(--accent); margin-top: 2px; }
.no-data { padding: 16px 0; color: var(--text-label); font-size: 13px; text-align: center; }
.awards-list { margin-top: 12px; border-top: 1px solid var(--glass-border); padding-top: 10px; }
.awards-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.awards-items { list-style: none; padding: 0; margin: 0; }
.awards-items li { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--glass-border); }
.awards-items li:last-child { border: none; }
.award-dot { width: 5px; height: 5px; min-width: 5px; border-radius: 50%; background: var(--accent); opacity: 0.6; }
.award-title { color: var(--text-primary); }
.award-meta { margin-left: auto; color: var(--text-label); font-size: 12px; }
@media (max-width: 768px) { .comp-stats { grid-template-columns: 1fr 1fr; } }
</style>
