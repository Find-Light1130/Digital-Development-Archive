<template>
  <div class="dashboard">
    <div class="admin-toolbar no-print">
      <span class="admin-title">本年级教师审核<span v-if="myGrade" class="grade-chip">{{ myGrade }}</span></span>
      <el-button class="btn-secondary" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="glass-card chart-card">
      <div class="card-header">
        <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
          <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.5 0-8 1.8-8 5v2h16v-2c0-3.2-4.5-5-8-5z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linejoin="round"/>
        </svg>
        本年级教师审核
        <span class="card-hint">仅显示本年级教师账号</span>
      </div>
      <div class="table-scroll" style="padding:8px 0 0">
        <table class="user-grid">
          <thead>
            <tr>
              <th>用户名</th>
              <th>昵称</th>
              <th>班级</th>
              <th>注册时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.username }}</td>
              <td class="user-cell-dim">{{ u.name || '—' }}</td>
              <td class="user-cell-dim">{{ u.class_name || '未分配' }}</td>
              <td class="user-cell-dim">{{ formatTime(u.created_at) }}</td>
              <td><span class="status-badge" :class="`status-${u.status}`">{{ statusText(u.status) }}</span></td>
              <td>
                <template v-if="u.status === 'pending'">
                  <el-button size="small" class="btn-primary" style="margin-right:6px" @click="approve(u)">通过</el-button>
                  <el-button size="small" class="btn-secondary" @click="reject(u)">驳回</el-button>
                </template>
                <span v-else class="user-cell-dim">—</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!users.length" class="no-data">暂无教师账号</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getUsers, approveUser, rejectUser, requestErrorText } from '../utils/api'
import { getStoredUser } from '../utils/auth'
import { ElMessage } from 'element-plus'

const myGrade = ref('')
const users = ref([])
const loading = ref(false)

const STATUS_TEXT = { pending: '待审核', approved: '已通过', rejected: '已驳回' }
const statusText = (s) => STATUS_TEXT[s] || s || '—'

function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function load() {
  loading.value = true
  try {
    const res = await getUsers()
    users.value = res.data || []
  } catch (e) {
    users.value = []
    ElMessage.error(requestErrorText(e, '暂无教师账号'))
  } finally {
    loading.value = false
  }
}

function approve(u) {
  approveUser(u.id).then(() => {
    ElMessage.success(`已通过 ${u.username} 的账号`)
    load()
  }).catch((e) => ElMessage.error(e?.response?.data?.detail || '操作失败'))
}

function reject(u) {
  rejectUser(u.id).then(() => {
    ElMessage.success(`已驳回 ${u.username} 的账号`)
    load()
  }).catch((e) => ElMessage.error(e?.response?.data?.detail || '操作失败'))
}

onMounted(() => {
  const u = getStoredUser()
  myGrade.value = u?.grade || ''
  load()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.admin-toolbar { display: flex; align-items: center; gap: 12px; }
.admin-title { font-size: 18px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px; }
.grade-chip {
  font-size: 12px; font-weight: 600; color: #a78bfa;
  background: rgba(167, 139, 250, 0.15); border: 1px solid rgba(167, 139, 250, 0.3);
  padding: 2px 10px; border-radius: 10px;
}
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; flex-wrap: wrap; gap: 6px; }
.card-hint { margin-left: 8px; font-size: 11px; color: var(--text-label); font-weight: 400; }
.table-scroll { overflow-x: auto; }
.user-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-grid th { text-align: left; font-size: 11px; font-weight: 600; color: var(--text-label); padding: 6px 12px; border-bottom: 1px solid var(--glass-border); }
.user-grid td { padding: 10px 12px; color: var(--text-primary); border-bottom: 1px solid var(--glass-border); vertical-align: middle; }
.user-grid tr:last-child td { border-bottom: none; }
.user-cell-dim { color: var(--text-muted); }
.status-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.status-badge.status-pending { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.status-approved { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.status-badge.status-rejected { color: #f87171; background: rgba(248, 113, 113, 0.15); }
.no-data { text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px 0; }
</style>