<template>
  <div class="app-container">
    <Starfield />
    <header class="app-header">
      <div class="header-inner">
        <router-link to="/" class="logo-area">
          <svg viewBox="0 0 28 28" width="24" height="24">
            <rect x="3" y="15" width="5" height="10" rx="1.5" fill="var(--accent)" opacity="0.85"/>
            <rect x="11.5" y="7" width="5" height="18" rx="1.5" fill="var(--accent)" opacity="0.65"/>
            <rect x="20" y="3" width="5" height="22" rx="1.5" fill="var(--accent)" opacity="0.45"/>
          </svg>
          <span class="logo-text">AI数字智育系统</span>
          <span class="logo-badge">v1.0</span>
        </router-link>
        <nav class="nav-links" v-if="loggedIn">
          <router-link v-if="user && user.role === 'student'" to="/student" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>学生端
          </router-link>
          <router-link v-if="user && user.role === 'teacher'" to="/teacher" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>教师端
          </router-link>
          <router-link v-if="user && user.role === 'grade_leader'" to="/grade-leader" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>年级工作台
          </router-link>
          <router-link v-if="user && user.role === 'grade_leader'" to="/grade-leader/review" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>教师审核
          </router-link>
          <template v-if="user && user.role === 'admin'">
            <router-link to="/admin" class="nav-link" active-class="nav-active">
              <span class="nav-indicator"></span>管理端
            </router-link>
            <router-link to="/admin/review" class="nav-link" active-class="nav-active">
              <span class="nav-indicator"></span>用户审核
            </router-link>
          </template>
          <router-link to="/help" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>帮助中心
          </router-link>
        </nav>
        <nav class="nav-links" v-else>
          <router-link to="/" class="nav-link" active-class="nav-active" exact>
            <span class="nav-indicator"></span>首页
          </router-link>
          <router-link to="/login" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>登录
          </router-link>
          <router-link to="/register" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>注册
          </router-link>
          <router-link to="/help" class="nav-link" active-class="nav-active">
            <span class="nav-indicator"></span>帮助中心
          </router-link>
        </nav>
        <span style="flex:1"></span>
        <el-dropdown v-if="loggedIn && user" trigger="click" class="user-menu" @command="onUserCommand">
          <div class="user-chip">
            <span class="user-name">{{ user.name || user.username }}</span>
            <span class="user-role" :class="`role-${user.role}`">{{ roleLabel }}</span>
            <svg class="chip-caret" viewBox="0 0 24 24" width="12" height="12">
              <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button class="theme-toggle" :class="{ 'is-light': !isDark }" @click="cycleTheme" :title="themeTitle" aria-label="切换主题">
          <span class="theme-icon-wrap">
            <svg class="theme-icon sun" viewBox="0 0 24 24" width="18" height="18">
              <circle cx="12" cy="12" r="5" fill="none" stroke="var(--text-muted)" stroke-width="1.5"/>
              <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke="var(--text-muted)" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <svg class="theme-icon moon" viewBox="0 0 24 24" width="18" height="18">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="none" stroke="var(--text-muted)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
      </div>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade">
          <component :is="Component" :key="$route.path" />
        </transition>
      </router-view>
    </main><button class="back-top" :class="{ show: showBackTop }" @click="scrollToTop" title="回到顶部" aria-label="回到顶部">
      <svg viewBox="0 0 24 24" width="20" height="20">
        <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <transition name="veil-fade">
      <div v-if="loggingOut" class="logout-veil" aria-hidden="true">
        <div class="logout-inner">
          <div class="logout-mark">
            <svg viewBox="0 0 28 28" width="26" height="26">
              <rect x="3" y="15" width="5" height="10" rx="1.5" fill="var(--accent)" opacity="0.85"/>
              <rect x="11.5" y="7" width="5" height="18" rx="1.5" fill="var(--accent)" opacity="0.65"/>
              <rect x="20" y="3" width="5" height="22" rx="1.5" fill="var(--accent)" opacity="0.45"/>
            </svg>
          </div>
          <span class="logout-text">已退出登录</span>
        </div>
      </div>
    </transition>

    <el-dialog v-model="pwdVisible" title="修改密码" width="420px" class="pwd-dialog" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent="submitPassword">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old" class="glass-input" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.next" class="glass-input" type="password" show-password placeholder="至少 8 位，含字母和数字" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm" class="glass-input" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <p v-if="pwdError" class="pwd-error">{{ pwdError }}</p>
      </el-form>
      <template #footer>
        <el-button class="btn-secondary" @click="pwdVisible = false">取消</el-button>
        <el-button class="btn-primary" :loading="pwdLoading" @click="submitPassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { themeKey } from './utils/colors'
import { isLoggedIn, getStoredUser, clearAuth } from './utils/auth'
import { logoutAccount, changePassword } from './utils/api'
import { ElMessage } from 'element-plus'
import Starfield from './components/Starfield.vue'

const route = useRoute()
const router = useRouter()
const THEME_MODES = ['auto', 'dark', 'light']
const isDark = ref(true)
const themeMode = ref('auto')
const showBackTop = ref(false)
const loggedIn = ref(false)
const user = ref(null)
const loggingOut = ref(false)
const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdError = ref('')
const pwdForm = ref({ old: '', next: '', confirm: '' })
let mq = null

const roleLabel = computed(() => {
  const labels = { student: '学生', teacher: '教师', grade_leader: '年级组长', admin: '管理员' }
  return labels[user.value?.role] || ''
})

