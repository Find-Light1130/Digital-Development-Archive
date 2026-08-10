import { ref } from 'vue'

export const themeKey = ref(0)

export const SUBJECT_COLORS = [
  '#34d399', '#409eff', '#b88230', '#c45656',
  '#7c3aed', '#0891b2', '#be185d', '#78716c', '#16a34a',
  '#f97316', '#0ea5e9', '#a3e635', '#ec4899', '#eab308',
]

export function subjectColor(s, allSubjects) {
  const idx = allSubjects.indexOf(s)
  if (idx < 0) return SUBJECT_COLORS[0]
  return SUBJECT_COLORS[idx % SUBJECT_COLORS.length]
}

export function readCSSVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function readRGBA(name, alpha) {
  return `rgba(${readCSSVar(name)}, ${alpha})`
}

export function isLightTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light'
}

export function themeTooltip() {
  const light = isLightTheme()
  return {
    backgroundColor: light ? 'rgba(255,255,255,0.96)' : 'rgba(15,20,22,0.94)',
    borderColor: light ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.08)',
    textStyle: { color: light ? '#1a202c' : '#e2e8f0', fontSize: 12 },
    axisPointer: {
      type: 'line',
      lineStyle: { color: light ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.3)', type: 'dashed' },
    },
  }
}

export function levelIndex(rate) {
  if (rate >= 85) return 1
  if (rate >= 70) return 2
  if (rate >= 60) return 3
  return 4
}

export function levelColor(rate) {
  return `var(--level-${levelIndex(rate)})`
}

export function heatColor(rate) {
  const r = Math.max(0, Math.min(1, (Number(rate) || 0) / 100))
  return `hsl(${(r * 120).toFixed(0)} 72% 46%)`
}

export function scoreSegmentColor(rate) {
  const r = Math.max(0, Math.min(100, Number(rate) || 0))
  const bucket = Math.floor(r / 5)
  const mid = bucket * 5 + 2.5
  return heatColor(mid)
}

function hslToRgb(h, s, l) {
  h /= 360
  const a = s * Math.min(l, 1 - l)
  const f = (n) => {
    const k = (n + h * 12) % 12
    return l - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)))
  }
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255))
}

export function heatTextColor(rate) {
  const r = Math.max(0, Math.min(1, (Number(rate) || 0) / 100))
  const [R, G, B] = hslToRgb(r * 120, 0.72, 0.46)
  const lum = 0.2126 * R + 0.7152 * G + 0.0722 * B
  return lum > 150 ? '#1a202c' : '#ffffff'
}

export function themePalette() {
  const light = isLightTheme()
  return {
    axisLabel: light ? '#718096' : '#a3b1c1',
    axisLine: light ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)',
    splitLine: light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.04)',
    name: light ? '#718096' : '#a3b1c1',
    muted: light ? '#718096' : '#a3b1c1',
  }
}
