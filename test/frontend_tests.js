/**
 * 前端构建冒烟测试
 * 运行：node test/frontend_tests.js
 * 说明：执行 vite build 并校验产物（dist 存在、chunk 拆分、无全量 echarts 引入）。
 */
'use strict'
const { spawnSync } = require('node:child_process')
const { existsSync, readdirSync, readFileSync, statSync } = require('node:fs')
const { join, dirname } = require('node:path')
const zlib = require('node:zlib')

const root = join(__dirname, '..')
const frontend = join(root, 'frontend')
const src = join(frontend, 'src')
const dist = join(frontend, 'dist')

let failures = 0
let passes = 0
function check(name, cond, extra = '') {
  console.log((cond ? '  ok  ' : 'FAIL  ') + name + (cond ? '' : `  [${extra}]`))
  if (cond) passes++
  else failures++
}

console.log('== 构建 ==')
const build = spawnSync('npm run build', {
  cwd: frontend,
  shell: process.platform === 'win32',
  encoding: 'utf-8',
})
check('vite build 退出码为 0', build.status === 0, `status=${build.status}`)
const buildOut = (build.stdout || '') + (build.stderr || '')
check('构建无 error 标记', !/error/i.test(buildOut))

console.log('== 模板编译（dev 编译器） ==')
const sfcCompiler = require(join(frontend, 'node_modules', '@vue/compiler-sfc'))
const vueFiles = []
;(function walk(dir) {
  if (!existsSync(dir)) return
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) walk(p)
    else if (e.name.endsWith('.vue')) vueFiles.push(p)
  }
})(join(src, 'views'))
walk(join(src, 'components'))
let sfcErrors = 0
for (const f of vueFiles) {
  const { descriptor } = sfcCompiler.parse(readFileSync(f, 'utf8'))
  if (!descriptor.template) continue
  const res = sfcCompiler.compileTemplate({ source: descriptor.template.content, filename: f, id: 'smoke' })
  for (const e of res.errors || []) {
    sfcErrors++
    console.log(`  FAIL ${f}: ${e.message}`)
  }
}
check('全部 SFC 模板 dev 编译零错误', sfcErrors === 0, `errors=${sfcErrors}`)

console.log('== script setup 运行时 API 导入 ==')
const RUNTIME_APIS = ['ref', 'computed', 'watch', 'watchEffect', 'reactive', 'shallowRef',
  'toRefs', 'nextTick', 'onMounted', 'onBeforeMount', 'onUpdated', 'onBeforeUpdate',
  'onUnmounted', 'onBeforeUnmount', 'onActivated', 'onDeactivated', 'onErrorCaptured',
  'provide', 'inject']
const COMPILER_MACROS = ['defineProps', 'defineEmits', 'defineExpose', 'withDefaults', 'defineOptions']
let missingImports = 0
for (const f of vueFiles) {
  const content = readFileSync(f, 'utf8')
  const m = content.match(/<script setup>([\s\S]*?)<\/script>/)
  if (!m) continue
  const script = m[1]
  const importMatch = script.match(/import\s*\{([^}]*)\}\s*from\s*'vue'/)
  const imported = new Set(
    (importMatch ? importMatch[1] : '').split(',').map((s) => s.trim().split(/\s+as\s+/)[0]).filter(Boolean)
  )
  for (const api of RUNTIME_APIS) {
    const usage = new RegExp(`(?<![\\w.])${api}\\s*\\(`).test(script)
    if (usage && !imported.has(api)) {
      missingImports++
      console.log(`  FAIL ${f}: 使用 ${api}() 但未从 vue 导入`)
    }
  }
}
check('script setup 无漏导入的 vue API', missingImports === 0, `missing=${missingImports}`)

console.log('== 产物 ==')
const distOk = existsSync(dist) && existsSync(join(dist, 'index.html'))
check('dist/index.html 存在', distOk)
const assetsDir = join(dist, 'assets')
const jsFiles = distOk && existsSync(assetsDir)
  ? readdirSync(assetsDir).filter((f) => f.endsWith('.js'))
  : []
check('assets 下存在 JS 产物', jsFiles.length > 0, `count=${jsFiles.length}`)

const hasEchartsChunk = jsFiles.some((f) => f.startsWith('echarts-'))
check('echarts 独立 vendor chunk', hasEchartsChunk)

