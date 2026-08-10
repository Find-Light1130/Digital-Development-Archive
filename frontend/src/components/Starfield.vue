<template>
  <canvas ref="canvasRef" class="starfield" aria-hidden="true"></canvas>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { themeKey, readCSSVar, isLightTheme } from '../utils/colors'

const canvasRef = ref(null)
let raf = 0
let stars = []
let meteors = []
let width = 0
let height = 0
let dpr = 1
let theme = 'dark'

const METEOR_COLORS = [
  '34, 211, 153',  // emerald
  '96, 165, 250',  // blue
  '167, 231, 215', // teal-mint
  '192, 132, 252', // purple
  '56, 189, 248',  // sky
]

const METEOR_WEIGHTS = [1, 2, 2, 2, 2]

function pickMeteorColor() {
  const total = METEOR_WEIGHTS.reduce((a, b) => a + b, 0)
  let r = Math.random() * total
  for (let i = 0; i < METEOR_WEIGHTS.length; i++) {
    r -= METEOR_WEIGHTS[i]
    if (r < 0) return METEOR_COLORS[i]
  }
  return METEOR_COLORS[0]
}

let auroras = []

const AURORA_GRADIENTS = [
  [52, 211, 153],
  [96, 165, 250],
  [139, 92, 246],
  [56, 189, 248],
]

function auroraColor(p) {
  const n = AURORA_GRADIENTS.length
  const f = (((p % 1) + 1) % 1) * n
  const i = Math.floor(f) % n
  const j = (i + 1) % n
  const t = f - Math.floor(f)
  const A = AURORA_GRADIENTS[i]
  const B = AURORA_GRADIENTS[j]
  return `${Math.round(A[0] + (B[0] - A[0]) * t)}, ${Math.round(A[1] + (B[1] - A[1]) * t)}, ${Math.round(A[2] + (B[2] - A[2]) * t)}`
}

function makeStars(count) {
  const light = theme === 'light'
  return Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    r: light ? 0.7 + Math.random() * 1.1 : 0.6 + Math.random() * 1.3,
    base: light ? 0.08 + Math.random() * 0.3 : 0.15 + Math.random() * 0.45,
    phase: Math.random() * Math.PI * 2,
    speed: 0.25 + Math.random() * 0.75,
    drift: 2 + Math.random() * 6,
    dim: Math.random() < 0.25,
    sparkle: Math.random() < 0.3,
    spin: Math.random() * Math.PI,
    spinSpeed: (Math.random() < 0.5 ? -1 : 1) * (0.3 + Math.random() * 0.6),
  }))
}

function makeAuroras() {
  const n = width > 1100 ? 4 : 3
  auroras = Array.from({ length: n }, () => ({
    cx: 0.12 + Math.random() * 0.76,
    cy: 0.1 + Math.random() * 0.6,
    rx: 0.5 + Math.random() * 0.35,
    ry: 0.22 + Math.random() * 0.16,
    alpha: theme === 'light' ? 0.07 + Math.random() * 0.05 : 0.16 + Math.random() * 0.1,
    drift: 0.00002 + Math.random() * 0.00002,
    phase: Math.random() * Math.PI * 2,
    phase2: Math.random() * Math.PI * 2,
    hue: Math.random() * 3,
  }))
}

function makeMeteor() {
  return {
    x: width * 0.88 + Math.random() * width * 0.3,
    y: Math.random() * height * 0.3,
    vx: -(2.2 + Math.random() * 2.6),
    vy: 1.4 + Math.random() * 1.6,
    life: 0,
    max: 110 + Math.random() * 90,
    len: 22 + Math.random() * 22,
    color: pickMeteorColor(),
  }
}

let nextShower = performance.now() + 6000
let burstsLeft = 0
let nextBurst = -1

function maybeSpawn(t) {
  if (t >= nextShower) {
    nextShower = t + 16000 + Math.random() * 9000
    burstsLeft = 3 + Math.floor(Math.random() * 3)
    nextBurst = t + 300 + Math.random() * 300
  }
  if (burstsLeft > 0 && t >= nextBurst) {
    burstsLeft--
    const n = 1 + Math.floor(Math.random() * 2)
    for (let i = 0; i < n; i++) {
      const m = makeMeteor()
      m.life = -i * 7
      m.y = Math.random() * height * 0.4
      meteors.push(m)
    }
    if (burstsLeft > 0) {
      nextBurst = t + 300 + Math.random() * 300
    }
  } else if (Math.random() < 0.012 && meteors.length < 3) {
    meteors.push(makeMeteor())
  }
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  width = canvas.clientWidth
  height = canvas.clientHeight
  canvas.width = Math.max(1, Math.floor(width * dpr))
  canvas.height = Math.max(1, Math.floor(height * dpr))
  const target = Math.round(Math.min(90, Math.max(30, (width * height) / 26000)))
  stars = makeStars(target)
  makeAuroras()
}