function refreshAuth() {
  loggedIn.value = isLoggedIn()
  user.value = getStoredUser()
}

watch(() => route.fullPath, refreshAuth)

watch(() => route.query.auto, (val) => {
  if (val === '1') {
    ElMessage.success('您已登录，已自动跳转到工作台')
    const q = { ...route.query }
    delete q.auto
    router.replace({ path: route.path, query: q })
  }
})

async function doLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try { await logoutAccount() } catch { /* ignore */ }
  clearAuth()
  refreshAuth()
  if (route.path !== '/') {
    router.push('/')
  }
  setTimeout(() => {
    loggingOut.value = false
  }, 720)
}

function onUserCommand(command) {
  if (command === 'logout') doLogout()
  else if (command === 'password') {
    pwdForm.value = { old: '', next: '', confirm: '' }
    pwdError.value = ''
    pwdVisible.value = true
  }
}

async function submitPassword() {
  pwdError.value = ''
  const { old: oldPwd, next, confirm } = pwdForm.value
  if (!oldPwd) { pwdError.value = '请输入原密码'; return }
  if (!next) { pwdError.value = '请输入新密码'; return }
  if (next.length < 8 || !/[A-Za-z]/.test(next) || !/\d/.test(next)) {
    pwdError.value = '新密码需至少 8 位且同时包含字母和数字'
    return
  }
  if (next !== confirm) { pwdError.value = '两次输入的新密码不一致'; return }
  pwdLoading.value = true
  try {
    await changePassword(oldPwd, next)
    pwdVisible.value = false
    ElMessage.success('密码已修改，请重新登录')
    clearAuth()
    refreshAuth()
    router.push('/login')
  } catch (e) {
    pwdError.value = e?.response?.data?.detail || '修改失败，请检查原密码'
  } finally {
    pwdLoading.value = false
  }
}

