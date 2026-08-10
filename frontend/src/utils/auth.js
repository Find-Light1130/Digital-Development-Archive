const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export const ROLE_HOME = {
  student: '/student',
  teacher: '/teacher',
  grade_leader: '/grade-leader',
  admin: '/admin',
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch (e) {
    return null
  }
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return !!getToken()
}

export const ROLE_LABELS = {
  student: '学生',
  teacher: '教师',
  grade_leader: '年级组长',
  admin: '管理员',
}