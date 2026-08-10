<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-dust" aria-hidden="true"></div>

      <div class="hero-badge" v-reveal="{ direction: 'up', delay: 0 }">
        <span class="pulse-dot"></span>
        基于 AI 的学生成长数字画像
      </div>

      <h1 class="hero-title" v-reveal="{ direction: 'up', delay: 60 }">
        看见每一次<span class="grad">进步</span>
      </h1>

      <p class="hero-sub" v-reveal="{ direction: 'up', delay: 120 }">
         融合学业成绩、素质评估、情绪与活动足迹，
        <br />为 学生 / 教师 / 年级组长 / 管理员 提供一站式成长洞察。
      </p>

      <div class="hero-cta" v-reveal="{ direction: 'up', delay: 180 }">
        <template v-if="loggedIn">
          <router-link :to="myHome" class="home-btn primary">进入我的工作台 →</router-link>
          <button class="home-btn ghost" @click="doLogout">退出登录</button>
        </template>
        <template v-else>
          <router-link to="/register" class="home-btn primary">立即注册</router-link>
          <router-link to="/login" class="home-btn ghost">已有账号，去登录</router-link>
        </template>
      </div>

      <div class="hero-stats" v-reveal="{ direction: 'up', delay: 240 }">
        <div class="stat" v-for="s in stats" :key="s.label">
          <span class="stat-num"><CountUp :value="s.value" />{{ s.suffix }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Roles -->
    <section class="section">
      <div class="section-head" v-reveal>
        <h2>四大角色，一处洞察</h2>
        <p>按身份进入专属工作台 · 新账号需管理员审核（年级组长由管理员创建）</p>
      </div>
      <div class="role-grid">
        <router-link
          :to="roleLink(r.key)"
          class="role-card glass-card"
          v-for="r in roles"
          :key="r.key"
          v-reveal="{ direction: 'up', delay: 60 }"
        >
          <div class="role-icon" :style="{ background: r.bg }">
            <svg v-html="r.icon" width="23" height="23" viewBox="0 0 24 24" fill="none"></svg>
          </div>
          <div class="role-name">{{ r.name }}</div>
          <p class="role-desc">{{ r.desc }}</p>
          <ul class="role-features">
            <li v-for="f in r.features" :key="f">{{ f }}</li>
          </ul>
          <span class="role-link">{{ r.cta }} <span class="arr">→</span></span>
        </router-link>
      </div>
    </section>

    <!-- Features -->
    <section class="section">
      <div class="section-head" v-reveal>
        <h2>核心能力</h2>
        <p>以数据刻画成长，以 AI 驱动建议</p>
      </div>
      <div class="feature-grid">
        <div class="feature glass-card" v-for="(f, i) in features" :key="f.title" v-reveal="{ direction: 'up', delay: i * 40 }">
          <div class="feature-svg">
            <svg v-html="f.icon" width="22" height="22" viewBox="0 0 24 24" fill="none"></svg>
          </div>
          <div class="feature-title">{{ f.title }}</div>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Tech -->
    <section class="section">
      <div class="section-head" v-reveal>
        <h2>技术底座</h2>
        <p>轻量、现代、可靠的工程</p>
      </div>
      <div class="tech-grid">
        <span class="tech" v-for="t in tech" :key="t.name" v-reveal="{ direction: 'up', delay: 40 }">
          <span class="tech-name">{{ t.name }}</span>
          <span class="tech-role">{{ t.role }}</span>
        </span>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-band glass-card" v-reveal="{ direction: 'up', delay: 60 }">
      <div class="cta-glow" aria-hidden="true"></div>
      <h2>开始你的数字智育之旅</h2>
      <p>注册即开通学生 / 教师账号，年级组长由管理员创建，审核通过后即可使用全部功能。</p>
      <div class="hero-cta cta-center">
        <template v-if="loggedIn">
          <router-link :to="myHome" class="home-btn primary">进入我的工作台 →</router-link>
        </template>
        <template v-else>
          <router-link to="/register" class="home-btn primary">立即注册</router-link>
          <router-link to="/login" class="home-btn ghost">登录系统</router-link>
        </template>
      </div>
    </section>

    <footer class="footer">
      <span>AI数字智育系统 v1.0</span>
      <span class="dot">·</span>
      <span>学生 · 教师 · 年级组长 · 管理员，一站式成长洞察</span>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CountUp from '../components/CountUp.vue'
import { isLoggedIn, getStoredUser, clearAuth } from '../utils/auth'

const loggedIn = computed(() => isLoggedIn())
const user = getStoredUser()
const myHome = computed(() => (user ? { student: '/student', teacher: '/teacher', grade_leader: '/grade-leader', admin: '/admin' }[user.role] || '/' : '/'))

const stats = [
  { value: 1050, suffix: '+', label: '学生样本' },
  { value: 9, suffix: '', label: '大学科' },
  { value: 4, suffix: '', label: '角色工作台' },
  { value: 5, suffix: '', label: '成长维度' },
]

const IC = {
  student: '<path d="M3 9.5l9-4.5 9 4.5-9 4.5-9-4.5z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M7 11.6v3.5c0 1.6 2.2 2.9 5 2.9s5-1.3 5-2.9v-3.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M21 9.6V14" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
  teacher: '<rect x="4" y="4.5" width="16" height="11" rx="2" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M9 18.5h6M12 15.5v3" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/><path d="M7.5 9h5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
  admin: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M9 12l2.2 2.2L15.5 9.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  chart: '<path d="M3.5 17.5l5-6 3.5 3.5 6.5-8" stroke="currentColor" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7h3.5v3.5" stroke="currentColor" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  radar: '<polygon points="12,3 20.5,8 17.3,17.5 6.7,17.5 3.5,8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M12 3v6M20.5 8l-6.5 1M17.3 17.5l-4.3-4.5M6.7 17.5L10 13M3.5 8l6.5 1" stroke="currentColor" stroke-width="1.1" fill="none" stroke-linecap="round"/>',
  bell: '<path d="M6 9.5a6 6 0 0 1 12 0v3.5l1.5 3h-15L6 13V9.5z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M10 19a2.2 2.2 0 0 0 4 0" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
  spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linejoin="round"/><path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2z" stroke="currentColor" stroke-width="1.1" fill="none" stroke-linejoin="round"/>',
  compass: '<circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M15 9l-1.6 4.4L9 15l1.6-4.4L15 9z" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linejoin="round"/>',
  shield: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
}

const roles = [
  {
    key: 'student', icon: IC.student, bg: 'linear-gradient(135deg,#047857,#34d399)', name: '学生端',
    desc: '专属成长档案，看见自己一路的进步与短板。',
    features: ['成长指数 & 五维画像', '九科成绩趋势', '综合素质与活动足迹'],
    cta: '进入学生端',
  },
  {
    key: 'teacher', icon: IC.teacher, bg: 'linear-gradient(135deg,#2563eb,#60a5fa)', name: '教师端',
    desc: '班级学情一览，精准定位薄弱点与异常。',
    features: ['班级均分 / 掌握率', '各科成绩趋势', '分布与预警洞察'],
    cta: '进入教师端',
  },
  {
    key: 'admin', icon: IC.admin, bg: 'linear-gradient(135deg,#b45309,#fbbf24)', name: '管理端',
    desc: '全校数据总览与账号审核管理。',
    features: ['全校成长总览', '年级 / 班级对比', '用户审核管理'],
    cta: '进入管理端',
  },
  {
    key: 'grade_leader', icon: IC.shield, bg: 'linear-gradient(135deg,#6d28d9,#a78bfa)', name: '年级组长',
    desc: '本年级数据总览与教师账号审核。',
    features: ['本年级数据总览', '各班成长对比', '本年级教师审核'],
    cta: '进入年级工作台',
  },
]

const roleLink = (key) => {
  if (loggedIn.value && user && user.role === key) return myHome.value
  return (key === 'admin' || key === 'grade_leader') ? '/login' : '/register'
}

const features = [
  { icon: IC.chart, title: '成长指数', desc: '学业、心理、体育、实践、兴趣五维加权，综合评估成长水平。' },
  { icon: IC.radar, title: 'AI 五维画像', desc: '雷达式呈现各维度强弱，一眼读懂学生综合表现。' },
  { icon: IC.bell, title: '智能预警', desc: '自动识别成绩下滑、情绪波动与出勤异常，及时提醒关注。' },
  { icon: IC.spark, title: '个性化建议', desc: '结合画像与趋势，生成针对性、可执行的学习提升建议。' },
  { icon: IC.compass, title: '成长足迹', desc: '按年级分期的活动与实践总结，还原逐学期成长过程。' },
  { icon: IC.shield, title: '安全管理', desc: '账号审核 + 加盐哈希密码 + 会话令牌，保障数据隐私。' },
]

const tech = [
  { name: 'Vue 3', role: '前端框架' },
  { name: 'FastAPI', role: '后端服务' },
  { name: 'ECharts', role: '数据可视化' },
  { name: 'SQLAlchemy', role: 'ORM' },
  { name: 'SQLite', role: '数据库' },
  { name: 'Element Plus', role: 'UI 组件' },
]

function doLogout() {
  clearAuth()
  window.location.href = '/'
}
</script>

<style scoped>
.home { display: flex; flex-direction: column; gap: 26px; }

/* --- Hero --- */
/* 背景柔光（替代点状尘埃） */
.hero-dust {
  position: absolute; inset: 0; pointer-events: none; z-index: 0; opacity: 0.9;
  background:
    radial-gradient(48% 36% at 50% 10%, rgba(var(--accent-rgb), 0.2), transparent 70%),
    radial-gradient(40% 30% at 22% 22%, rgba(96, 165, 250, 0.17), transparent 70%),
    radial-gradient(40% 28% at 80% 26%, rgba(139, 92, 246, 0.15), transparent 70%),
    radial-gradient(30% 22% at 64% 54%, rgba(var(--accent-rgb), 0.13), transparent 70%),
    radial-gradient(26% 20% at 34% 70%, rgba(96, 165, 250, 0.1), transparent 70%);
  filter: blur(10px);
  animation: heroHalo 9s ease-in-out infinite alternate;
}
@keyframes heroHalo {
  0% { transform: translate3d(-1.2%, -0.6%, 0) scale(1); }
  100% { transform: translate3d(1.2%, 0.8%, 0) scale(1.05); }
}
.hero-title, .hero-sub, .hero-cta, .hero-stats, .hero-badge { position: relative; z-index: 1; }

.hero {
  position: relative;
  overflow: hidden;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 80px 24px 70px;
  border-radius: 28px;
  border: 1px solid rgba(var(--accent-rgb), 0.12);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02), inset 0 -30px 60px rgba(var(--accent-rgb), 0.04);
  background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.05), rgba(96, 165, 250, 0.04) 55%, rgba(var(--accent-rgb), 0.02));
}

