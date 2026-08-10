import { createApp } from 'vue'
import 'element-plus/es/components/message/style/css'
import App from './App.vue'
import router from './router'
import vSnap from './utils/snap'
import vReveal from './utils/reveal'

const savedTheme = localStorage.getItem('theme')
const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches
const effectiveLight = savedTheme === 'light' || (savedTheme !== 'dark' && prefersLight)
document.documentElement.setAttribute('data-theme', effectiveLight ? 'light' : '')

const app = createApp(App)
app.use(router)
app.directive('snap', vSnap)
app.directive('reveal', vReveal)
app.mount('#app')
