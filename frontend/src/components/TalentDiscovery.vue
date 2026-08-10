<template>
  <div class="glass-card chart-card talent-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <circle cx="12" cy="12" r="9" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
        <path d="M8 12l2.5 2.5L16 9.5" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      AI 综合素质·特长发现
    </div>

    <div v-if="loading" class="talent-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else-if="data">
      <div class="ai-summary">{{ data.summary }}</div>

      <div class="talent-grid" v-if="data.talents.length">
        <div v-for="t in data.talents" :key="t.direction" class="talent-item">
          <div class="talent-head">
            <span class="talent-name">{{ t.direction }}</span>
            <span class="talent-level" :class="t.level === '明显' ? 'strong' : ''">{{ t.level }}</span>
          </div>
          <div class="talent-basis">{{ t.basis }}</div>
          <ul class="talent-sugg">
            <li v-for="(s, i) in t.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>

      <div v-else class="empty-line">暂未识别出明显特长方向，多尝试社团与课外活动吧。</div>

      <div v-if="Object.keys(data.quality).length" class="quality-line">
        <span v-for="(v, k) in data.quality" :key="k" class="q-chip">{{ k }} {{ v }}</span>
      </div>

      <div v-if="data.awards.length" class="award-line">
        <span class="award-title">最近荣誉：</span>
        <span v-for="a in data.awards" :key="a.date + a.title" class="award-chip">{{ a.level }}·{{ a.title }}</span>
      </div>
    </template>

    <EmptyState v-else-if="error" icon="data" title="加载失败" :hint="error" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getTalent } from '../utils/api'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
})

const data = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await getTalent(props.studentId)
    data.value = d
  } catch (e) {
    error.value = e?.response?.status === 404 ? '该学生不存在' : '加载失败'
  } finally {
    loading.value = false
  }
}

load()
defineExpose({ load })
</script>

<style scoped>
.talent-loading { padding: 8px 2px; }
.ai-summary { font-size: 13px; line-height: 1.9; color: var(--text-secondary); background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; }
.talent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.talent-item { border: 1px solid var(--glass-border); border-radius: 10px; padding: 10px 12px; background: var(--glass-bg); }
.talent-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.talent-name { font-weight: 700; color: var(--text-primary); font-size: 14px; }
.talent-level { font-size: 11px; color: var(--text-muted); border: 1px solid var(--glass-border); padding: 1px 8px; border-radius: 999px; }
.talent-level.strong { color: var(--warning); border-color: var(--warning); }
.talent-basis { font-size: 12px; color: var(--text-muted); line-height: 1.6; }
.talent-sugg { margin: 8px 0 0; padding-left: 16px; }
.talent-sugg li { font-size: 12px; color: var(--text-secondary); line-height: 1.8; }
.empty-line { color: var(--text-label); font-size: 13px; padding: 8px 0; }
.quality-line { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.q-chip { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); }
.award-line { margin-top: 10px; font-size: 12px; color: var(--text-muted); }
.award-chip { margin-right: 8px; color: var(--accent); }
</style>
