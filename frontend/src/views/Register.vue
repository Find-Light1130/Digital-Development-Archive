<template>
  <div class="reg-page">
    <div class="reg-card glass-card" v-reveal="{ direction: 'up', delay: 0 }">
      <!-- 表单 -->
      <div class="form-panel">
        <h1 class="form-title">创建账号</h1>
        <p class="form-sub">填写信息，选择账号类型</p>

        <form class="auth-form" @submit.prevent="onSubmit">
          <label class="field" v-reveal="{ direction: 'up', delay: 40 }">
            <span class="field-label">用户名</span>
            <el-input v-model="form.username" class="glass-input" placeholder="2-20 位字母 / 数字 / 下划线 / 中文" size="large"
                      autocomplete="username" />
          </label>

          <label class="field" v-reveal="{ direction: 'up', delay: 80 }">
            <span class="field-label">昵称（选填）</span>
            <el-input v-model="form.name" class="glass-input" placeholder="展示用昵称，默认同用户名" size="large" />
          </label>

          <label class="field" v-reveal="{ direction: 'up', delay: 120 }">
            <span class="field-label">账号类型</span>
            <div class="role-pills">
              <button v-for="r in roleOptions" :key="r.value" type="button"
                      :class="['pill', { active: form.role === r.value }]"
                      :style="form.role === r.value ? { background: r.color, borderColor: r.color } : {}"
                      @click="form.role = r.value">
                {{ r.label }}
              </button>
            </div>
          </label>

          <div class="two-col" v-reveal="{ direction: 'up', delay: 160 }">
            <label class="field">
              <span class="field-label">密码</span>
              <el-input v-model="form.password" class="glass-input" type="password" show-password
                        placeholder="至少 8 位，含字母和数字" size="large" autocomplete="new-password" @input="onPwdInput" />
              <div class="strength" v-if="form.password">
                <div class="strength-bars">
                  <span v-for="i in 3" :key="i" :class="['bar', { on: strengthLevel >= i }]" :style="{ background: strengthColor }"></span>
                </div>
                <span class="strength-label" :style="{ color: strengthColor }">{{ strengthText }}</span>
              </div>
            </label>
            <label class="field">
              <span class="field-label">确认密码</span>
              <el-input v-model="form.confirm" class="glass-input" type="password" show-password
                        placeholder="再次输入密码" size="large" autocomplete="new-password" />
            </label>
          </div>

          <label class="field" v-if="form.role === 'student'" v-reveal="{ direction: 'up', delay: 200 }">
            <span class="field-label">学生证号<span class="req">*</span></span>
            <el-input v-model="form.studentId" class="glass-input" placeholder="实名绑定，请输入真实学生证号" size="large"
                      :maxlength="10" @input="form.studentId = form.studentId.replace(/\D/g, '')" />
          </label>

          <p class="pwd-rules">
            密码需 <b>至少 8 位</b>，且 <b>同时包含字母和数字</b>。
          </p>

          <p v-if="error" class="form-error">{{ error }}</p>

          <el-button class="btn-primary submit-btn" native-type="submit" :loading="loading" size="large">
            <span class="submit-text">提交注册</span>
            <span class="submit-arrow">→</span>
          </el-button>
        </form>

        <p class="form-switch">
          已有账号？
          <router-link to="/login" class="switch-link">去登录</router-link>
        </p>
      </div>

      <!-- 成长蓝图：横向三步 + 流动光束 -->
      <aside class="blueprint-side">
        <div class="bp-inner">
          <div class="bp-head">
            <span class="bp-tag">三步开启</span>
            <h2>你的成长之旅</h2>
            <p>从注册到使用，始终在途</p>
          </div>

          <div class="track">
            <div class="track-line" aria-hidden="true">
              <span class="track-fill seg-1"></span>
              <span class="track-fill seg-2"></span>
            </div>
            <div class="node" v-for="s in steps" :key="s.n">
              <span class="node-dot">{{ s.n }}</span>
              <span class="node-label">{{ s.title }}</span>
              <span class="node-desc">{{ s.desc }}</span>
            </div>
          </div>

          <div class="perks">
            <div class="perk" v-for="p in perks" :key="p.label">
              <span class="perk-mark"></span>
              <span>{{ p.label }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerAccount } from '../utils/api'