let maxJsGzip = 0
let maxFile = ''
for (const f of jsFiles) {
  const content = readFileSync(join(assetsDir, f))
  const gz = zlib.gzipSync(content).length
  if (gz > maxJsGzip) {
    maxJsGzip = gz
    maxFile = f
  }
}
check('最大 JS chunk gzip < 350KB', maxJsGzip < 350 * 1024, `${maxFile}: ${(maxJsGzip / 1024).toFixed(1)}KB`)

console.log('== 源码检查 ==')
function walk(dir, acc = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name)
    if (entry.isDirectory()) walk(p, acc)
    else if (/\.(js|vue)$/.test(entry.name)) acc.push(p)
  }
  return acc
}
const sources = walk(src)
const fullEcharts = sources.filter((f) => /from\s+['"]echarts['"]|\bimport\s+['"]echarts['"]/.test(readFileSync(f, 'utf-8')))
check('无全量 echarts 引入', fullEcharts.length === 0, fullEcharts.join(', '))
const echartsOnDemand = sources.filter((f) => readFileSync(f, 'utf-8').includes("'echarts/core'") || readFileSync(f, 'utf-8').includes('"echarts/core"'))
check('存在 echarts/core 按需注册', echartsOnDemand.length > 0)

const mainJs = read('main.js')
check('main.js 无全量 use(ElementPlus)', !/use\(ElementPlus\)/.test(mainJs))
check('main.js 无全量 element-plus 样式', !/element-plus\/dist\/index\.css/.test(mainJs))
check('vite 配置使用 ElementPlusResolver', /ElementPlusResolver/.test(read('../vite.config.js')) && /unplugin-vue-components/.test(read('../vite.config.js')))
check('vite 配置移除 element-plus manualChunk', !/['"]element-plus['"]\s*:\s*\[['"]element-plus['"]\]/.test(read('../vite.config.js')))

console.log('== 安全头（SPA meta CSP）==')
const html = readFileSync(join(frontend, 'index.html'), 'utf-8')
check('index.html 含 CSP meta', /http-equiv="Content-Security-Policy"/.test(html))

console.log('== 源码静态检查 ==')
const allSource = sources.map((f) => readFileSync(f, 'utf-8')).join('\n')
check('无 .table-scroll 缺失 Firefox 滚动条属性', allSource.includes('scrollbar-width: thin'))
check('sticky 列使用不透明底色变量', allSource.includes('var(--glass-bg-solid)'))
check('echarts 按需注册 Legend 组件', allSource.includes('LegendComponent'))
check('成绩对照表固定列宽', allSource.includes('table-layout: fixed'))
check('存在素质评估组件', sources.some((f) => f.endsWith('QualityChart.vue')))

console.log('== 检修回归（大检修阶段）==')
function read(name) {
  return readFileSync(join(src, name), 'utf-8')
}
check('QualityChart 初始自动选中首科目', /if \(!selectedSubject\.value && subjectList\.value\.length\)/.test(read('components/QualityChart.vue')))
check('ScoreChart 科目陈旧自动重置', /!selectedSubject\.value \|\| !allSubjects\.value\.includes\(selectedSubject\.value\)/.test(read('components/ScoreChart.vue')))
check('QualityChart 科目列表变化自动跟随', /watch\(subjectList,\s*\(list\)/.test(read('components/QualityChart.vue')))
check('QualityChart 等级色绿→红渐变', /52 \* \(1 - t\) \+ 240 \* t/.test(read('components/QualityChart.vue')) && /211 \* \(1 - t\) \+ 82 \* t/.test(read('components/QualityChart.vue')))
check('QualityChart 磁吸滚动接入 v-snap', /table-scroll[^>]*v-snap/.test(read('components/QualityChart.vue')))
check('TeacherDashboard 请求令牌防竞态', /requestSeq/.test(read('views/TeacherDashboard.vue')))
check('StudentDashboard 请求令牌防竞态', /requestSeq/.test(read('views/StudentDashboard.vue')))
check('StudentDetail 请求令牌防竞态', /requestSeq/.test(read('views/StudentDetail.vue')))
check('视图无 data.error 契约分支', !/\.data\s*\.\s*error/.test(allSource))
check('考试总结防除零', /if \(!score \|\| !max_score\) return 0/.test(read('components/ExamReview.vue')))
check('成绩图表 hover 状态随数据重置', /hoveredColumn\.value\s*=\s*[''"]/.test(read('components/ScoreChart.vue')))
check('未使用 --table-sticky-bg 变量', !allSource.includes('--table-sticky-bg'))
check('路由含未知路径兜底', /pathMatch/.test(read('router/index.js')))

console.log('== 磁吸对齐与统一列宽 ==')
const snapSrc = read('utils/snap.js')
check('存在 v-snap 磁吸指令', sources.some((f) => f.endsWith('snap.js')))
check('v-snap 支持配置吸留列宽/列选择器', /opts\.sticky/.test(snapSrc) && /opts\.columns/.test(snapSrc))
check('v-snap 滚动停止后平滑对齐', /behavior:\s*['"]smooth['"]/.test(snapSrc) && /settleDelay/.test(snapSrc))
check('v-snap 已在 main.js 全局注册', /directive\(['"]snap['"]/.test(read('main.js')))
const scoreTable = read('components/ScoreChart.vue')
const qualityTable = read('components/QualityChart.vue')
const teacherTable = read('views/TeacherDashboard.vue')
check('ScoreChart 表格接入 v-snap', /table-scroll[^>]*v-snap/.test(scoreTable))
check('TeacherDashboard 表格接入 v-snap', /table-scroll[^>]*v-snap/.test(teacherTable))
check('QualityChart 表格接入 v-snap', /table-scroll[^>]*v-snap/.test(qualityTable))
check('score-grid 数据列宽统一为 76px', /\.col-data\s*\{\s*width: 76px/.test(scoreTable) && /\.col-corner\s*\{\s*width: 76px/.test(scoreTable))
check('quality-grid 全部列宽统一为 76px', /\.q-corner\s*\{[^}]*width: 76px/.test(qualityTable) && /\.q-head\s*\{\s*width: 76px/.test(qualityTable))

console.log('== 体验优化 ==')
check('存在请求错误提示工具 requestErrorText', /requestErrorText/.test(read('utils/api.js')))
check('学生端区分 404 错误提示', /requestErrorText\(/.test(read('views/StudentDashboard.vue')))
check('学生详情区分 404 错误提示', /requestErrorText\(/.test(read('views/StudentDetail.vue')))
check('教师端区分 404 错误提示', /requestErrorText\(/.test(read('views/TeacherDashboard.vue')))
check('管理端区分 404 错误提示', /requestErrorText\(/.test(read('views/AdminDashboard.vue')))
check('成绩对照表小屏纵向堆叠', /@media\s*\(max-width:\s*768px\)\s*\{[^}]*\.split-layout\s*\{\s*flex-direction:\s*column/.test(read('components/ScoreChart.vue')))
check('教师端对照表小屏纵向堆叠', /\.split-layout\s*\{\s*flex-direction:\s*column/.test(read('views/TeacherDashboard.vue')))
check('素质评估表小屏纵向堆叠', /@media\s*\(max-width:\s*768px\)\s*\{[^}]*\.quality-body\s*\{\s*flex-direction:\s*column/.test(read('components/QualityChart.vue')))

console.log('== 体验优化二期 ==')
check('api 提供姓名搜索 getStudentSearch', /getStudentSearch/.test(read('utils/api.js')))
check('CountUp 数值不变时跳过动画', /if \(to === from\)/.test(read('components/CountUp.vue')))
check('CountUp 后续从上次值连续过渡', /const from = mounted \? shown : 0/.test(read('components/CountUp.vue')))
check('成绩对照表点击支持整列热区', /halfBand/.test(read('components/ScoreChart.vue')))
check('成绩对照表点击热区半径扩大', /bestDist <= 45/.test(read('components/ScoreChart.vue')))
check('无 CSS 磁吸与 JS 吸附冲突', !allSource.includes('scroll-snap-type') && !allSource.includes('scroll-snap-align'))

console.log('== 体验优化三期 ==')
const adminView = read('views/AdminDashboard.vue')
const appView = read('App.vue')
check('移动端头部压缩媒体查询', /@media\s*\(max-width:\s*768px\)\s*\{[\s\S]*\.logo-badge\s*\{\s*display:\s*none/.test(appView) && /@media\s*\(max-width:\s*480px\)/.test(appView))
check('v-snap 防止重复吸附动画', /animating/.test(snapSrc) && /lastTarget/.test(snapSrc))
check('v-snap 吸附有稍长稳定期', /settleDelay \|\| 200/.test(snapSrc))
check('表格右缘渐隐已移除', !appView.includes('snap-overflow') && !snapSrc.includes('snap-overflow'))
check('玻璃卡片去除投影', /\.glass-card\s*\{[\s\S]*?box-shadow:\s*none/.test(appView) && /\.glass-card:hover\s*\{\s*box-shadow:\s*none/.test(appView))
check('管理端提供刷新按钮', /@click="load"/.test(adminView) && /loading/.test(adminView) && /刷新/.test(adminView))
check('管理端刷新带 loading 状态', /loading\s*=\s*ref\(false\)/.test(adminView) && /finally\s*\{\s*loading\.value\s*=\s*false/.test(adminView))
check('管理端掌握率表接入磁吸', /table-scroll[^>]*v-snap/.test(read('views/AdminDashboard.vue')))
check('素质雷达空数据占位', /v-if="radarHasData"[\s\S]*v-else[\s\S]*暂无素质数据/.test(read('components/QualityChart.vue')))
check('教师趋势空数据占位', /v-if="teacherTrendHasData"[\s\S]*v-else[\s\S]*暂无成绩数据/.test(read('views/TeacherDashboard.vue')))
check('空图表占位样式存在', /\.chart-empty[\s\S]*var\(--text-label\)/.test(appView))

console.log('== 体验优化四期 ==')
const teacherSrc = read('views/TeacherDashboard.vue')
check('折线图整列 hover 定位列', /convertToPixel\(\{ xAxisIndex: 0 \},\s*i\)/.test(teacherSrc) && /trendZrBound/.test(teacherSrc))
check('折线图绑定 zr mousemove', /zr\.on\(['"]mousemove['"],\s*onTrendChartMove\)/.test(teacherSrc))
check('悬停滚动改为平滑跟随', /scrollTo\(\{ left: target, behavior: ['"]smooth['"] \}\)/.test(teacherSrc))
check('教师端星号注释在滚动区外', /<\/table>\s*<\/div>\s*<div v-if="teacherFootnotes\.length" class="table-note">/.test(teacherSrc))
check('学生端星号注释在滚动区外', /<\/table>\s*<\/div>\s*<div v-if="subjectFootnotes\.length" class="table-note">/.test(scoreTable))
check('v-snap 由 JS 独立承担磁吸', /behavior:\s*['"]smooth['"]/.test(snapSrc) && !snapSrc.includes('ResizeObserver'))

console.log('== 体验优化五期 ==')
const distChart = read('components/DistributionChart.vue')
check('教师折线图点/列放大统一', /emphasis:\s*\{\s*scale/.test(teacherSrc) && /stateAnimation:\s*\{\s*duration/.test(teacherSrc))
check('学生折线图点/列放大统一', /emphasis:\s*\{\s*scale/.test(scoreTable) && /stateAnimation:\s*\{\s*duration/.test(scoreTable))
check('存在分布图组件', sources.some((f) => f.endsWith('DistributionChart.vue')))
check('分布图柱线同轴平滑曲线', /type:\s*['"]bar['"]/.test(distChart) && /type:\s*['"]line['"]/.test(distChart) && /smooth:\s*true/.test(distChart))
check('api 提供班级分布接口', /getClassDistribution/.test(read('utils/api.js')))
check('api 提供全校分布接口', /getSchoolDistribution/.test(read('utils/api.js')))
check('教师端接入分布图', /DistributionChart/.test(teacherSrc) && /getClassDistribution/.test(teacherSrc))
check('管理端接入分布图', /DistributionChart/.test(adminView) && /getSchoolDistribution/.test(adminView))
check('教师端分布指标可切换', /distributionMetric = ['"]growth['"]/.test(teacherSrc) && /distributionMetric = ['"]score['"]/.test(teacherSrc))
check('管理端分布支持年级过滤', /schoolDistGrade/.test(adminView))

console.log(`\n结果：通过 ${passes} 项自检，失败 ${failures} 项`)
if (failures > 0) process.exit(1)
console.log('ALL TESTS PASSED')