function syncTheme() {
  const next = isLightTheme() ? 'light' : 'dark'
  if (next !== theme) {
    theme = next
    stars = makeStars(stars.length || 50)
    makeAuroras()
  }
}

function drawAurora(ctx, b, t) {
  const cx = b.cx * width + Math.sin(t * b.drift + b.phase) * width * 0.08
  const cy = b.cy * height + Math.sin(t * b.drift * 1.3 + b.phase2 + 1.2) * height * 0.04
  const rx = b.rx * width * (1 + 0.1 * Math.sin(t * 0.0002 + b.phase))
  const ry = b.ry * height * (1 + 0.14 * Math.sin(t * 0.00026 + b.phase2))
  const a = b.alpha
  const hue = b.hue + t * 0.00024

  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(Math.sin(t * 0.00006 + b.phase) * 0.08)
  ctx.scale(1, ry / rx)
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx)
  g.addColorStop(0, `rgba(${auroraColor(hue)}, ${a})`)
  g.addColorStop(0.5, `rgba(${auroraColor(hue + 0.8)}, ${a * 0.5})`)
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g
  ctx.fillRect(-rx, -rx, rx * 2, rx * 2)
  ctx.restore()
}

function drawSparkle(ctx, s, alpha, accent, blue, t) {
  const rot = s.spin + t * 0.0005 * s.spinSpeed
  const inner = s.r * 0.4
  const outer = s.r * 3.4
  ctx.save()
  ctx.translate(s.x, s.y)
  ctx.rotate(rot)
  ctx.beginPath()
  ctx.moveTo(0, -outer)
  ctx.lineTo(inner, -inner)
  ctx.lineTo(outer, 0)
  ctx.lineTo(inner, inner)
  ctx.lineTo(0, outer)
  ctx.lineTo(-inner, inner)
  ctx.lineTo(-outer, 0)
  ctx.lineTo(-inner, -inner)
  ctx.closePath()
  ctx.fillStyle = `rgba(${s.dim ? blue : accent}, ${alpha})`
  ctx.fill()
  ctx.restore()
}

function draw(t) {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const light = theme === 'light'
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)

  const accent = readCSSVar('--accent-rgb') || '52, 211, 153'
  const blue = '96, 165, 250'

  ctx.globalCompositeOperation = 'lighter'
  for (const b of auroras) drawAurora(ctx, b, t)
  ctx.globalCompositeOperation = 'source-over'

  for (const s of stars) {
    const twinkle = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 0.001 * s.speed + s.phase))
    const alpha = s.base * twinkle
    s.y -= s.drift * 0.004
    if (s.y < -2) { s.y = height + 2; s.x = Math.random() * width }
    if (s.sparkle) {
      drawSparkle(ctx, s, alpha, accent, blue, t)
      continue
    }
    ctx.beginPath()
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${s.dim ? blue : accent}, ${alpha})`
    ctx.fill()
    if (s.r > 1.5) {
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r * 3.2, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${accent}, ${alpha * 0.12})`
      ctx.fill()
    }
  }

  maybeSpawn(t)
  meteors = meteors.filter((m) => m.life < m.max)
  for (const m of meteors) {
    m.life++
    m.x += m.vx
    m.y += m.vy
    const fade = m.life < 0 ? 0 : 1 - m.life / m.max
    const tail = m.len
    const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * tail, m.y - m.vy * tail)
    grad.addColorStop(0, `rgba(${m.color}, ${0.95 * fade * (light ? 0.6 : 1)})`)
    grad.addColorStop(0.35, `rgba(${m.color}, ${0.8 * fade})`)
    grad.addColorStop(1, `rgba(${m.color}, 0)`)
    ctx.strokeStyle = grad
    ctx.lineWidth = 1.7
    ctx.beginPath()
    ctx.moveTo(m.x, m.y)
    ctx.lineTo(m.x - m.vx * tail, m.y - m.vy * tail)
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(m.x, m.y, m.life < 0 ? 0 : 2.6, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${m.color}, ${0.28 * fade})`
    ctx.fill()
    ctx.beginPath()
    ctx.arc(m.x, m.y, m.life < 0 ? 0 : 1.5, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255,255,255,${0.95 * fade})`
    ctx.fill()
  }
}

function loop(t) {
  draw(t)
  raf = requestAnimationFrame(loop)
}

function onResize() {
  resize()
}

watch(themeKey, () => {
  syncTheme()
})

onMounted(() => {
  resize()
  syncTheme()
  loop(0)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.starfield {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
</style>
