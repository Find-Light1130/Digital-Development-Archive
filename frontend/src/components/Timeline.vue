<template>
  <div v-if="sections.length" class="timeline">
    <template v-for="section in sections" :key="section.grade">
      <div class="tl-period" v-reveal="{ direction: 'left', delay: 0 }">
        <span class="tl-period-line"></span>
        <span class="tl-period-badge">
          <span class="tl-dot-mark"></span>
          {{ section.title }}
          <span class="tl-dot-mark"></span>
        </span>
        <span class="tl-period-line"></span>
      </div>
      <div v-for="(item, i) in section.items" :key="item.key" class="tl-item" v-reveal="{ direction: 'up', delay: Math.min(i, 6) * 60 }">
        <div class="tl-rail">
          <span class="tl-dot" :style="{ background: item.color, boxShadow: `0 0 0 4px ${item.color}22` }"></span>
          <span v-if="i < section.items.length - 1" class="tl-line"></span>
        </div>
        <div class="tl-card glass-card" :class="`tl-${item.type}`">
          <div class="tl-head">
            <span class="tl-badge" :style="{ color: item.color, borderColor: item.color + '66', background: item.color + '14' }">{{ item.badge }}</span>
            <span class="tl-date">{{ item.dateLabel }}</span>
          </div>
          <div class="tl-title" :style="{ color: item.color }">{{ item.title }}</div>
          <div class="tl-detail">{{ item.detail }}</div>
          <div class="tl-subs" v-if="item.subs && item.subs.length">
            <span v-for="(s, j) in item.subs" :key="j" class="tl-sub">{{ s }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { dateSemester, semesterIndex } from '../utils/semesters'

const props = defineProps({
  scores: { type: Array, default: () => [] },
  emotions: { type: Array, default: () => [] },
  activities: { type: Array, default: () => [] },
  awards: { type: Array, default: () => [] },
  quality: { type: Array, default: () => [] },
})

const GRADE_ORDER = ['初一', '初二', '初三']
const AWARD_COLOR = { 国家级: '#f87171', 省级: '#fbbf24', 市级: '#60a5fa', 校级: '#34d399' }

function gradeOf(sem) {
  return sem ? String(sem).slice(0, 2) : ''
}

const sections = computed(() => {
  const buckets = new Map()
  const bucketOf = (sem) => {
    const key = sem || ''
    if (!buckets.has(key)) buckets.set(key, { sem: sem || '', items: [] })
    return buckets.get(key)
  }

  const examGroups = new Map()
  for (const s of props.scores) {
    if (s.score === null || s.score === undefined) continue
    if (s.exam_type !== '期中' && s.exam_type !== '期末') continue
    const key = `${s.semester}|${s.exam_type}|${s.date}`
    if (!examGroups.has(key)) examGroups.set(key, { semester: s.semester, type: s.exam_type, date: s.date, items: [] })
    examGroups.get(key).items.push(s)
  }
  for (const g of examGroups.values()) {
    const rates = g.items.map((s) => (s.max_score ? (s.score / s.max_score) * 100 : 0))
    const avgRate = Math.round(rates.reduce((a, b) => a + b, 0) / g.items.length)
    bucketOf(g.semester).items.push({
      key: `score-${g.semester}-${g.type}-${g.date}`,
      type: 'score',
      date: g.date,
      dateLabel: (g.date || '').slice(0, 10),
      semester: g.semester,
      badge: g.type,
      color: '#34d399',
      title: `${g.semester}·${g.type}综评`,
      detail: `共 ${g.items.length} 科 · 平均得分率 ${avgRate}%`,
      subs: g.items.map((s) => `${s.subject} ${Math.round(s.score)}`),
    })
  }

  const qualityGroups = new Map()
  for (const q of props.quality) {
    for (const sem of q.semesters || []) {
      const dims = sem.dimensions || []
      const avg = dims.length ? Math.round(dims.reduce((acc, d) => acc + (d.score || 0), 0) / dims.length) : 0
      const key = sem.semester || ''
      if (!qualityGroups.has(key)) qualityGroups.set(key, [])
      qualityGroups.get(key).push({ subject: q.subject, avg })
    }
  }
  for (const [sem, list] of qualityGroups) {
    bucketOf(sem).items.push({
      key: `quality-${sem}`,
      type: 'quality',
      date: '',
      dateLabel: sem || '',
      semester: sem,
      badge: '素质',
      color: '#60a5fa',
      title: '音体美信综合素质评估',
      detail: `共 ${list.length} 科`,
      subs: list.map((x) => `${x.subject} ${x.avg}分`),
    })
  }

  const actGroups = new Map()
  for (const act of props.activities) {
    const sem = act.semester || dateSemester(act.date)
    if (!actGroups.has(sem)) actGroups.set(sem, [])
    actGroups.get(sem).push(act)
  }
  for (const [sem, list] of actGroups) {
    const byType = {}
    for (const a of list) {
      const t = a.type || '活动'
      if (!byType[t]) byType[t] = { count: 0, hours: 0 }
      byType[t].count += 1
      byType[t].hours += a.hours || 0
    }
    const totalHours = list.reduce((acc, a) => acc + (a.hours || 0), 0)
    bucketOf(sem).items.push({
      key: `activity-${sem}`,
      type: 'activity',
      date: '',
      dateLabel: sem || '',
      semester: sem,
      badge: '学期总结',
      color: '#fbbf24',
      title: `${sem || '学期'}体育·社团·实践综合总结`,
      detail: `共 ${list.length} 次 · 累计 ${Math.round(totalHours * 10) / 10} 小时`,
      subs: Object.entries(byType).map(([t, v]) => `${t} ${v.count}次 ${Math.round(v.hours * 10) / 10}小时`),
    })
  }

  for (const a of props.awards) {
    const sem = dateSemester(a.date)
    bucketOf(sem).items.push({
      key: `award-${a.id}`,
      type: 'award',
      date: a.date,
      dateLabel: (a.date || '').slice(0, 10),
      semester: sem,
      badge: '获奖',
      color: AWARD_COLOR[a.level] || '#34d399',
      title: a.title,
      detail: `获得${a.level || ''}奖项`,
      subs: [],
    })
  }

  const byGrade = new Map()
  for (const { sem, items } of buckets.values()) {
    if (!items.length) continue
    const grade = sem ? gradeOf(sem) : '其他'
    if (!byGrade.has(grade)) byGrade.set(grade, { grade, title: grade === '其他' ? '其他记录' : `${grade}年级`, items: [] })
    byGrade.get(grade).items.push(...items)
  }

  const gradeKey = (g) => {
    const idx = GRADE_ORDER.indexOf(g)
    return idx < 0 ? 9 : idx
  }
  const semKeyOf = (it) => (it.semester ? semesterIndex(it.semester) : 99)

  return [...byGrade.values()]
    .sort((a, b) => gradeKey(a.grade) - gradeKey(b.grade))
    .map((sec) => {
      sec.items.sort((a, b) => {
        const si = semKeyOf(a) - semKeyOf(b)
        if (si) return si
        return String(a.date || '9999').localeCompare(String(b.date || '9999'))
      })
      return sec
    })
})
</script>

<style scoped>
.timeline { padding: 4px 2px 8px; }
.tl-period { display: flex; align-items: center; gap: 12px; margin: 30px 0 16px; }
.tl-period-line { flex: 1; height: 1px; background: linear-gradient(90deg, transparent, rgba(var(--accent-rgb), 0.45), transparent); }
.tl-period-badge {
  display: inline-flex; align-items: center; gap: 9px; flex-shrink: 0;
  padding: 6px 18px; border-radius: 20px; letter-spacing: 2px;
  font-size: 13px; font-weight: 700; color: var(--accent);
  background: linear-gradient(135deg, rgba(var(--accent-rgb), 0.18), rgba(var(--accent-rgb), 0.05));
  border: 1px solid rgba(var(--accent-rgb), 0.35);
  box-shadow: 0 2px 10px rgba(var(--accent-rgb), 0.12);
}
.tl-dot-mark { width: 6px; height: 6px; border-radius: 1px; background: var(--accent); transform: rotate(45deg); opacity: 0.55; }
.tl-period:first-child { margin-top: 6px; }
.tl-item { display: flex; gap: 14px; position: relative; }
.tl-rail { display: flex; flex-direction: column; align-items: center; width: 18px; flex-shrink: 0; }
.tl-dot { width: 11px; height: 11px; border-radius: 50%; margin-top: 22px; flex-shrink: 0; }
.tl-line { width: 2px; flex: 1; background: var(--glass-border); margin-top: 4px; }
.tl-card {
  flex: 1;
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 12px;
}
.tl-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.tl-badge {
  font-size: 10px; font-weight: 700; padding: 1px 8px; border-radius: 8px; border: 1px solid;
}
.tl-date { font-size: 11px; color: var(--text-label); }
.tl-title { font-size: 14px; font-weight: 600; }
.tl-detail { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.tl-subs { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.tl-sub { font-size: 10px; color: var(--text-muted); background: var(--glass-bg); border: 1px solid var(--glass-border); padding: 1px 6px; border-radius: 6px; }
</style>