.hero-title {
  position: relative;
  font-size: 56px;
  font-weight: 800;
  letter-spacing: 1px;
  line-height: 1.1;
  margin-top: 22px;
  color: var(--text-primary);
}
.grad {
  background: linear-gradient(135deg, var(--accent), #60a5fa, var(--accent), #60a5fa);
  background-size: 250% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradShimmer 8s ease-in-out infinite;
}
@keyframes gradShimmer {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.hero-sub {
  position: relative;
  margin-top: 18px;
  font-size: 16px;
  line-height: 1.9;
  color: var(--text-muted);
}

.hero-cta { position: relative; margin-top: 30px; display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; }
.cta-center { justify-content: center; }
.home-btn {
  padding: 12px 26px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
  font-family: inherit;
}
.home-btn.primary {
  background: var(--btn-primary-bg);
  color: #fff;
  animation: btnBreath 3.4s ease-in-out infinite;
}
.home-btn.primary:hover { transform: translateY(-2px); animation-play-state: paused; box-shadow: 0 8px 30px var(--btn-primary-shadow-hover); }
.home-btn.ghost { background: var(--glass-bg); color: var(--text-secondary); border-color: var(--glass-border); backdrop-filter: blur(8px); }
.home-btn.ghost:hover { color: var(--text-primary); border-color: rgba(var(--accent-rgb), 0.4); transform: translateY(-2px); }
@keyframes btnBreath {
  0%, 100% { box-shadow: 0 4px 18px var(--btn-primary-shadow); }
  50% { box-shadow: 0 6px 30px var(--btn-primary-shadow-hover); }
}

.hero-stats {
  position: relative;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 46px;
}
.stat {
  min-width: 120px;
  padding: 14px 22px;
  border-radius: 16px;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(12px);
}
.stat-num {
  font-size: 30px;
  font-weight: 800;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.stat-label { display: block; margin-top: 2px; font-size: 12px; color: var(--text-label); }

/* Sections */
.section { display: flex; flex-direction: column; gap: 18px; }
.section-head h2 { font-size: 26px; font-weight: 800; color: var(--text-primary); }
.section-head h2::after {
  content: ''; display: block; width: 46px; height: 4px; margin-top: 10px; border-radius: 3px;
  background: linear-gradient(90deg, var(--accent), #60a5fa);
}
.section-head p { margin-top: 6px; color: var(--text-label); font-size: 14px; }

.role-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.role-card {
  padding: 26px; text-decoration: none; display: flex; flex-direction: column; border-radius: 18px;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.35s ease, border-color 0.35s ease;
}
.role-card:hover { transform: translateY(-6px); border-color: rgba(var(--accent-rgb), 0.4); box-shadow: 0 14px 40px rgba(var(--accent-rgb), 0.16); }
.role-icon {
  width: 48px; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
  transition: box-shadow 0.35s ease, background 0.35s ease, filter 0.35s ease;
}
.role-card:hover .role-icon {
  box-shadow: 0 10px 26px rgba(var(--accent-rgb), 0.45), 0 0 0 4px rgba(var(--accent-rgb), 0.14);
  filter: brightness(1.08) saturate(1.1);
}
.role-name { margin-top: 16px; font-size: 20px; font-weight: 700; color: var(--text-primary); transition: color 0.3s; }
.role-card:hover .role-name { color: var(--accent); }
.role-desc { margin-top: 8px; font-size: 13px; line-height: 1.7; color: var(--text-muted); }
.role-features { list-style: none; margin: 14px 0 18px; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.role-features li { font-size: 13px; color: var(--text-secondary); padding-left: 18px; position: relative; }
.role-features li::before {
  content: ''; position: absolute; left: 0; top: 8px; width: 6px; height: 6px;
  border-radius: 2px; background: var(--accent); transform: rotate(45deg);
}
.role-link { margin-top: auto; font-size: 13px; font-weight: 600; color: var(--accent); }
.role-link .arr { display: inline-block; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.role-card:hover .role-link .arr { transform: translateX(4px); }

.feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.feature {
  padding: 24px; border-radius: 18px;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.35s ease, border-color 0.35s ease;
}
.feature:hover { transform: translateY(-4px); border-color: rgba(var(--accent-rgb), 0.35); box-shadow: 0 12px 34px rgba(var(--accent-rgb), 0.13); }
.feature-svg {
  position: relative; overflow: hidden;
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: var(--accent);
  background: rgba(var(--accent-rgb), 0.12);
  border: 1px solid rgba(var(--accent-rgb), 0.25);
  transition: color 0.3s, background 0.3s, border-color 0.3s, box-shadow 0.35s ease;
}
.feature-svg::after {
  content: ''; position: absolute; top: 0; left: 0; width: 60%; height: 100%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  transform: translateX(-160%) skewX(-18deg);
  opacity: 0;
  transition: transform 0.7s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s;
  pointer-events: none;
}
.feature:hover .feature-svg { color: #fff; background: linear-gradient(135deg, var(--accent), #60a5fa); border-color: transparent; box-shadow: 0 8px 22px rgba(var(--accent-rgb), 0.35); }
.feature:hover .feature-svg::after { transform: translateX(340%) skewX(-18deg); opacity: 1; }
.feature-title { margin-top: 16px; font-size: 17px; font-weight: 700; color: var(--text-primary); transition: color 0.3s; }
.feature:hover .feature-title { color: var(--accent); }
.feature-desc { margin-top: 8px; font-size: 13px; line-height: 1.8; color: var(--text-muted); }

.tech-strip { padding: 20px; border-radius: 18px; }
.tech-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
.tech {
  padding: 18px 10px; border-radius: 14px; text-align: center;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
  transition: transform 0.3s ease, border-color 0.3s ease;
}
.tech:hover { transform: translateY(-3px); border-color: rgba(var(--accent-rgb), 0.4); }
.tech-name { display: block; font-size: 15px; font-weight: 700; color: var(--text-primary); }
.tech-role { display: block; margin-top: 4px; font-size: 11px; color: var(--text-muted); }

.cta-band {
  position: relative; overflow: hidden;
  padding: 48px 30px; text-align: center; border-radius: 22px;
  background: linear-gradient(150deg, rgba(var(--accent-rgb), 0.14), rgba(96, 165, 250, 0.10));
}
.cta-band > * { position: relative; z-index: 1; }
@keyframes auraBreathe {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.08); }
}
.cta-glow {
  position: absolute; left: 50%; top: -70%; transform: translateX(-50%);
  width: 560px; height: 560px; border-radius: 50%; pointer-events: none; z-index: 0;
  background: radial-gradient(circle, rgba(var(--accent-rgb), 0.3), rgba(96, 165, 250, 0.16) 45%, transparent 70%);
  filter: blur(24px);
  animation: auraBreathe 7s ease-in-out infinite;
}
.cta-band::after {
  content: ''; position: absolute; left: 12%; right: 12%; bottom: -18px; height: 44px; border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(var(--accent-rgb), 0.22), transparent 70%);
  filter: blur(14px); pointer-events: none;
}
.cta-band h2 { font-size: 24px; font-weight: 800; color: var(--text-primary); }
.cta-band p { margin-top: 10px; color: var(--text-muted); font-size: 14px; }

.footer {
  padding: 18px 4px 8px; text-align: center; display: flex; gap: 10px; justify-content: center;
  font-size: 12px; color: var(--text-label); flex-wrap: wrap;
}
.footer .dot { opacity: 0.5; }

.pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); margin-right: 8px; display: inline-block; box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.5); animation: pulse 1.6s ease-out infinite; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.5); }
  70% { box-shadow: 0 0 0 8px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

@media (max-width: 1024px) {
  .role-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 900px) {
  .feature-grid { grid-template-columns: 1fr 1fr; }
  .tech-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .hero-title { font-size: 36px; }
  .hero { min-height: 460px; padding: 60px 16px; }
  .role-grid, .feature-grid { grid-template-columns: 1fr; }
  .tech-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>