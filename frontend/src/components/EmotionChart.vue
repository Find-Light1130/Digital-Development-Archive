<template>
  <v-chart :option="option" style="height: 200px" autoresize />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { themeKey, themeTooltip, themePalette, readCSSVar } from '../utils/colors'

const props = defineProps({ emotions: Array })

const levelLabels = { 1: '低落', 2: '一般', 3: '良好' }

const option = computed(() => {
  void themeKey.value
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  const accentRGB = readCSSVar('--accent-rgb')
  const levelColors = {
    1: readCSSVar('--level-4'),
    2: readCSSVar('--level-3'),
    3: readCSSVar('--level-1'),
  }
  const data = (props.emotions || []).map((e) => e.emotion_level)
  return {
    tooltip: {
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
      formatter: (p) => {
        const lbl = levelLabels[p.value] || p.value
        const clr = levelColors[p.value] || '#e6a23c'
        return `${p.name}<br/><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${clr};margin-right:4px"></span>情绪: ${lbl}`
      },
    },
    xAxis: {
      type: 'category',
      data: (props.emotions || []).map((e) => (e.date || '').slice(5)),
      axisLabel: { color: pal.axisLabel, fontSize: 10 },
      axisLine: { lineStyle: { color: pal.axisLine } },
    },
    yAxis: {
      type: 'value', min: 0.5, max: 3.5,
      splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } },
      axisLabel: {
        color: pal.axisLabel, fontSize: 10,
        formatter: (v) => levelLabels[v] || '',
      },
    },
    grid: { left: 40, right: 20, bottom: 24 },
    series: [
      {
        type: 'line',
        data: data.map((v) => ({
          value: v,
          symbol: 'circle',
          symbolSize: 10,
          itemStyle: { color: levelColors[v] || '#e6a23c', borderColor: 'rgba(255,255,255,0.2)', borderWidth: 1 },
        })),
        smooth: true,
        lineStyle: { color: `rgba(${accentRGB},0.35)`, width: 2 },
        areaStyle: { color: `rgba(${accentRGB},0.06)` },
        emphasis: { lineStyle: { width: 3 } },
      },
    ],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})
</script>
