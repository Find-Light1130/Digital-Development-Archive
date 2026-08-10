const SEMESTER_ORDER = ['初一上', '初一下', '初二上', '初二下', '初三上', '初三下']
const FIRST_SCHOOL_YEAR = 2025

const SEMESTER_RANGES = {
  '初一上': ['2025-09-01', '2026-02-15'],
  '初一下': ['2026-02-16', '2026-08-31'],
  '初二上': ['2026-09-01', '2027-02-15'],
  '初二下': ['2027-02-16', '2027-08-31'],
  '初三上': ['2027-09-01', '2028-02-15'],
  '初三下': ['2028-02-16', '2028-08-31'],
}

export function semesterIndex(sem) {
  return SEMESTER_ORDER.indexOf(sem)
}

export function dateSemester(dateStr) {
  const d = String(dateStr || '').slice(0, 10)
  if (!d) return ''
  for (const [sem, [start, end]] of Object.entries(SEMESTER_RANGES)) {
    if (d >= start && d <= end) return sem
  }
  return ''
}

export function semesterSchoolYear(sem) {
  const idx = SEMESTER_ORDER.indexOf(sem)
  if (idx < 0) return null
  const start = FIRST_SCHOOL_YEAR + Math.floor(idx / 2)
  return `${start}-${start + 1}`
}

export function semesterGroups(semesters) {
  const groups = new Map()
  for (const s of semesters) {
    const year = semesterSchoolYear(s)
    const key = year ? `${year} 学年` : '其他'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(s)
  }
  for (const options of groups.values()) {
    options.sort((a, b) => SEMESTER_ORDER.indexOf(a) - SEMESTER_ORDER.indexOf(b))
  }
  return [...groups.entries()]
    .sort((a, b) => {
      const ya = a[0]
      const yb = b[0]
      if (ya === '其他') return 1
      if (yb === '其他') return -1
      return ya.localeCompare(yb)
    })
    .map(([label, options]) => ({ label, options }))
}