function onScroll() {
  showBackTop.value = window.scrollY > 400
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function applyTheme(light) {
  isDark.value = !light
  document.documentElement.setAttribute('data-theme', light ? 'light' : '')
}

function resolveMode() {
  if (themeMode.value === 'auto') {
    applyTheme(mq ? mq.matches : false)
  } else {
    applyTheme(themeMode.value === 'light')
  }
}

const themeTitle = computed(() => ({
  auto: '跟随系统（点击切换）',
  dark: '暗色模式（点击切换）',
  light: '亮色模式（点击切换）',
}[themeMode.value]))

function cycleTheme() {
  const idx = THEME_MODES.indexOf(themeMode.value)
  themeMode.value = THEME_MODES[(idx + 1) % THEME_MODES.length]
  localStorage.setItem('theme', themeMode.value)
  resolveMode()
  themeKey.value++
}

function onMqChange() {
  if (themeMode.value !== 'auto') return
  applyTheme(mq.matches)
  themeKey.value++
}

onMounted(() => {
  refreshAuth()
  const saved = localStorage.getItem('theme')
  if (saved === 'light' || saved === 'dark' || saved === 'auto') {
    themeMode.value = saved
  } else {
    themeMode.value = 'auto'
  }
  mq = window.matchMedia('(prefers-color-scheme: light)')
  mq.addEventListener('change', onMqChange)
  resolveMode()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onBeforeUnmount(() => {
  if (mq) mq.removeEventListener('change', onMqChange)
  window.removeEventListener('scroll', onScroll)
})
</script>

<style>
:root {
  --bg-1: #0b1416;
  --bg-2: #13211e;
  --bg-3: #0e171a;
  --text-primary: #f2f5f9;
  --text-secondary: #dde4ec;
  --text-muted: #a3b1c1;
  --text-label: #7d8b9b;
  --text-label-light: #8d9bab;
  --accent: #34d399;
  --accent-rgb: 52, 211, 153;
  --level-1: #34d399;
  --level-2: #60a5fa;
  --level-3: #fbbf24;
  --level-4: #f87171;
  --success: #34d399;
  --info: #60a5fa;
  --danger: #f87171;
  --card-pad: 20px;
  --card-radius: 16px;
  --header-bg: rgba(0,0,0,0.38);
  --glass-bg: rgba(255,255,255,0.04);
  --glass-bg-hover: rgba(255,255,255,0.06);
  --glass-border: rgba(255,255,255,0.06);
  --glass-border-hover: rgba(255,255,255,0.1);
  --glass-solid: rgba(15,20,22,0.92);
  --glass-solid-95: rgba(15,20,22,0.95);
  --header-border: rgba(255,255,255,0.06);
  --shadow: 0 4px 24px rgba(0,0,0,0.2), 0 1px 4px rgba(0,0,0,0.1);
  --shadow-hover: 0 8px 40px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.15);
  --border-light: rgba(255,255,255,0.08);
  --skeleton-color: rgba(255,255,255,0.04);
  --skeleton-to-color: rgba(255,255,255,0.08);
  --btn-primary-bg: linear-gradient(135deg, #059669, #10b981);
  --btn-primary-shadow: rgba(5,150,105,0.25);
  --btn-primary-shadow-hover: rgba(5,150,105,0.4);
  --warning: #e6a23c;
  --warning-rgb: 230, 162, 60;
  --tag-final: #f87171;
  --tag-midterm: #fbbf24;
  --tag-final-bg: rgba(248,113,113,0.25);
  --tag-midterm-bg: rgba(251,191,36,0.25);
  --pill-active-text: #fff;
  --header-shadow: 0 1px 20px rgba(0,0,0,0.3);
  --glass-bg-solid: #213131; /* blurred bg behind glass card, so glass-bg over it = #2a3939 */
  --dropdown-item-hover-bg: linear-gradient(135deg, #240E40, #241E41);
  --dropdown-focus-border: #241E41;
  --el-text-color-primary: #f2f5f9;
  --el-text-color-regular: #dde4ec;
  --el-text-color-secondary: #a3b1c1;
  --el-text-color-placeholder: #7d8b9b;
  --el-text-color-disabled: #6b7d8d;
  --el-bg-color-overlay: #15201f;
  --el-bg-color: #0f1819;
  --el-fill-color-blank: #0f1819;
  --el-fill-color: #15201f;
  --el-fill-color-light: #1a2a29;
  --el-fill-color-lighter: #203432;
  --el-fill-color-extra-light: #1c2c2b;
  --el-border-color: #2c403e;
  --el-border-color-light: #263936;
  --el-border-color-lighter: #223330;
  --el-border-color-extra-light: #1d2c2a;
  --el-disabled-bg-color: #1a2423;
  --el-datepicker-active-color: #34d399;
  --el-datepicker-hover-text-color: #34d399;
  --el-datepicker-selected-bg-color: rgba(52,211,153,0.25);
  --el-datepicker-inrange-bg-color: rgba(52,211,153,0.18);
  --el-datepicker-inrange-hover-bg-color: rgba(52,211,153,0.25);
  --el-datepicker-header-border-color: #223330;
  --el-datepicker-border-color: #223330;
  --el-color-primary: #34d399;
  --el-color-primary-light-3: #5edcb0;
  --el-color-primary-light-5: #86e6c3;
  --el-color-primary-light-7: #aef0d6;
  --el-color-primary-light-8: #c3f4e0;
  --el-color-primary-light-9: #e3faf1;
  --el-color-primary-dark-2: #2aae7e;
  --el-color-success: #34d399;
  --el-color-success-light-3: #5edcb0;
  --el-color-success-light-5: #86e6c3;
  --el-color-success-light-7: #aef0d6;
  --el-color-success-light-8: #c3f4e0;
  --el-color-success-light-9: #e3faf1;
  --el-color-success-dark-2: #2aae7e;
  --el-color-error: #f87171;
  --el-color-error-light-3: #fa9c9c;
  --el-color-error-light-5: #fcc0c0;
  --el-color-error-light-7: #fde4e4;
  --el-color-error-light-8: #feeded;
  --el-color-error-light-9: #fef7f7;
  --el-color-error-dark-2: #c94f4f;
  --el-color-warning: #fbbf24;
  --el-color-warning-light-3: #fcd366;
  --el-color-warning-light-5: #fde298;
  --el-color-warning-light-7: #fef0ca;
  --el-color-warning-light-8: #fef6dd;
  --el-color-warning-light-9: #fffbea;
  --el-color-warning-dark-2: #d18f10;
  --el-color-info: #60a5fa;
  --el-color-info-light-3: #8fc0fb;
  --el-color-info-light-5: #b6d6fd;
  --el-color-info-light-7: #dcebfe;
  --el-color-info-light-8: #eaf2fe;
  --el-color-info-light-9: #f3f8ff;
  --el-color-info-dark-2: #3d7fd4;
}

:root[data-theme="light"] {
  --bg-1: #d7dde4;
  --bg-2: #cdd5de;
  --bg-3: #dde3ea;
  --text-primary: #1a202c;
  --text-secondary: #2d3748;
  --text-muted: #718096;
  --text-label: #7a8a9a;
  --text-label-light: #8a9aaa;
  --accent: #059669;
  --accent-rgb: 5, 150, 105;
  --level-1: #059669;
  --level-2: #2563eb;
  --level-3: #d97706;
  --level-4: #dc2626;
  --success: #059669;
  --info: #2563eb;
  --danger: #dc2626;
  --card-pad: 20px;
  --card-radius: 16px;
  --header-bg: rgba(215,221,228,0.82);
  --glass-bg: rgba(215,221,228,0.66);
  --glass-bg-hover: rgba(215,221,228,0.82);
  --glass-border: rgba(0,0,0,0.09);
  --glass-border-hover: rgba(0,0,0,0.16);
  --glass-solid: rgba(215,221,228,0.92);
  --glass-solid-95: rgba(215,221,228,0.95);
  --header-border: rgba(0,0,0,0.06);
  --shadow: 0 2px 20px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04);
  --shadow-hover: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.07);
  --border-light: rgba(0,0,0,0.09);
  --skeleton-color: rgba(0,0,0,0.07);
  --skeleton-to-color: rgba(0,0,0,0.11);
  --btn-primary-bg: linear-gradient(135deg, #059669, #10b981);
  --btn-primary-shadow: rgba(5,150,105,0.25);
  --btn-primary-shadow-hover: rgba(5,150,105,0.4);
  --warning: #d97706;
  --warning-rgb: 217, 119, 6;
  --tag-final: #dc2626;
  --tag-midterm: #d97706;
  --tag-final-bg: rgba(220,38,38,0.15);
  --tag-midterm-bg: rgba(217,119,6,0.15);
  --pill-active-text: #fff;
  --header-shadow: 0 1px 20px rgba(0,0,0,0.08);
  --glass-bg-solid: #d7dde4;
  --dropdown-item-hover-bg: rgba(0,0,0,0.04);
  --dropdown-focus-border: rgba(0,0,0,0.15);
  --el-text-color-primary: #1a202c;
  --el-text-color-regular: #2d3748;
  --el-text-color-secondary: #718096;
  --el-text-color-placeholder: #a0aec0;
  --el-text-color-disabled: #c0c8d0;
  --el-bg-color-overlay: #ffffff;
  --el-bg-color: #ffffff;
  --el-fill-color-blank: #ffffff;
  --el-fill-color: #f5f7fa;
  --el-fill-color-light: #f0f2f5;
  --el-fill-color-lighter: #e9edf2;
  --el-fill-color-extra-light: #edf0f3;
  --el-border-color: #dcdfe6;
  --el-border-color-light: #e4e7ed;
  --el-border-color-lighter: #ebeef5;
  --el-border-color-extra-light: #f2f4f7;
  --el-disabled-bg-color: #f5f7fa;
  --el-datepicker-active-color: #059669;
  --el-datepicker-hover-text-color: #059669;
  --el-datepicker-selected-bg-color: rgba(5,150,105,0.15);
  --el-datepicker-inrange-bg-color: rgba(5,150,105,0.12);
  --el-datepicker-inrange-hover-bg-color: rgba(5,150,105,0.18);
  --el-datepicker-header-border-color: #ebeef5;
  --el-datepicker-border-color: #ebeef5;
  --el-color-primary: #059669;
  --el-color-primary-light-3: #4db18a;
  --el-color-primary-light-5: #7cc5a6;
  --el-color-primary-light-7: #aadbc6;
  --el-color-primary-light-8: #c3e6d6;
  --el-color-primary-light-9: #e3f4ec;
  --el-color-primary-dark-2: #047e56;
  --el-color-success: #059669;
  --el-color-success-light-3: #4db18a;
  --el-color-success-light-5: #7cc5a6;
  --el-color-success-light-7: #aadbc6;
  --el-color-success-light-8: #c3e6d6;
  --el-color-success-light-9: #e3f4ec;
  --el-color-success-dark-2: #047e56;
  --el-color-error: #dc2626;
  --el-color-error-light-3: #e66363;
  --el-color-error-light-5: #ee9191;
  --el-color-error-light-7: #f5bfbf;
  --el-color-error-light-8: #f8d5d5;
  --el-color-error-light-9: #fbebeb;
  --el-color-error-dark-2: #b31e1e;
  --el-color-warning: #d97706;
  --el-color-warning-light-3: #e59b4d;
  --el-color-warning-light-5: #eeb97d;
  --el-color-warning-light-7: #f6d6ad;
  --el-color-warning-light-8: #f9e3c6;
  --el-color-warning-light-9: #fcf1e3;
  --el-color-warning-dark-2: #b05f05;
  --el-color-info: #2563eb;
  --el-color-info-light-3: #5b8bf1;
  --el-color-info-light-5: #8aaef5;
  --el-color-info-light-7: #b9d1fa;
  --el-color-info-light-8: #cfe0fc;
  --el-color-info-light-9: #e6eefe;
  --el-color-info-dark-2: #1e4ebc;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background: linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 40%, var(--bg-3) 100%);
  min-height: 100vh;
  color: var(--text-primary);
  transition: background 0.4s ease, color 0.4s ease;
}

body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 256px 256px;
}

.app-container { min-height: 100vh; display: flex; flex-direction: column; }

.app-header {
  position: sticky; top: 0; z-index: 100;
  background: var(--header-bg);
  backdrop-filter: blur(28px) saturate(1.6);
  -webkit-backdrop-filter: blur(28px) saturate(1.6);
  border-bottom: 1px solid var(--header-border);
  box-shadow: var(--header-shadow);
  transition: background 0.4s ease, border-color 0.4s ease;
}

.header-inner {
  max-width: 1240px; margin: 0 auto;
  display: flex; align-items: center; height: 60px; padding: 0 24px;
}

.logo-area { display: flex; align-items: center; gap: 10px; margin-right: 48px; text-decoration: none; }
.logo-text { font-size: 19px; font-weight: 700; background: linear-gradient(135deg, var(--accent), #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.logo-badge { font-size: 10px; font-weight: 600; color: var(--bg-1); background: linear-gradient(135deg, var(--accent), #60a5fa); padding: 1px 7px; border-radius: 8px; }
.nav-links { display: flex; gap: 4px; }
.nav-link { position: relative; display: flex; align-items: center; gap: 6px; padding: 0 18px; height: 42px; line-height: 42px; font-size: 14px; font-weight: 500; color: var(--text-muted); text-decoration: none; border-radius: 10px; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); }
.nav-link:hover { color: var(--accent); background: rgba(var(--accent-rgb), 0.08); }
.nav-active { color: var(--accent) !important; background: rgba(var(--accent-rgb), 0.12) !important; font-weight: 600; }
.nav-indicator { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.5; }

.user-menu { margin-right: 6px; }
.user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px; border-radius: 11px;
  border: 1px solid var(--glass-border); background: var(--glass-bg);
  cursor: pointer; transition: border-color 0.25s ease, background 0.25s ease;
}
.user-chip:hover { border-color: rgba(var(--accent-rgb), 0.4); background: rgba(var(--accent-rgb), 0.06); }
.chip-caret { color: var(--text-label); transition: transform 0.25s ease; }
.user-menu:hover .chip-caret { transform: translateY(2px); }
.user-name { font-size: 13px; font-weight: 600; color: var(--text-primary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-role { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.user-role.role-student { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.user-role.role-teacher { color: #60a5fa; background: rgba(96, 165, 250, 0.15); }
.user-role.role-grade_leader { color: #a78bfa; background: rgba(167, 139, 250, 0.15); }
.user-role.role-admin { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
@keyframes logout-spin { to { transform: rotate(360deg); } }

.pwd-dialog :deep(.el-dialog__title) { color: var(--text-primary); font-weight: 700; }
.pwd-error { margin: 0 0 4px; font-size: 13px; color: var(--danger); }

.logout-veil {
  position: fixed; inset: 0; z-index: 300;
  display: flex; align-items: center; justify-content: center;
  background: rgba(5, 9, 11, 0.82);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  pointer-events: none;
}
.logout-inner {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  animation: logout-rise 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}
@keyframes logout-rise {
  from { opacity: 0; transform: translateY(12px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.logout-mark {
  width: 58px; height: 58px; border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--accent), #60a5fa);
  box-shadow: 0 8px 30px var(--btn-primary-shadow), 0 0 0 8px rgba(var(--accent-rgb), 0.12);
  animation: logout-breathe 1.2s ease-in-out infinite;
}
@keyframes logout-breathe {
  0%, 100% { transform: scale(1); box-shadow: 0 8px 30px var(--btn-primary-shadow), 0 0 0 6px rgba(var(--accent-rgb), 0.1); }
  50% { transform: scale(1.06); box-shadow: 0 10px 36px var(--btn-primary-shadow-hover), 0 0 0 12px rgba(var(--accent-rgb), 0.16); }
}
.logout-text { color: var(--text-secondary); font-size: 14px; letter-spacing: 3px; }

.veil-fade-enter-active, .veil-fade-leave-active { transition: opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.veil-fade-enter-from, .veil-fade-leave-to { opacity: 0; }

.theme-toggle {
  width: 36px; height: 36px; border-radius: 10px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.theme-toggle:hover { background: var(--glass-bg-hover); border-color: var(--glass-border-hover); }

.theme-icon-wrap { position: relative; width: 18px; height: 18px; }
.theme-icon { position: absolute; inset: 0; transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
.theme-icon.sun { opacity: 1; transform: scale(1) rotate(0deg); }
.theme-icon.moon { opacity: 0; transform: scale(0.3) rotate(90deg); }
.is-light .sun { opacity: 0; transform: scale(0.3) rotate(-90deg); }
.is-light .moon { opacity: 1; transform: scale(1) rotate(0deg); }

.app-main { flex: 1; padding: 28px 24px; max-width: 1260px; width: 100%; margin: 0 auto; position: relative; z-index: 1; }

@media (max-width: 768px) {
  .header-inner { height: 52px; padding: 0 12px; gap: 4px; }
  .logo-area { margin-right: 8px; gap: 6px; }
  .logo-text { font-size: 15px; }
  .logo-badge { display: none; }
  .nav-links { gap: 0; flex: 1; }
  .nav-link { padding: 0 10px; font-size: 13px; height: 38px; line-height: 38px; }
  .user-name { display: none; }
  .user-role { display: none; }
  .app-main { padding: 16px 12px; }
}
@media (max-width: 480px) {
  .logo-text { font-size: 13px; }
  .nav-link { padding: 0 6px; font-size: 12px; }
  .header-inner { padding: 0 8px; }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from { opacity: 0; transform: translateY(6px); }
.fade-leave-to { opacity: 0; transform: translateY(-4px); }

.rise-enter-active { transition: opacity 0.45s cubic-bezier(0.22, 0.61, 0.36, 1), transform 0.45s cubic-bezier(0.22, 0.61, 0.36, 1); }
.rise-enter-from { opacity: 0; transform: translateY(14px); }

@keyframes rise-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.content-wrap, .profile-wrap { display: flex; flex-direction: column; gap: 16px; }

.content-wrap > *,
.profile-wrap > * {
  animation: rise-in 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}
.content-wrap > *:nth-child(1), .profile-wrap > *:nth-child(1) { animation-delay: 0ms; }
.content-wrap > *:nth-child(2), .profile-wrap > *:nth-child(2) { animation-delay: 50ms; }
.content-wrap > *:nth-child(3), .profile-wrap > *:nth-child(3) { animation-delay: 100ms; }
.content-wrap > *:nth-child(4), .profile-wrap > *:nth-child(4) { animation-delay: 150ms; }
.content-wrap > *:nth-child(5), .profile-wrap > *:nth-child(5) { animation-delay: 200ms; }
.content-wrap > *:nth-child(6), .profile-wrap > *:nth-child(6) { animation-delay: 250ms; }
.content-wrap > *:nth-child(7), .profile-wrap > *:nth-child(7) { animation-delay: 300ms; }
.content-wrap > *:nth-child(8), .profile-wrap > *:nth-child(8) { animation-delay: 350ms; }
@media (prefers-reduced-motion: reduce) {
  .rise-enter-active, .fade-enter-active, .fade-leave-active,
  .content-wrap > *, .profile-wrap > * {
    animation: none !important; transition: none !important;
  }
}

.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(28px) saturate(1.5);
  -webkit-backdrop-filter: blur(28px) saturate(1.5);
  border: 1px solid var(--glass-border);
  border-radius: var(--card-radius);
  box-shadow: none;
  transition: all 0.35s cubic-bezier(0.4,0,0.2,1), background 0.4s ease, border-color 0.4s ease;
}
.glass-card:hover { box-shadow: none; background: var(--glass-bg-hover); border-color: var(--glass-border-hover); }

.kpi-value { font-size: 32px; font-weight: 700; background: linear-gradient(135deg, var(--accent), #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.5px; font-variant-numeric: tabular-nums; }
.kpi-label { font-size: 12px; font-weight: 500; color: var(--text-label-light); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }

/* ===== 卡片标题栏（全局基础样式，子组件内 scoped 父样式不生效，需在此兜底） ===== */
.card-header { display: flex; align-items: center; gap: 6px; padding: 10px 0 12px; font-size: 15px; font-weight: 600; color: var(--accent); }

/* tabular-nums for stable numeric columns */
.m-cell, .score-grid td, .el-table .cell, .kpi-card, .stat-value, .count-up { font-variant-numeric: tabular-nums; }
.btn-primary { background: var(--btn-primary-bg) !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important; box-shadow: 0 2px 12px var(--btn-primary-shadow) !important; color: #fff !important; }
.btn-primary:hover { transform: translateY(-1px) scale(1.02) !important; box-shadow: 0 4px 20px var(--btn-primary-shadow-hover) !important; }
.btn-primary:active { transform: translateY(0) scale(0.98) !important; }

.btn-secondary { border-radius: 10px !important; border: 1px solid var(--glass-border) !important; color: var(--text-muted) !important; background: var(--glass-bg) !important; backdrop-filter: blur(8px) !important; font-weight: 500 !important; transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important; }
.btn-secondary:hover { background: var(--glass-bg-hover) !important; color: var(--text-primary) !important; border-color: var(--glass-border-hover) !important; transform: translateY(-1px); }

.glass-input .el-input__wrapper,
.glass-input .el-input__wrapper.is-focus { background: var(--glass-bg) !important; backdrop-filter: blur(8px); border-radius: 10px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.15) !important; border: 1px solid var(--glass-border) !important; transition: all 0.25s; }
.glass-input .el-input__wrapper:hover { border-color: rgba(var(--accent-rgb), 0.3) !important; box-shadow: 0 2px 12px rgba(0,0,0,0.25) !important; }
.glass-input .el-input__inner { color: var(--text-primary) !important; }
.glass-input .el-input__inner::placeholder { color: var(--text-label) !important; }

.glass-select .el-select__wrapper,
.glass-select .el-select__wrapper.is-focused,
.glass-select .el-select__wrapper.is-hovering { background: var(--glass-bg) !important; backdrop-filter: blur(8px); border-radius: 10px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.15) !important; border: 1px solid var(--glass-border) !important; }
.glass-select .el-select__wrapper:hover { border-color: rgba(var(--accent-rgb), 0.3) !important; }
.glass-select .el-select__wrapper.is-focused { border-color: var(--dropdown-focus-border) !important; }
.glass-select .el-select__selected-item { color: var(--text-primary) !important; }

/* ===== 日期选择器 / 数字输入框：与玻璃风格输入框一致，跟随当前颜色模式 ===== */
.el-date-editor .el-input__wrapper,
.el-date-editor.el-input__wrapper,
.el-input-number .el-input__wrapper {
  background: var(--glass-bg) !important;
  backdrop-filter: blur(8px);
  border-radius: 10px !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15) !important;
  border: 1px solid var(--glass-border) !important;
  transition: all 0.25s;
}
.el-date-editor .el-input__wrapper:hover,
.el-input-number .el-input__wrapper:hover { border-color: rgba(var(--accent-rgb), 0.3) !important; box-shadow: 0 2px 12px rgba(0,0,0,0.25) !important; }
.el-date-editor .el-input__wrapper.is-focus { border-color: var(--dropdown-focus-border) !important; }
.el-date-editor .el-input__inner,
.el-input-number .el-input__inner { color: var(--text-primary) !important; }
.el-date-editor .el-input__inner::placeholder,
.el-input-number .el-input__inner::placeholder { color: var(--text-label) !important; }
.el-date-editor .el-input__prefix,
.el-date-editor .el-input__suffix,
.el-date-editor .el-range-separator { color: var(--text-muted) !important; }

.glass-table {
  background: transparent !important;
  --el-table-header-bg-color: transparent !important;
  --el-table-row-hover-bg-color: rgba(var(--accent-rgb), 0.10) !important;
  --el-table-current-row-bg-color: transparent !important;
  --el-table-tr-bg-color: transparent !important;
  --el-table-border-color: transparent !important;
}
.glass-table::before,
.glass-table .el-table__inner-wrapper::after {
  display: none !important;
}
.glass-table .el-table__header-wrapper,
.glass-table .el-table__header-wrapper tr,
.glass-table .el-table__header-wrapper th,
.glass-table .el-table__header-wrapper tr:hover,
.glass-table .el-table__header-wrapper th:hover {
  background: rgba(255,255,255,0.02) !important;
}
[data-theme="light"] .glass-table .el-table__header-wrapper,
[data-theme="light"] .glass-table .el-table__header-wrapper tr,
[data-theme="light"] .glass-table .el-table__header-wrapper th,
[data-theme="light"] .glass-table .el-table__header-wrapper tr:hover,
[data-theme="light"] .glass-table .el-table__header-wrapper th:hover {
  background: rgba(0,0,0,0.02) !important;
}
.glass-table .el-table__header th { color: var(--text-secondary); font-weight: 500; }
.glass-table .el-table__body tr { background: rgba(255,255,255,0.02) !important; transition: all 0.2s; }
[data-theme="light"] .glass-table .el-table__body tr { background: rgba(0,0,0,0.02) !important; }
.glass-table .el-table__body tr.current-row,
.glass-table .el-table__body tr.current-row > td { background: transparent !important; }
.glass-table td { border-bottom-color: var(--glass-border) !important; color: var(--text-secondary) !important; font-weight: 500 !important; transition: background-color 0.2s; }
.glass-table th { border-bottom-color: var(--glass-border) !important; color: var(--text-secondary) !important; font-weight: 500 !important; }
.glass-table .el-table__empty-text { color: var(--text-label) !important; }
.glass-table .el-table__body tr.el-table__row--striped { background: transparent !important; }

.el-dialog {
  background: var(--glass-solid) !important;
  backdrop-filter: blur(32px) saturate(1.5) !important;
  border: 1px solid var(--border-light) !important;
  border-radius: 20px !important;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5) !important;
}
.el-dialog__title { color: var(--text-primary) !important; }
.el-dialog__body { color: var(--text-secondary) !important; }
.el-dialog__headerbtn .el-dialog__close { color: var(--text-label) !important; }
.el-dialog__headerbtn:hover .el-dialog__close { color: var(--text-primary) !important; }

.el-select-dropdown, .el-popper {
  background: var(--glass-solid-95) !important;
  backdrop-filter: blur(28px) saturate(1.5) !important;
  border: 1px solid var(--border-light) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
}
.el-select-dropdown__item { color: var(--text-secondary) !important; }
.el-select-dropdown__item.selected { color: var(--accent) !important; font-weight: 600 !important; background: rgba(var(--accent-rgb), 0.12) !important; }
.el-select-dropdown__item.is-hovering { background: var(--dropdown-item-hover-bg) !important; }
.el-autocomplete-suggestion__item { color: var(--text-secondary) !important; }
.el-autocomplete-suggestion__item.is-hovering,
.el-autocomplete-suggestion__item:hover { background: var(--dropdown-item-hover-bg) !important; }
.sug-id { display: inline-block; width: 46px; color: var(--text-label); font-size: 12px; font-variant-numeric: tabular-nums; }
.sug-name { font-weight: 600; color: var(--text-primary); margin-right: 8px; }
.sug-meta { font-size: 11px; color: var(--text-label); }
.el-popper__arrow::before { background: var(--glass-solid-95) !important; border-color: var(--border-light) !important; }
.el-dropdown-menu__item { color: var(--text-secondary) !important; background: transparent !important; }
.el-dropdown-menu__item:not(.is-disabled):hover { color: var(--accent) !important; background: var(--dropdown-item-hover-bg) !important; }
.el-dropdown-menu__item:not(.is-disabled):focus,
.el-dropdown-menu__item:not(.is-disabled):active { color: var(--accent) !important; background: var(--dropdown-item-hover-bg) !important; }
.el-dropdown-menu {
  background-color: var(--glass-solid-95) !important;
  --el-dropdown-menu-bg-color: var(--glass-solid-95);
  --el-dropdown-menuItem-hover-fill: var(--dropdown-item-hover-bg);
  --el-dropdown-menuItem-hover-color: var(--accent);
  --el-dropdown-menuItem-hover-border-radius: 8px;
}

/* ===== Element Plus 语义组件：主色对齐主题（radio/link/loading/switch 等） ===== */
.el-radio { --el-radio-text-color: var(--text-secondary); }
.el-radio__label { color: var(--text-secondary) !important; }
.el-radio.is-checked .el-radio__label { color: var(--text-primary) !important; }
.el-radio__input.is-checked .el-radio__inner { border-color: var(--accent) !important; background: var(--accent) !important; }
.el-radio__input.is-checked + .el-radio__label { color: var(--accent) !important; }
.el-radio__inner { border-color: var(--glass-border-hover) !important; background: var(--glass-bg) !important; }
.el-radio__input.is-checked .el-radio__inner::after { background: var(--glass-solid-95) !important; }
.el-radio__inner:hover { border-color: var(--accent) !important; }

.el-button.is-link {
  color: var(--accent) !important;
  background: transparent !important;
  border: none !important;
  --el-button-hover-text-color: var(--accent);
  --el-button-active-text-color: var(--accent);
}
.el-button.is-link:hover { color: var(--accent) !important; opacity: 0.82; }

.el-loading-spinner .path { stroke: var(--accent) !important; }
.el-loading-spinner .el-loading-text { color: var(--text-secondary) !important; }

.el-collapse {
  --el-collapse-header-text-color: var(--text-secondary);
  --el-collapse-header-active-color: var(--accent);
  --el-collapse-content-text-color: var(--text-muted);
}
.el-switch { --el-switch-on-color: var(--accent); --el-switch-off-color: var(--glass-border-hover); }
.el-checkbox { --el-checkbox-checked-bg-color: var(--accent); --el-checkbox-checked-input-border-color: var(--accent); }
.el-checkbox__input.is-checked .el-checkbox__inner { background-color: var(--accent) !important; border-color: var(--accent) !important; }
.el-checkbox__input.is-checked + .el-checkbox__label { color: var(--accent) !important; }
.el-checkbox__label { color: var(--text-secondary) !important; }

.el-message {
  background: var(--glass-solid-95) !important;
  border: 1px solid var(--glass-border) !important;
  box-shadow: var(--shadow) !important;
}
.el-message__content { color: var(--text-secondary) !important; }
.el-message .el-message__icon { font-size: 16px; }
.el-notification {
  background: var(--glass-solid-95) !important;
  border: 1px solid var(--glass-border) !important;
  box-shadow: var(--shadow) !important;
}
.el-notification__title { color: var(--text-primary) !important; }
.el-notification__content { color: var(--text-secondary) !important; }
.el-notification__closeBtn { color: var(--text-label) !important; }

/* ===== Element Plus date-picker / time-picker panel surfaces ===== */
.el-picker-panel {
  background: var(--glass-solid-95) !important;
  color: var(--text-secondary) !important;
}
.el-picker-panel__icon-btn { color: var(--text-muted) !important; }
.el-picker-panel__icon-btn:hover { color: var(--accent) !important; }
.el-picker-panel__footer { background: transparent !important; border-top: 1px solid var(--glass-border) !important; }
.el-picker-panel__shortcut { color: var(--text-secondary) !important; }
.el-picker-panel__shortcut:hover { color: var(--accent) !important; }
.el-picker-panel__sidebar { background: transparent !important; border-right: 1px solid var(--glass-border) !important; }
.el-picker-panel__sidebar .el-picker-panel__shortcut.is-selected { color: var(--accent) !important; }
.el-date-table th { color: var(--text-label) !important; }
.el-date-table td { color: var(--text-secondary) !important; }
.el-date-table td.in-range .cell { background-color: var(--el-datepicker-inrange-bg-color) !important; }
.el-date-table td.in-range:hover .cell { background-color: var(--el-datepicker-inrange-hover-bg-color) !important; }
.el-date-table td.today .cell { color: var(--accent) !important; font-weight: 600; }
.el-date-table td.current:not(.disabled) .cell { color: var(--accent) !important; background-color: var(--el-datepicker-selected-bg-color) !important; border-radius: 8px; }
.el-date-table td.available:hover .cell { color: var(--accent) !important; }
.el-date-table td.disabled .cell { color: var(--text-label) !important; opacity: 0.5; }
.el-date-table td.prev-month .cell,
.el-date-table td.next-month .cell { color: var(--text-label-light) !important; opacity: 0.7; }
.el-month-table td .cell, .el-year-table td .cell { color: var(--text-secondary) !important; }
.el-month-table td.in-range .cell, .el-year-table td.in-range .cell { background-color: var(--el-datepicker-inrange-bg-color) !important; }
.el-month-table td.today .cell, .el-year-table td.today .cell { color: var(--accent) !important; }
.el-month-table td.current .cell, .el-year-table td.current .cell { color: var(--accent) !important; background-color: var(--el-datepicker-selected-bg-color) !important; }
.el-month-table td .cell:hover, .el-year-table td .cell:hover { color: var(--accent) !important; }
.el-time-panel { background: var(--glass-solid-95) !important; }
.el-time-spinner__item { color: var(--text-secondary) !important; }
.el-time-spinner__item.active:not(.disabled) { color: var(--accent) !important; }
.el-time-spinner__item:hover:not(.disabled):not(.active) { color: var(--accent) !important; }
.el-time-spinner__arrow { color: var(--text-muted) !important; }
.el-date-range-picker__header,
.el-date-range-picker__content { border-color: var(--glass-border) !important; }

.el-skeleton { --el-skeleton-color: var(--skeleton-color) !important; --el-skeleton-to-color: var(--skeleton-to-color) !important; }

.chart-empty {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-label);
  font-size: 13px;
  letter-spacing: 0.5px;
}

/* ===== v-reveal entrance ===== */
.v-reveal {
  opacity: 0;
  transform: translate3d(var(--reveal-x, 0), var(--reveal-y, 44px), 0);
  transition: opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1), transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: opacity, transform;
}
.v-reveal.is-revealed {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}

/* ===== focus visibility (accessibility) ===== */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}
button:focus:not(:focus-visible),
a:focus:not(:focus-visible) {
  outline: none;
}

/* ===== back to top ===== */
.back-top {
  position: fixed;
  right: 24px;
  bottom: 28px;
  z-index: 100;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-solid);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow);
  opacity: 0;
  pointer-events: none;
  transform: translateY(12px);
  transition: opacity 0.3s, transform 0.3s, background 0.3s, color 0.3s;
}
.back-top.show {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
.back-top:hover {
  background: var(--glass-bg-hover);
  color: var(--accent);
}

/* ===== print ===== */
@media print {
  :root,
  :root[data-theme="light"] {
    --text-primary: #1a202c !important;
    --text-secondary: #2d3748 !important;
    --text-muted: #4a5568 !important;
    --text-label: #718096 !important;
    --accent: #059669 !important;
    --glass-border: rgba(0,0,0,0.14) !important;
    --glass-bg: rgba(0,0,0,0.03) !important;
  }
  body::after { display: none !important; }
  .app-header, .back-top, .theme-toggle, .no-print { display: none !important; }
  .app-container { padding: 0 !important; }
  .app-main { padding: 0 !important; }
  .glass-card {
    background: #fff !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    border: 1px solid #ddd !important;
    box-shadow: none !important;
    break-inside: avoid;
  }
  .kpi-value { -webkit-text-fill-color: #059669 !important; background: none !important; }
  body { background: #fff !important; }
}

@media (prefers-reduced-motion: reduce) {
  .v-reveal { opacity: 1; transform: none; transition: none; }
  * { animation-duration: 0.001s !important; transition-duration: 0.001s !important; }
}
</style>