const router = useRouter()
const form = reactive({ username: '', name: '', role: 'student', password: '', confirm: '', studentId: '' })
const loading = ref(false)
const error = ref('')
const strengthLevel = ref(0)
const strengthColor = ref('var(--danger)')
const strengthText = ref('')

const roleOptions = [
  { value: 'student', label: '学生', color: '#34d399' },
  { value: 'teacher', label: '教师', color: '#60a5fa' },
  { value: 'admin', label: '管理员', color: '#fbbf24' },
]

const steps = [
  { n: '1', title: '填写资料', desc: '用户名与实名信息' },
  { n: '2', title: '等待审核', desc: '管理员审核身份' },
  { n: '3', title: '开始使用', desc: '进入专属工作台' },
]

const perks = [
  { label: '加盐加密' },
  { label: '实名绑定' },
  { label: '多角色审核' },
]

function onPwdInput() {
  const pwd = form.password
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Za-z]/.test(pwd) && /\d/.test(pwd)) score++
  if (pwd.length >= 12 || (/[A-Za-z]/.test(pwd) && /\d/.test(pwd) && /[^A-Za-z0-9]/.test(pwd))) score++
  strengthLevel.value = score
  const [c, t] = [
    ['var(--danger)', '强度弱，请包含字母和数字'],
    ['var(--warning)', '强度中等，可继续加强'],
    ['var(--level-1)', '强度较强'],
  ][Math.max(0, score - 1)] || ['var(--text-label)', '']
  strengthColor.value = c
  strengthText.value = t
}

