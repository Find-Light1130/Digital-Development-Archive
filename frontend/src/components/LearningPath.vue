<template>
  <div class="glass-card chart-card lp-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M4 19V5m0 14h16M6 14l3-3 2 2 4-5 3 3" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      AI 个性化学习路径
      <div class="lp-actions">
        <span v-if="plan" class="lp-week">{{ plan.week_label }}</span>
        <el-button v-if="canGenerate" size="small" :loading="generating" @click="generate">重新生成</el-button>
      </div>
    </div>

    <div v-if="loading" class="lp-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else-if="plan">
      <div class="lp-progress">
        <div class="lp-bar"><i :style="{ width: progress.percent + '%' }"></i></div>
        <span class="lp-percent">已完成 {{ progress.done }}/{{ progress.total }}（{{ progress.percent }}%）</span>
      </div>

      <div class="lp-goals">
        <span v-for="(g, i) in plan.goals" :key="i" class="goal-chip">{{ g }}</span>
      </div>

      <div class="lp-items">
        <div v-for="(it, i) in plan.items" :key="it.key" class="lp-item" :class="{ done: it.done }">
          <button class="check" :class="{ checked: it.done }" @click="toggle(it)">
            <span v-if="it.done">✓</span>
          </button>
          <div class="lp-item-main">
            <div class="lp-item-task">{{ it.task }}</div>
            <div class="lp-item-meta"><span class="subj-tag">{{ it.subject }}</span>约 {{ it.minutes }} 分钟</div>
          </div>
        </div>
      </div>

      <div v-if="plan.mental_risk" class="lp-mental">
        已为你加入心理调节任务：保持心情稳定也是学习的一部分。
      </div>
    </template>

    <EmptyState v-else-if="error" icon="clock" title="暂无学习计划" :hint="error" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getLearningPath, generateLearningPath, toggleLearningItem } from '../utils/api'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
  canGenerate: { type: Boolean, default: true },
})

const plan = ref(null)
const loading = ref(false)
const generating = ref(false)
const error = ref('')

const progress = computed(() => {
  const items = plan.value?.items || []
  const total = items.length
  const done = items.filter((i) => i.done).length
  return { total, done, percent: total ? Math.round((done / total) * 100) : 0 }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getLearningPath(props.studentId)
    plan.value = data
  } catch (e) {
    error.value = e?.response?.status === 404 ? '暂无成绩数据，无法生成计划' : '加载失败'
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  try {
    const { data } = await generateLearningPath(props.studentId)
    plan.value = data
    ElMessage.success('已根据最新成绩重新生成计划')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

async function toggle(it) {
  if (!plan.value?.id) return
  const next = !it.done
  it.done = next
  try {
    const { data } = await toggleLearningItem(plan.value.id, it.key, next)
    plan.value = data
  } catch (e) {
    it.done = !next
  }
}

load()
defineExpose({ load })
</script>

<style scoped>
.lp-card .card-header { flex-wrap: wrap; gap: 8px; }
.lp-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.lp-week { font-size: 12px; color: var(--text-label); }
.lp-loading { padding: 8px 2px; }
.lp-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.lp-bar { flex: 1; height: 8px; background: var(--glass-border); border-radius: 4px; overflow: hidden; }
.lp-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--success)); border-radius: 4px; transition: width 0.4s; }
.lp-percent { font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.lp-goals { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.goal-chip { font-size: 12px; color: var(--warning); border: 1px solid var(--warning); border-radius: 999px; padding: 2px 10px; background: rgba(251, 191, 36, 0.08); }
.lp-items { display: flex; flex-direction: column; gap: 6px; }
.lp-item { display: flex; gap: 10px; align-items: flex-start; padding: 8px 10px; border: 1px solid var(--glass-border); border-radius: 10px; background: var(--glass-bg); }
.lp-item.done { opacity: 0.55; }
.lp-item.done .lp-item-task { text-decoration: line-through; }
.check { width: 20px; height: 20px; min-width: 20px; border-radius: 50%; border: 1.5px solid var(--glass-border); background: transparent; color: #fff; font-size: 12px; cursor: pointer; margin-top: 2px; }
.check.checked { background: var(--success); border-color: var(--success); }
.lp-item-task { font-size: 13px; color: var(--text-primary); line-height: 1.6; }
.lp-item-meta { display: flex; align-items: center; gap: 8px; margin-top: 3px; }
.subj-tag { font-size: 11px; color: var(--accent); border: 1px solid var(--accent); border-radius: 999px; padding: 0 8px; }
.lp-item-meta { font-size: 11px; color: var(--text-label); }
.lp-mental { margin-top: 12px; font-size: 12px; color: var(--success); background: rgba(52, 211, 153, 0.08); border: 1px dashed var(--success); border-radius: 8px; padding: 8px 12px; }
</style>
