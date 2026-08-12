<template>
  <div class="dashboard">
    <div class="admin-toolbar no-print">
      <span class="admin-title">用户审核</span>
      <span class="card-hint">新注册账号需审核后可用 · 可分班/创建账号</span>
    </div>

    <div class="glass-card chart-card">
      <div class="card-header">
        <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
          <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.5 0-8 1.8-8 5v2h16v-2c0-3.2-4.5-5-8-5z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linejoin="round"/>
          <circle cx="19" cy="7" r="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
        </svg>
        用户管理
        <span style="flex:1"></span>
        <el-button size="small" class="btn-primary" style="margin-right:8px" @click="openCreate">创建账号</el-button>
        <el-select v-model="userFilter" placeholder="全部状态" size="small" class="glass-select" style="width:120px"
                   @change="loadUsers">
          <el-option label="全部状态" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
      </div>
      <div class="table-scroll" v-snap="{ columns: 'th' }" style="padding:8px 0 0">
        <table class="user-grid">
          <thead>
            <tr>
              <th>用户名</th>
              <th>昵称</th>
              <th>角色</th>
              <th>班级 / 年级</th>
              <th>注册时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.username }}</td>
              <td class="user-cell-dim">{{ u.name || '—' }}</td>
              <td><span class="user-badge" :class="`role-${u.role}`">{{ u.role_label }}</span></td>
              <td class="user-cell-dim">
                <template v-if="u.role === 'teacher'">
                  <template v-if="editingClass === u.id">
                    <el-select v-model="classDraft" size="small" class="glass-select" style="width:110px"
                               placeholder="选择班级" @change="saveClass(u)">
                      <el-option v-for="c in allClassOptions" :key="c" :label="c" :value="c" />
                    </el-select>
                  </template>
                  <template v-else>
                    {{ u.class_name || '未分配' }}
                    <el-button link type="primary" size="small" @click="startEditClass(u)">分班</el-button>
                  </template>
                </template>
                <span v-else-if="u.role === 'grade_leader'">{{ u.grade || '—' }}</span>
                <span v-else>—</span>
              </td>
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
        <div v-if="!users.length" class="no-data">暂无用户</div>
      </div>
    </div>

    <el-dialog v-model="createVisible" title="创建账号" width="460px" class="glass-dialog">
      <div class="create-form">
        <el-form label-width="76px">
          <el-form-item label="账号类型">
            <el-radio-group v-model="createForm.role">
              <el-radio value="teacher">教师</el-radio>
              <el-radio value="grade_leader">年级组长</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="createForm.username" class="glass-input" placeholder="2-20 位字母/数字/下划线/中文" />
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="createForm.name" class="glass-input" placeholder="展示用昵称，默认同用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="createForm.password" class="glass-input" type="password" show-password
                      placeholder="至少 8 位，含字母和数字" />
          </el-form-item>
          <el-form-item v-if="createForm.role === 'teacher'" label="班级">
            <el-select v-model="createForm.class_name" class="glass-select" placeholder="选择班级" style="width:100%">
              <el-option v-for="c in allClassOptions" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="年级">
            <el-select v-model="createForm.grade" class="glass-select" placeholder="选择年级" style="width:100%">
              <el-option v-for="g in ['初一','初二','初三']" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button class="btn-secondary" @click="createVisible = false">取消</el-button>
        <el-button class="btn-primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getUsers, approveUser, rejectUser, setUserClass, adminCreateUser, requestErrorText } from '../utils/api'
import { ElMessage } from 'element-plus'

const users = ref([])
const userFilter = ref('')
const editingClass = ref(null)
const classDraft = ref('')
const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({ role: 'teacher', username: '', name: '', password: '', class_name: '', grade: '' })

const allClassOptions = []
for (let g of ['初一', '初二', '初三']) {
  for (let c = 1; c <= 7; c++) allClassOptions.push(`${g}${c}班`)
}

const STATUS_TEXT = { pending: '待审核', approved: '已通过', rejected: '已驳回' }

function statusText(s) {
  return STATUS_TEXT[s] || s || '—'
}

async function loadUsers() {
  try {
    const res = await getUsers(userFilter.value || undefined)
    users.value = res.data || []
  } catch (e) {
    users.value = []
    ElMessage.error(requestErrorText(e, '暂无用户数据'))
  }
}

function approve(u) {
  approveUser(u.id).then(() => {
    ElMessage.success(`已通过 ${u.username} 的账号`)
    loadUsers()
  }).catch(() => ElMessage.error('操作失败，请重试'))
}

function reject(u) {
  rejectUser(u.id).then(() => {
    ElMessage.success(`已驳回 ${u.username} 的账号`)
    loadUsers()
  }).catch(() => ElMessage.error('操作失败，请重试'))
}

function startEditClass(u) {
  editingClass.value = u.id
  classDraft.value = u.class_name || ''
}

function saveClass(u) {
  const val = classDraft.value
  if (!val) return
  setUserClass(u.id, val).then(() => {
    ElMessage.success(`已将 ${u.username} 分配到 ${val}`)
    editingClass.value = null
    loadUsers()
  }).catch((e) => {
    editingClass.value = null
    ElMessage.error(requestErrorText(e, '设置失败'))
  })
}

function openCreate() {
  createForm.value = { role: 'teacher', username: '', name: '', password: '', class_name: '', grade: '' }
  createVisible.value = true
}

async function doCreate() {
  const f = createForm.value
  if (!f.username.trim()) { ElMessage.warning('请输入用户名'); return }
  if (!f.password || f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) {
    ElMessage.warning('密码需至少 8 位且包含字母和数字')
    return
  }
  if (f.role === 'teacher' && !f.class_name) { ElMessage.warning('请为教师选择班级'); return }
  if (f.role === 'grade_leader' && !f.grade) { ElMessage.warning('请选择年级'); return }
  creating.value = true
  try {
    await adminCreateUser({
      username: f.username.trim(),
      password: f.password,
      role: f.role,
      name: f.name.trim() || undefined,
      class_name: f.role === 'teacher' ? f.class_name : undefined,
      grade: f.role === 'grade_leader' ? f.grade : undefined,
    })
    ElMessage.success('账号创建成功')
    createVisible.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建失败，请重试')
  } finally {
    creating.value = false
  }
}

function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

onMounted(loadUsers)
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.admin-toolbar { display: flex; align-items: center; gap: 12px; }
.admin-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; flex-wrap: wrap; gap: 6px; }
.card-hint { font-size: 12px; color: var(--text-label); font-weight: 400; }
.table-scroll { overflow-x: auto; }
.user-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.user-grid th {
  text-align: left; font-size: 11px; font-weight: 600; color: var(--text-label);
  padding: 6px 12px; border-bottom: 1px solid var(--glass-border);
}
.user-grid td { padding: 10px 12px; color: var(--text-primary); border-bottom: 1px solid var(--glass-border); vertical-align: middle; }
.user-grid tr:last-child td { border-bottom: none; }
.user-cell-dim { color: var(--text-muted); }
.user-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.user-badge.role-student { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.user-badge.role-teacher { color: #60a5fa; background: rgba(96, 165, 250, 0.15); }
.user-badge.role-grade_leader { color: #a78bfa; background: rgba(167, 139, 250, 0.15); }
.user-badge.role-admin { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.create-form { padding-top: 4px; }
.status-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.status-badge.status-pending { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.status-badge.status-approved { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.status-badge.status-rejected { color: #f87171; background: rgba(248, 113, 113, 0.15); }
.no-data { text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px 0; }
</style>