async function onSubmit() {
  error.value = ''
  if (!form.username.trim()) { error.value = '请输入用户名'; return }
  if (form.password.length < 8) { error.value = '密码至少 8 位'; return }
  if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) { error.value = '密码需同时包含字母和数字'; return }
  if (form.password !== form.confirm) { error.value = '两次输入的密码不一致'; return }
  if (form.role === 'student' && !form.studentId.trim()) { error.value = '请填写学生证号'; return }
  loading.value = true
  try {
    const res = await registerAccount({
      username: form.username.trim(),
      name: form.name.trim(),
      role: form.role,
      password: form.password,
      student_id: form.role === 'student' ? Number(form.studentId) : undefined,
    })
    ElMessage.success(res.data.message || '注册成功')
    router.replace('/login')
  } catch (e) {
    error.value = e?.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reg-page {
  min-height: calc(100vh - 130px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 12px;
}
.reg-card {
  width: 100%;
  max-width: 960px;
  display: grid;
  grid-template-columns: 1.1fr 0.95fr;
  overflow: hidden;
  border-radius: 24px;
}

/* --- 表单 --- */
.form-panel { padding: 44px 42px; display: flex; flex-direction: column; justify-content: center; }
.form-title { font-size: 28px; font-weight: 800; color: var(--text-primary); }
.form-sub { margin-top: 8px; color: var(--text-muted); font-size: 14px; }
.auth-form { margin-top: 24px; display: flex; flex-direction: column; gap: 16px; }
.field-label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.req { color: var(--danger); margin-left: 2px; }
.strength { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.strength-bars { display: flex; gap: 4px; flex: 1; }
.strength-bars .bar { height: 4px; flex: 1; border-radius: 3px; background: var(--glass-border); transition: background 0.25s ease; }
.strength-label { font-size: 11px; white-space: nowrap; }
.pwd-rules { font-size: 12px; color: var(--text-label); margin-top: -6px; line-height: 1.6; }
.pwd-rules b { color: var(--text-muted); font-weight: 600; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.role-pills { display: flex; gap: 8px; }
.pill {
  font-size: 13px; padding: 7px 18px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-secondary); cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: #fff; font-weight: 600; }
.submit-btn {
  width: 100%; height: 48px; font-size: 15px; margin-top: 6px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  border-radius: 14px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
}
.submit-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 28px var(--btn-primary-shadow-hover); }
.submit-arrow { display: inline-block; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); font-weight: 700; }
.submit-btn:hover .submit-arrow { transform: translateX(5px); }
.form-error { color: var(--danger); font-size: 13px; margin-top: -6px; }
.form-switch { margin-top: 20px; text-align: center; color: var(--text-label); font-size: 13px; }
.switch-link { color: var(--accent); font-weight: 600; text-decoration: none; }
.switch-link:hover { text-decoration: underline; }

/* --- 成长蓝图：横向三步 --- */
.blueprint-side {
  position: relative; overflow: hidden;
  padding: 44px 36px;
  display: flex; align-items: center;
  background: linear-gradient(160deg, rgba(96, 165, 250, 0.05), rgba(var(--accent-rgb), 0.07) 55%, rgba(var(--accent-rgb), 0.02));
}
.blueprint-side::before {
  content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(42% 30% at 18% 18%, rgba(96, 165, 250, 0.22), transparent 70%),
    radial-gradient(46% 32% at 78% 22%, rgba(var(--accent-rgb), 0.2), transparent 70%),
    radial-gradient(38% 30% at 60% 78%, rgba(139, 92, 246, 0.14), transparent 70%),
    radial-gradient(30% 24% at 28% 88%, rgba(var(--accent-rgb), 0.14), transparent 70%);
  filter: blur(6px);
  animation: haloDrift 9s ease-in-out infinite alternate;
}
@keyframes haloDrift {
  0% { transform: translate3d(-1.5%, -1%, 0) scale(1); }
  100% { transform: translate3d(1.5%, 1.2%, 0) scale(1.06); }
}
.bp-inner { position: relative; z-index: 1; width: 100%; }
.bp-tag {
  display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: 2px;
  color: var(--accent); padding: 4px 12px; border-radius: 10px;
  background: rgba(var(--accent-rgb), 0.12); border: 1px solid rgba(var(--accent-rgb), 0.25);
}
.bp-head h2 { margin-top: 14px; font-size: 24px; font-weight: 800; color: var(--text-primary); }
.bp-head p { margin-top: 6px; font-size: 13px; color: var(--text-muted); }

.track {
  position: relative;
  margin-top: 40px;
  display: flex;
  align-items: flex-start;
}
.node { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 2; }
.node-dot {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700;
  color: var(--text-secondary);
  background: var(--glass-solid);
  border: 1.5px solid rgba(var(--accent-rgb), 0.3);
  box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.06);
}
.node-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.node-desc { font-size: 11px; color: var(--text-label); }

.track-line {
  position: absolute; left: 16.66%; right: 16.66%; top: 16px; height: 2px;
  background: rgba(var(--accent-rgb), 0.14);
  border-radius: 2px;
  overflow: hidden;
}
.track-fill {
  position: absolute; top: 0; height: 100%; width: 50%;
  background: linear-gradient(90deg, rgba(var(--accent-rgb), 0.75), var(--accent));
  box-shadow: 0 0 10px 1px rgba(var(--accent-rgb), 0.55);
  transform-origin: left center;
}
.seg-1 { left: 0; animation: seg1Fill 5s ease-in-out infinite; }
.seg-2 { left: 50%; animation: seg2Fill 5s ease-in-out infinite; }

@keyframes seg1Fill {
  0% { transform: scaleX(0); opacity: 0; }
  4% { opacity: 1; }
  20% { transform: scaleX(1); }
  26% { opacity: 1; }
  32% { opacity: 0; }
  100% { opacity: 0; }
}
@keyframes seg2Fill {
  0%, 46% { transform: scaleX(0); opacity: 0; }
  50% { opacity: 1; }
  67% { transform: scaleX(1); }
  73% { opacity: 1; }
  78% { opacity: 0; }
  100% { opacity: 0; }
}

.perks { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 44px; }
.perk {
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; color: var(--text-secondary);
  padding: 7px 14px; border-radius: 12px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
  transition: border-color 0.25s ease, color 0.25s ease;
}
.perk:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--text-primary); }
.perk-mark {
  width: 6px; height: 6px; border-radius: 2px;
  background: var(--accent); transform: rotate(45deg);
}

@media (max-width: 760px) {
  .reg-card { grid-template-columns: 1fr; }
  .blueprint-side { display: none; }
  .form-panel { padding: 32px 22px; }
  .two-col { grid-template-columns: 1fr; }
}
</style>
