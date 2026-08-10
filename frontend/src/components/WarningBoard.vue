<template>
  <div class="glass-card chart-card warning-board">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M12 4l8 15H4l8-15z" stroke="var(--warning)" stroke-width="1.5" fill="none" stroke-linejoin="round"/>
        <path d="M12 10v4M12 16.5v.5" stroke="var(--warning)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      AI 预警 · 干预工作台
      <div class="filter-tabs">
        <button v-for="f in filters" :key="f.value" class="filter-tab" :class="{ active: level === f.value }" @click="level = f.value">
          {{ f.label }}<span v-if="f.value && counts[f.value]">({{ counts[f.value] }})</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="wb-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else>
      <div v-if="!rows.length" class="wb-empty">当前范围内没有{{ level === 'all' ? '高' : '' }}风险学生</div>
      <div v-else class="wb-table">
        <div v-for="r in rows" :key="r.student_id" class="wb-row">
          <span class="wb-badge" :class="r.risk_level">{{ r.risk_level === 'red' ? '红' : '黄' }}</span>
          <div class="wb-main">
            <div class="wb-top">
              <span class="wb-name" @click="openDetail(r.student_id)">{{ r.name }}</span>
              <span class="wb-class">{{ r.class_name }}</span>
              <span class="wb-score">风险 {{ r.risk_score }}</span>
              <div class="wb-actions">
                <el-button size="small" @click="openIntervention(r)">干预</el-button>
                <el-button size="small" type="primary" plain @click="openDetail(r.student_id)">详情</el-button>
              </div>
            </div>
            <div class="wb-warnings">
              <span v-for="(w, i) in r.warnings.slice(0, 3)" :key="i" class="warn-chip">{{ w.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <el-dialog v-model="ivOpen" :title="'干预工作台 · ' + (curStudent?.name || '')" width="680px" append-to-body>
      <InterventionPanel v-if="ivOpen" :student-id="curStudent?.student_id" :student-name="curStudent?.name" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getWarningBoard } from '../utils/api'
import InterventionPanel from './InterventionPanel.vue'

const props = defineProps({
  className: { type: String, default: null },
  grade: { type: String, default: null },
})

const router = useRouter()
const rows = ref([])
const loading = ref(false)
const level = ref('all')
const ivOpen = ref(false)
const curStudent = ref(null)

const filters = [
  { label: '全部', value: 'all' },
  { label: '红色预警', value: 'red' },
  { label: '黄色预警', value: 'yellow' },
]

const counts = computed(() => {
  const c = { red: 0, yellow: 0 }
  for (const r of rows.value) if (c[r.risk_level] != null) c[r.risk_level]++
  return c
})

const filtered = computed(() => {
  if (level.value === 'all') return rows.value
  return rows.value.filter((r) => r.risk_level === level.value)
})

async function load() {
  loading.value = true
  try {
    const { data } = await getWarningBoard({ className: props.className, grade: props.grade })
    rows.value = data
  } catch (e) {
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(() => [props.className, props.grade], load, { immediate: true })

function openIntervention(r) {
  curStudent.value = r
  ivOpen.value = true
}

function openDetail(id) {
  router.push({ path: `/teacher/student/${id}`, query: { class: props.className } })
}
</script>

<style scoped>
.warning-board .card-header { flex-wrap: wrap; gap: 8px; }
.filter-tabs { display: flex; gap: 6px; margin-left: auto; }
.filter-tab { border: 1px solid var(--glass-border); background: transparent; color: var(--text-muted); font-size: 12px; border-radius: 999px; padding: 3px 12px; cursor: pointer; }
.filter-tab.active { color: var(--warning); border-color: var(--warning); }
.wb-loading { padding: 8px 2px; }
.wb-empty { color: var(--text-label); font-size: 13px; padding: 16px 0; text-align: center; }
.wb-row { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px dashed var(--glass-border); }
.wb-row:last-child { border: none; }
.wb-badge { width: 22px; height: 22px; min-width: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; margin-top: 2px; }
.wb-badge.red { background: var(--danger); }
.wb-badge.yellow { background: var(--warning); }
.wb-main { flex: 1; min-width: 0; }
.wb-top { display: flex; align-items: center; gap: 10px; }
.wb-name { font-weight: 600; color: var(--text-primary); cursor: pointer; }
.wb-name:hover { color: var(--accent); }
.wb-class { font-size: 12px; color: var(--text-label); }
.wb-score { font-size: 12px; color: var(--warning); }
.wb-actions { margin-left: auto; display: flex; gap: 6px; }
.wb-warnings { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.warn-chip { font-size: 11px; color: var(--text-muted); background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 999px; padding: 2px 8px; }
@media (max-width: 720px) { .wb-top { flex-wrap: wrap; } .wb-actions { margin-left: 0; } }
</style>
