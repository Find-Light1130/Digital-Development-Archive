/**
 * 表格磁吸对齐指令 v-snap
 * 用法：<div class="table-scroll" v-snap>...</div>
 * 行为：横向滚动停止后，若当前未对齐到任一数据列（表头吸起点），
 *       自动以平滑动画滚动到最近列，与吸留列右侧对齐。
 * 默认以表头吸留列宽（sticky）作为对齐偏移，列由 th.col-head / th.q-head 表示。
 */
export default {
  mounted(el, binding) {
    const opts = binding.value || {}
    const settings = {
      columns: opts.columns || 'th.col-head, th.q-head',
      sticky: opts.sticky || 76,
      settleDelay: opts.settleDelay || 200,
    }
    let timer = null
    let animating = false
    let lastTarget = -1
    const cancel = () => { if (timer) { clearTimeout(timer); timer = null } }

    const nearestTarget = () => {
      const heads = el.querySelectorAll(settings.columns)
      if (!heads.length) return -1
      const rect = el.getBoundingClientRect()
      let best = -1
      let bestDiff = Infinity
      for (const th of heads) {
        const thRect = th.getBoundingClientRect()
        const contentLeft = el.scrollLeft - rect.left + thRect.left
        const snap = contentLeft - settings.sticky
        const d = Math.abs(el.scrollLeft - snap)
        if (d < bestDiff) { bestDiff = d; best = snap }
      }
      return best
    }

    const snap = () => {
      if (el.scrollWidth <= el.clientWidth) return
      const target = nearestTarget()
      if (target < 0) return
      const max = el.scrollWidth - el.clientWidth
      const clamped = Math.max(0, Math.min(target, max))
      if (Math.abs(el.scrollLeft - clamped) <= 1.5) {
        animating = false
        lastTarget = -1
        return
      }
      if (animating) return
      animating = true
      lastTarget = clamped
      el.scrollTo({ left: clamped, behavior: 'smooth' })
      window.setTimeout(() => { animating = false; lastTarget = -1 }, 420)
    }

    const onScroll = () => {
      cancel()
      if (animating) {
        if (Math.abs(el.scrollLeft - lastTarget) <= 1.5) {
          animating = false
          lastTarget = -1
        }
        return
      }
      timer = setTimeout(snap, settings.settleDelay)
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    el.__vSnap = { onScroll, cancel, snap }
  },
  unmounted(el) {
    if (el.__vSnap) {
      el.removeEventListener('scroll', el.__vSnap.onScroll)
      el.__vSnap.cancel()
      delete el.__vSnap
    }
  },
}
