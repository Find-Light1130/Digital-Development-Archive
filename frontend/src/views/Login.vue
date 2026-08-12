<template>
  <div class="login-page">
    <div class="login-card glass-card" v-reveal="{ direction: 'up', delay: 0 }">
      <!-- 纯星空尘埃 -->
      <aside class="vis-side">
        <div class="vis-dust" aria-hidden="true"></div>
        <div class="vis-inner">
          <div class="brand-logo">
            <svg viewBox="0 0 28 28" width="34" height="34">
              <rect x="3" y="15" width="5" height="10" rx="1.5" fill="#fff" opacity="0.85"/>
              <rect x="11.5" y="7" width="5" height="18" rx="1.5" fill="#fff" opacity="0.65"/>
              <rect x="20" y="3" width="5" height="22" rx="1.5" fill="#fff" opacity="0.45"/>
            </svg>
          </div>
          <h2 class="vis-title">看见每一次<span class="vis-grad">进步</span></h2>
          <p class="vis-sub">AI 数字智育 · 一站式成长洞察</p>
        </div>
      </aside>

      <!-- 表单 -->
      <div class="form-panel">
        <h1 class="form-title">欢迎回来</h1>
        <p class="form-sub">登录你的工作台，继续成长之旅</p>

        <form class="auth-form" @submit.prevent="onSubmit">
          <label class="field" v-reveal="{ direction: 'up', delay: 40 }">
            <span class="field-label">用户名</span>
            <el-input v-model="form.username" class="glass-input" placeholder="请输入用户名" size="large"
                      autocomplete="username" />
          </label>

          <label class="field" v-reveal="{ direction: 'up', delay: 120 }">
            <span class="field-label">密码</span>
            <el-input v-model="form.password" class="glass-input" type="password" show-password
                      placeholder="请输入密码" size="large" autocomplete="current-password" />
          </label>

          <p v-if="error" class="form-error">{{ error }}</p>

          <el-button class="btn-primary submit-btn btn-shine" native-type="submit" :loading="loading" size="large">
            登 录
          </el-button>
        </form>

        <p class="form-switch">
          还没有账号？
          <router-link to="/register" class="switch-link">立即注册</router-link>
        </p>
        <p class="form-tip">新注册账号需管理员审核后启用</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginAccount } from '../utils/api'
import { setAuth, ROLE_HOME } from '../utils/auth'

const route = useRoute()
const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const submitting = ref(false)

async function onSubmit() {
  if (submitting.value) return
  error.value = ''
  if (!form.username.trim()) { error.value = '请输入用户名'; return }
  if (!form.password) { error.value = '请输入密码'; return }
  loading.value = true
  submitting.value = true
  try {
    const res = await loginAccount({ username: form.username.trim(), password: form.password })
    const { token, user } = res.data
    setAuth(token, user)
    const redirect = route.query.redirect
    if (typeof redirect === 'string' && /^\/[^/]/.test(redirect)) router.replace(redirect)
    else router.replace(ROLE_HOME[user.role] || '/')
  } catch (e) {
    const status = e?.response?.status
    const detail = e?.response?.data?.detail
    if (status === 403) error.value = detail || '账号待审核或未通过'
    else error.value = detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 130px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 12px;
}
.login-card {
  width: 100%;
  max-width: 940px;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  overflow: hidden;
  border-radius: 24px;
}

/* --- 纯星空尘埃 --- */
.vis-side {
  position: relative; overflow: hidden;
  padding: 52px 40px;
  display: flex; align-items: center; justify-content: center;
}
.vis-dust {
  position: absolute; inset: 0; pointer-events: none; opacity: 0.85;
  background:
    radial-gradient(40% 30% at 20% 24%, rgba(96, 165, 250, 0.22), transparent 70%),
    radial-gradient(46% 34% at 76% 30%, rgba(var(--accent-rgb), 0.2), transparent 70%),
    radial-gradient(34% 28% at 56% 78%, rgba(139, 92, 246, 0.16), transparent 70%),
    radial-gradient(28% 22% at 30% 92%, rgba(var(--accent-rgb), 0.16), transparent 70%);
  filter: blur(8px);
  animation: haloDrift 9s ease-in-out infinite alternate;
}
@keyframes haloDrift {
  0% { transform: translate3d(-1.5%, -1%, 0) scale(1); }
  100% { transform: translate3d(1.5%, 1.2%, 0) scale(1.06); }
}
.vis-inner { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; text-align: center; }
.brand-logo {
  width: 62px; height: 62px; border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--accent), #60a5fa);
  box-shadow: 0 8px 26px var(--btn-primary-shadow);
}
.vis-title { margin-top: 26px; font-size: 30px; font-weight: 800; color: var(--text-primary); line-height: 1.3; }
.vis-grad {
  background: linear-gradient(135deg, var(--accent), #60a5fa, var(--accent));
  background-size: 250% 100%;
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  animation: gradShimmer 8s ease-in-out infinite;
}
@keyframes gradShimmer {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.vis-sub { margin-top: 10px; color: var(--text-muted); font-size: 14px; letter-spacing: 1px; }

/* --- 表单 --- */
.form-panel { padding: 48px 42px; display: flex; flex-direction: column; justify-content: center; }
.form-title { font-size: 28px; font-weight: 800; color: var(--text-primary); }
.form-sub { margin-top: 8px; color: var(--text-muted); font-size: 14px; }
.auth-form { margin-top: 28px; display: flex; flex-direction: column; gap: 18px; }
.field-label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.submit-btn { width: 100%; height: 46px; font-size: 15px; margin-top: 6px; }
.form-error { color: var(--danger); font-size: 13px; margin-top: -6px; }
.form-switch { margin-top: 22px; text-align: center; color: var(--text-label); font-size: 13px; }
.switch-link { color: var(--accent); font-weight: 600; text-decoration: none; }
.switch-link:hover { text-decoration: underline; }
.form-tip { margin-top: 10px; text-align: center; color: var(--text-label); font-size: 12px; }

.btn-shine { position: relative; overflow: hidden; }
.btn-shine::after {
  content: ''; position: absolute; top: 0; left: 0; width: 45%; height: 100%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transform: translateX(-160%) skewX(-18deg);
  transition: transform 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}
.btn-shine:hover::after { transform: translateX(360%) skewX(-18deg); }

@media (max-width: 760px) {
  .login-card { grid-template-columns: 1fr; }
  .vis-side { display: none; }
  .form-panel { padding: 36px 24px; }
}
</style>
