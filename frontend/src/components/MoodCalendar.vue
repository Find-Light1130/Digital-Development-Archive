<template>
  <div class="mood-cal">
    <div class="cal-head">
      <button type="button" class="cal-nav" @click="shiftMonth(-1)" title="上个月">‹</button>
      <span class="cal-title">{{ viewYear }}年{{ viewMonth }}月</span>
      <button type="button" class="cal-nav" @click="shiftMonth(1)" title="下个月">›</button>
      <span style="flex:1"></span>
      <div class="cal-legend">
        <span class="lg"><i style="background:var(--danger)"></i>低落</span>
        <span class="lg"><i style="background:var(--text-secondary)"></i>平静</span>
        <span class="lg"><i style="background:var(--accent)"></i>开心</span>
      </div>
    </div>
    <transition :name="slideName" mode="out-in">
      <div class="cal-grid" :key="`${viewYear}-${viewMonth}`">
        <div v-for="w in weekNames" :key="w" class="cal-week">{{ w }}</div>
        <div v-for="cell in cells" :key="cell.key" class="cal-cell"
             :class="{ empty: !cell.day, selected: cell.isSelected, recorded: !!cell.level }"
             :style="cell.level ? { background: levelColor(cell.level), borderColor: levelColor(cell.level) } : {}"
             @click="onSelect(cell)">
          <span class="day-num">{{ cell.day }}</span>
          <span v-if="cell.tags" class="day-tags">{{ cell.tags.join('、') }}</span>
        </div>
      </div>
    </transition>
    <transition name="pop">
      <div v-if="futureVisible" class="future-mask" @click.self="futureVisible = false">
        <div class="future-dialog" role="dialog" aria-modal="true" aria-label="未来日期不可记录">
          <div class="future-mark">
            <svg viewBox="0 0 24 24" width="22" height="22">
              <circle cx="12" cy="12" r="9" stroke="var(--accent)" stroke-width="1.6" fill="none"/>
              <path d="M12 7v5M12 16.5v.5" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </div>
          <h4 class="future-title">还不能记录这一天</h4>
          <p class="future-text">未来日期的情绪状态无法提前填写，请等到当天再来记录吧。</p>
          <button type="button" class="future-btn" @click="futureVisible = false">我知道了</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  emotions: { type: Array, default: () => [] },
})

const emit = defineEmits(['select'])

const now = new Date()
const viewYear = ref(now.getFullYear())
const viewMonth = ref(now.getMonth() + 1)
const slideDir = ref(1)
const futureVisible = ref(false)

const todayStr = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const selected = ref(todayStr)

const weekNames = ['日', '一', '二', '三', '四', '五', '六']

const slideName = computed(() => (slideDir.value >= 0 ? 'slide-next' : 'slide-prev'))

const logMap = computed(() => {
  const m = {}
  for (const e of props.emotions) m[e.date] = e
  return m
})

function shiftMonth(delta) {
  let m = viewMonth.value + delta
  let y = viewYear.value
  if (m < 1) { m = 12; y -= 1 }
  if (m > 12) { m = 1; y += 1 }
  slideDir.value = delta
  viewMonth.value = m
  viewYear.value = y
}

