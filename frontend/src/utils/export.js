function escapeCell(value) {
  const s = value === null || value === undefined ? '' : String(value)
  if (/[",\n\r]/.test(s)) {
    return '"' + s.replace(/"/g, '""') + '"'
  }
  return s
}

export function exportCSV(rows, filename) {
  if (!rows.length) return
  const header = Object.keys(rows[0])
  const lines = [header.join(',')]
  for (const row of rows) {
    lines.push(header.map((k) => escapeCell(row[k])).join(','))
  }
  const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : filename + '.csv'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function exportChartPNG(chart, filename) {
  if (!chart || typeof chart.getDataURL !== 'function') {
    console.warn('chart not ready for export')
    return
  }
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
  const a = document.createElement('a')
  a.href = url
  a.download = (filename || 'chart').endsWith('.png') ? filename : (filename || 'chart') + '.png'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
