<template>
  <v-chart :option="option" style="height: 300px" autoresize />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { themeKey, readCSSVar } from '../utils/colors'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({}),
    validator: (v) => v === null || v === undefined || typeof v === 'object',
  },
})

const INDICATORS = [
  { name: '学习能力', key: '学习能力' },
  { name: '心理健康', key: '心理健康' },
  { name: '体育健康', key: '体育健康' },
  { name: '实践能力', key: '实践能力' },
  { name: '兴趣发展', key: '兴趣发展' },
]

const option = computed(() => {
  void themeKey.value
  const accent = readCSSVar('--accent')
  const accentRGB = readCSSVar('--accent-rgb')
  const textMuted = readCSSVar('--text-muted')
  const data = props.data || {}
  const values = INDICATORS.map((i) => (typeof data[i.key] === 'number' ? data[i.key] : 0))
  return {
    tooltip: {},
    radar: {
      indicator: INDICATORS.map((i) => ({ name: i.name, max: 100 })),
      shape: 'circle',
      center: ['50%', '50%'],
      radius: '62%',
      splitArea: { areaStyle: { color: [`rgba(${accentRGB},0.02)`, `rgba(${accentRGB},0.06)`] } },
      axisLine: { lineStyle: { color: `rgba(${accentRGB},0.25)` } },
      axisName: { color: textMuted, fontSize: 12 },
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 8,
        data: [
          {
            value: values,
            name: '成长画像',
            areaStyle: { color: 'rgba(52,211,153,0.25)' },
            lineStyle: { color: accent, width: 2 },
            itemStyle: { color: accent },
            emphasis: { itemStyle: { color: accent, shadowBlur: 8, shadowColor: 'rgba(52,211,153,0.5)' } },
          },
        ],
      },
    ],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})
</script>