const cells = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value - 1, 1)
  const startWeekday = first.getDay()
  const daysInMonth = new Date(viewYear.value, viewMonth.value, 0).getDate()
  const y = String(viewYear.value).padStart(4, '0')
  const m = String(viewMonth.value).padStart(2, '0')
  const list = []
  for (let i = 0; i < startWeekday; i++) list.push({ key: 'p' + i, day: 0 })
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${y}-${m}-${String(d).padStart(2, '0')}`
    const log = logMap.value[date]
    list.push({
      key: date, day: d, date,
      isSelected: date === selected.value,
      isFuture: date > todayStr,
      level: log ? log.emotion_level : 0,
      tags: log?.tags?.length ? log.tags : null,
      log: log || null,
    })
  }
  const remainder = (7 - (list.length % 7)) % 7
  for (let i = 0; i < remainder; i++) list.push({ key: 't' + i, day: 0 })
  return list
})

function levelColor(level) {
  if (level === 1) return 'rgba(248,113,113,0.28)'
  if (level === 3) return 'rgba(52,211,153,0.30)'
  return 'rgba(148,163,184,0.22)'
}

function onSelect(cell) {
  if (!cell.day) return
  if (cell.isFuture) {
    futureVisible.value = true
    return
  }
  selected.value = cell.date
  emit('select', cell.date, cell.log)
}

onMounted(() => {
  emit('select', todayStr, logMap.value[todayStr] || null)
})
</script>

<style scoped>
.mood-cal { width: 100%; }
.cal-head { display: flex; align-items: center; gap: 8px; padding: 4px 0 10px; }
.cal-nav {
  width: 26px; height: 26px; border-radius: 8px; border: 1px solid var(--glass-border);
  background: var(--glass-bg); color: var(--text-secondary); cursor: pointer; font-size: 16px; line-height: 1;
  font-family: inherit; transition: all 0.2s;
}
.cal-nav:hover { color: var(--accent); border-color: rgba(var(--accent-rgb), 0.4); }
.cal-title { font-size: 14px; font-weight: 600; color: var(--text-primary); min-width: 96px; text-align: center; }
.cal-legend { display: flex; gap: 10px; font-size: 11px; color: var(--text-muted); }
.cal-legend .lg { display: inline-flex; align-items: center; gap: 4px; }
.cal-legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; opacity: 0.85; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-week { text-align: center; font-size: 11px; color: var(--text-label); padding: 2px 0; }
.cal-cell {
  min-height: 44px; border-radius: 10px; border: 1px solid var(--glass-border);
  background: var(--glass-bg); display: flex; flex-direction: column; align-items: center;
  justify-content: flex-start; padding: 4px 2px; cursor: pointer; transition: all 0.2s;
  position: relative;
}
.cal-cell.empty { background: transparent; border-color: transparent; cursor: default; }
.cal-cell:hover:not(.empty) { border-color: rgba(var(--accent-rgb), 0.5); transform: translateY(-1px); }
.cal-cell.selected {
  background: rgba(var(--accent-rgb), 0.30) !important;
  border-color: var(--accent) !important;
  outline: none;
}
.cal-cell.selected .day-num { color: var(--accent); font-weight: 800; }
.day-num { font-size: 12px; color: var(--text-secondary); }
.cal-cell.recorded .day-num { font-weight: 700; color: var(--text-primary); }
.day-tags { font-size: 9px; color: var(--text-muted); line-height: 1.3; text-align: center; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* month slide */
.slide-next-enter-active, .slide-prev-enter-active { transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.22, 1, 0.36, 1); }
.slide-next-leave-active, .slide-prev-leave-active { transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.22, 1, 0.36, 1); }
.slide-next-enter-from { opacity: 0; transform: translateX(26px); }
.slide-next-leave-to { opacity: 0; transform: translateX(-26px); }
.slide-prev-enter-from { opacity: 0; transform: translateX(-26px); }
.slide-prev-leave-to { opacity: 0; transform: translateX(26px); }

/* future-date modal */
.future-mask {
  position: fixed; inset: 0; z-index: 210;
  display: flex; align-items: center; justify-content: center;
  background: rgba(5, 9, 11, 0.5);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.future-dialog {
  width: 320px; max-width: calc(100vw - 48px);
  border-radius: 18px; padding: 26px 24px 22px; text-align: center;
  background: var(--glass-solid-95);
  backdrop-filter: blur(28px) saturate(1.5);
  -webkit-backdrop-filter: blur(28px) saturate(1.5);
  border: 1px solid var(--border-light);
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.future-mark {
  width: 48px; height: 48px; margin: 0 auto 12px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(var(--accent-rgb), 0.12);
}
.future-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.future-text { font-size: 13px; line-height: 1.6; color: var(--text-secondary); margin-bottom: 18px; }
.future-btn {
  border: none; cursor: pointer; padding: 8px 22px; border-radius: 10px;
  font-size: 13px; font-weight: 600; color: #fff; font-family: inherit;
  background: var(--btn-primary-bg);
  box-shadow: 0 2px 12px var(--btn-primary-shadow);
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
}
.future-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 20px var(--btn-primary-shadow-hover); }
.pop-enter-active, .pop-leave-active { transition: opacity 0.25s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; }
</style>
