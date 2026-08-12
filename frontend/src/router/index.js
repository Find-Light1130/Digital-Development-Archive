import { createRouter, createWebHashHistory } from 'vue-router'
import { isLoggedIn, getStoredUser, ROLE_HOME } from '../utils/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册' },
  },
  {
    path: '/help',
    name: 'HelpCenter',
    component: () => import('../views/HelpCenter.vue'),
    meta: { title: '帮助中心' },
  },
  {
    path: '/student',
    name: 'Student',
    component: () => import('../views/StudentDashboard.vue'),
    meta: { title: '学生端', requiresAuth: true, roles: ['student'] },
  },
  {
    path: '/teacher',
    name: 'Teacher',
    component: () => import('../views/TeacherDashboard.vue'),
    meta: { title: '教师端', requiresAuth: true, roles: ['teacher', 'grade_leader'] },
  },
  {
    path: '/teacher/student/:id',
    name: 'StudentDetail',
    component: () => import('../views/StudentDetail.vue'),
    meta: { title: '学生详情', requiresAuth: true, roles: ['teacher', 'grade_leader', 'admin'] },
  },
  {
    path: '/grade-leader',
    name: 'GradeLeader',
    component: () => import('../views/GradeLeaderDashboard.vue'),
    meta: { title: '年级组长工作台', requiresAuth: true, roles: ['grade_leader'] },
  },
  {
    path: '/grade-leader/review',
    name: 'GradeLeaderReview',
    component: () => import('../views/GradeLeaderReview.vue'),
    meta: { title: '教师审核', requiresAuth: true, roles: ['grade_leader'] },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminDashboard.vue'),
    meta: { title: '管理端', requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/admin/review',
    name: 'AdminReview',
    component: () => import('../views/AdminReview.vue'),
    meta: { title: '用户审核', requiresAuth: true, roles: ['admin'] },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const loggedIn = isLoggedIn()
  const user = getStoredUser()

  if (to.meta.requiresAuth) {
    if (!loggedIn) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (!user || user.status !== 'approved') {
      clearAuthLocal()
      return { path: '/login', query: { reason: 'approval' } }
    }
    if (to.meta.roles && !to.meta.roles.includes(user.role)) {
      return { path: ROLE_HOME[user.role] || '/', query: { reason: 'role' } }
    }
    return true
  }

  if (to.path === '/' && loggedIn && user && user.status === 'approved') {
    return { path: ROLE_HOME[user.role] || '/', query: { auto: '1' } }
  }

  if ((to.path === '/login' || to.path === '/register') && loggedIn && user) {
    return { path: ROLE_HOME[user.role] || '/' }
  }
  return true
})

function clearAuthLocal() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
}

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · AI数字智育系统` : 'AI数字智育系统'
})

export default router
