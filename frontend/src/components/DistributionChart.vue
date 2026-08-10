<template>
  <div class="dist-chart">
    <v-chart v-if="hasData" :option="option" style="height:264px" autoresize @click="onClick" />
    <div v-else class="chart-empty" style="height:264px">暂无数据</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { themeKey, themeTooltip, themePalette, readCSSVar } from '../utils/colors'

const props = defineProps({
  buckets: { type: Array, default: () => [] },
  counts: { type: Array, default: () => [] },
  color: { type: String, default: '' },
  unit: { type: String, default: '人数' },
})

const emit = defineEmits(['bucket-click'])

function onClick(params) {
  if (!params || !params.name) return
  const idx = props.buckets.indexOf(params.name)
  const count = idx >= 0 ? props.counts[idx] : 0
  if (count > 0) emit('bucket-click', params.name)
}

function hexToRgba(hex, alpha) {
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  const n = parseInt(h, 16)
  if (Number.isNaN(n)) return `rgba(52,211,153,${alpha})`
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`
}

const hasData = computed(() =>
  props.buckets.length > 0 && props.counts.some((c) => c > 0)
)

const option = computed(() => {
  void themeKey.value
  const pal = themePalette()
  const tooltipTheme = themeTooltip()
  const color = props.color || readCSSVar('--accent')
  return {
    tooltip: {
      trigger: 'axis', confine: true,
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
      formatter: (p) => {
        const item = p[0]
        if (!item) return ''
        return `${item.name} 区间<br/>${props.unit}: <b>${item.data}</b>`
      },
    },
    grid: { left: 44, right: 14, bottom: 28, top: 18 },
    xAxis: {
      type: 'category',
      data: props.buckets,
      axisLabel: { fontSize: 10, color: pal.axisLabel, interval: 0 },
      axisLine: { lineStyle: { color: pal.axisLine } },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      name: props.unit,
      nameLocation: 'middle',
      nameGap: 42,
      nameTextStyle: { fontSize: 12, color: pal.name },
      axisLabel: { fontSize: 10, color: pal.name },
      splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        data: props.counts,
        barWidth: '55%',
        itemStyle: { color: hexToRgba(color, 0.16), borderRadius: [4, 4, 0, 0] },
        emphasis: { itemStyle: { color: hexToRgba(color, 0.32), shadowBlur: 12, shadowColor: hexToRgba(color, 0.35) } },
        cursor: 'pointer',
      },
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: props.counts,
        lineStyle: { width: 2.5, color },
        itemStyle: { color },
        areaStyle: { color: hexToRgba(color, 0.10) },
        z: 3,
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
.dist-chart { width: 100%; }
</style>