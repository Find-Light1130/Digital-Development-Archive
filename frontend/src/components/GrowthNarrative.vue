<template>
  <div class="glass-card chart-card narrative-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M5 3v18M5 5h14l-2 4 2 4H5" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      AI 成长档案
    </div>

    <div v-if="loading" class="narr-loading"><el-skeleton :rows="5" animated /></div>

    <template v-else-if="narrative">
      <div class="narr-header">
        <div class="narr-name">{{ narrative.name }}<span class="narr-class">{{ narrative.class_name }}</span></div>
        <div class="narr-index">成长指数 <b>{{ narrative.growth_index }}</b></div>
      </div>
      <div class="narr-body">
        <div v-for="(p, i) in narrative.paragraphs" :key="i" class="narr-para"><MdText :text="p" /></div>
      </div>
      <div class="narr-tags">
        <span v-for="s in narrative.strengths" :key="s" class="narr-tag good">▲ {{ s }}</span>
        <span v-for="s in narrative.weakness" :key="s" class="narr-tag bad">▼ {{ s }}</span>
      </div>
      <div class="narr-foot">— AI 阶段成长小结</div>
    </template>

    <EmptyState v-else-if="error" icon="data" title="档案生成失败" :hint="error" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getGrowthNarrative } from '../utils/api'
import EmptyState from './EmptyState.vue'
import MdText from './MdText.vue'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
})

const narrative = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getGrowthNarrative(props.studentId)
    narrative.value = data
  } catch (e) {
    error.value = e?.response?.status === 404 ? '该学生不存在' : '档案加载失败'
  } finally {
    loading.value = false
  }
}

load()
defineExpose({ load })
</script>

<style scoped>
.narr-loading { padding: 8px 2px; }
.narr-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; flex-wrap: wrap; gap: 6px; }
.narr-name { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.narr-class { font-size: 12px; color: var(--text-label); margin-left: 8px; }
.narr-index { font-size: 13px; color: var(--text-muted); }
.narr-index b { color: var(--accent); font-size: 18px; margin-left: 4px; }
.narr-body { border-left: 2px solid var(--accent); padding-left: 14px; margin: 4px 0 12px; }
.narr-para { font-size: 14px; line-height: 2; color: var(--text-secondary); margin: 0 0 8px; text-indent: 2em; }
.narr-para :deep(.md-body) { font-size: 14px; line-height: 2; color: var(--text-secondary); }
.narr-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.narr-tag { font-size: 12px; padding: 3px 10px; border-radius: 999px; }
.narr-tag.good { background: rgba(52, 211, 153, 0.12); color: var(--success); }
.narr-tag.bad { background: rgba(248, 113, 113, 0.12); color: var(--danger); }
.narr-foot { text-align: right; font-size: 12px; color: var(--text-label); }
</style>
