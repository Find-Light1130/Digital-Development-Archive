<template>
  <div class="paper-analysis">
    <div v-if="loading" class="pa-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else-if="data">
      <div class="pa-kpis">
        <div class="pa-kpi"><div class="k-label">均分</div><div class="k-value">{{ data.avg }}</div></div>
        <div class="pa-kpi"><div class="k-label">最高/最低</div><div class="k-value small">{{ data.highest }} / {{ data.lowest }}</div></div>
        <div class="pa-kpi"><div class="k-label">及格率</div><div class="k-value">{{ data.pass_rate }}%</div></div>
        <div class="pa-kpi"><div class="k-label">难度</div><div class="k-value small">{{ data.difficulty }} · {{ data.difficulty_label }}</div></div>
        <div class="pa-kpi"><div class="k-label">区分度</div><div class="k-value small">{{ data.discrimination }} · {{ data.discrimination_label }}</div></div>
      </div>

      <div class="pa-buckets">
        <span v-for="(v, k) in data.buckets" :key="k" class="bucket" :class="k">{{ k }} {{ v }}人</span>
      </div>

      <div class="pa-summary">{{ data.summary }}</div>

      <div class="pa-sugg">
        <div class="pa-sub-title">AI 教学解读</div>
        <ul>
          <li v-for="(s, i) in data.teaching_suggestions" :key="i">{{ s }}</li>
        </ul>
      </div>
    </template>

    <EmptyState v-else-if="error" icon="chart" title="暂无分析" :hint="error" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getPaperAnalysis } from '../utils/api'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  planId: { type: [Number, String], required: true },
  className: { type: String, required: true },
})

const data = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  data.value = null
  try {
    const { data: d } = await getPaperAnalysis(props.planId, props.className)
    data.value = d
  } catch (e) {
    error.value = e?.response?.status === 404 ? '该考试本班暂无成绩，请先批阅' : '分析失败'
  } finally {
    loading.value = false
  }
}

load()
watch(() => [props.planId, props.className], load)
defineExpose({ load })
</script>

<style scoped>
.pa-loading { padding: 8px 2px; }
.pa-kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 12px; }
.pa-kpi { text-align: center; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 10px; padding: 8px 4px; }
.k-label { font-size: 11px; color: var(--text-muted); }
.k-value { font-size: 17px; font-weight: 700; color: var(--accent); margin-top: 2px; }
.k-value.small { font-size: 13px; }
.pa-buckets { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.bucket { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); }
.bucket.优秀 { color: var(--success); border-color: var(--success); }
.bucket.良好 { color: var(--accent); border-color: var(--accent); }
.bucket.及格 { color: var(--warning); border-color: var(--warning); }
.bucket.待提高 { color: var(--danger); border-color: var(--danger); }
.pa-summary { font-size: 13px; line-height: 1.9; color: var(--text-secondary); border-left: 3px solid var(--accent); background: var(--glass-bg); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; }
.pa-sub-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.pa-sugg ul { margin: 0; padding-left: 18px; }
.pa-sugg li { font-size: 13px; color: var(--text-secondary); line-height: 1.9; }
@media (max-width: 720px) { .pa-kpis { grid-template-columns: repeat(3, 1fr); } }
</style>
