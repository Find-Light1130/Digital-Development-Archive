<template>
  <div class="intervention-panel">
    <div class="ip-head">
      <span class="ip-title">干预记录 · {{ studentName }}</span>
      <el-button type="primary" size="small" :loading="creating" @click="create">AI 生成干预方案</el-button>
    </div>

    <div v-if="loading" class="ip-loading"><el-skeleton :rows="3" animated /></div>

    <div v-else-if="!list.length" class="ip-empty">暂无干预记录</div>

    <div v-for="it in list" :key="it.id" class="ip-item" :class="it.status">
      <div class="ip-item-head">
        <span class="ip-badge" :class="it.level">{{ it.level === 'red' ? '红' : '黄' }}</span>
        <span class="ip-name">{{ it.title }}</span>
        <span class="ip-status">{{ statusText(it.status) }}</span>
      </div>
      <div class="ip-plan">{{ it.plan_text }}</div>
      <div v-if="it.milestones.length" class="ip-milestones">
        <span v-for="(m, i) in it.milestones" :key="i" class="mile">{{ m }}</span>
      </div>
      <div class="ip-effect">
        <span>基线指数 <b>{{ it.baseline_index }}</b></span>
        <span>当前指数 <b>{{ it.current_index ?? '—' }}</b></span>
        <span v-if="it.effect != null" class="delta" :class="it.effect >= 0 ? 'good' : 'bad'">
          效果 {{ it.effect >= 0 ? '+' : '' }}{{ it.effect }}
        </span>
        <el-button v-if="it.status === 'open'" size="small" type="primary" plain @click="openFollow(it)">跟进</el-button>
        <el-button v-if="it.status !== 'closed'" size="small" type="danger" plain @click="close(it)">关闭并评估效果</el-button>
      </div>
      <div v-if="it.follow_notes.length" class="ip-notes">
        <div v-for="(n, i) in it.follow_notes" :key="i" class="note">• {{ n.time?.slice(0, 16) }} {{ n.note }}</div>
      </div>
    </div>

    <el-dialog v-model="followOpen" title="记录跟进" width="420px" append-to-body>
      <el-input v-model="followText" type="textarea" :rows="3" placeholder="记录本次跟进情况…" />
      <template #footer>
        <el-button @click="followOpen = false">取消</el-button>
        <el-button type="primary" @click="doFollow">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getInterventions, createIntervention, followIntervention, closeIntervention } from '../utils/api'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
  studentName: { type: String, default: '' },
})

const list = ref([])
const loading = ref(false)
const creating = ref(false)
const followOpen = ref(false)
const followText = ref('')
const followId = ref(null)

function statusText(s) {
  return { open: '待执行', in_progress: '进行中', closed: '已闭环' }[s] || s
}

async function load() {
  loading.value = true
  try {
    const { data } = await getInterventions(props.studentId)
    list.value = data
  } catch (e) {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function create() {
  creating.value = true
  try {
    const { data } = await createIntervention(props.studentId)
    list.value.unshift(data)
    ElMessage.success('已生成干预方案')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '该学生暂无明确预警信号')
  } finally {
    creating.value = false
  }
}

function openFollow(it) {
  followId.value = it.id
  followText.value = ''
  followOpen.value = true
}

async function doFollow() {
  await followIntervention(followId.value, followText.value)
  followOpen.value = false
  ElMessage.success('已记录')
  load()
}

async function close(it) {
  try {
    const { data } = await closeIntervention(it.id)
    ElMessage.success('已闭环，效果 ' + (data.effect ?? '—'))
    load()
  } catch (e) {
    ElMessage.error('关闭失败')
  }
}

load()
defineExpose({ load })
</script>

<style scoped>
.ip-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.ip-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.ip-loading, .ip-empty { padding: 12px 0; color: var(--text-label); font-size: 13px; }
.ip-item { border: 1px solid var(--glass-border); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: var(--glass-bg); }
.ip-item-head { display: flex; align-items: center; gap: 8px; }
.ip-badge { width: 20px; height: 20px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; }
.ip-badge.red { background: var(--danger); }
.ip-badge.yellow { background: var(--warning); }
.ip-name { font-weight: 600; color: var(--text-primary); font-size: 13px; }
.ip-status { margin-left: auto; font-size: 11px; padding: 1px 8px; border-radius: 999px; background: var(--glass-border); color: var(--text-muted); }
.ip-item.closed .ip-status { color: var(--success); }
.ip-plan { font-size: 12px; color: var(--text-secondary); line-height: 1.8; margin: 8px 0; }
.ip-milestones { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.mile { font-size: 11px; color: var(--text-muted); background: var(--glass-border); border-radius: 999px; padding: 2px 8px; }
.ip-effect { display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--text-muted); }
.ip-effect b { color: var(--text-primary); }
.delta.good { color: var(--success); }
.delta.bad { color: var(--danger); }
.ip-notes { margin-top: 8px; border-top: 1px dashed var(--glass-border); padding-top: 6px; }
.note { font-size: 12px; color: var(--text-muted); line-height: 1.7; }
</style>
