const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false

function setup(el, binding) {
  const dir = (binding.value && binding.value.direction) || 'up'
  const delay = (binding.value && binding.value.delay) || 0
  const distance = dir === 'left' ? 36 : 44
  el.classList.add('v-reveal')
  el.style.transitionDelay = `${delay}ms`
  el.style.setProperty('--reveal-x', dir === 'left' ? `-${distance}px` : '0px')
  el.style.setProperty('--reveal-y', dir === 'up' ? `${distance}px` : '0px')
}

function observe(el) {
  if (reduced()) {
    el.classList.add('is-revealed')
    return
  }
  if (!('IntersectionObserver' in window)) {
    el.classList.add('is-revealed')
    return
  }
  if (el.__revealIO) {
    el.__revealIO.observe(el)
    return
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        el.classList.add('is-revealed')
        io.unobserve(el)
      }
    })
  }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' })
  io.observe(el)
  el.__revealIO = io
}

export default {
  mounted(el, binding) {
    setup(el, binding)
    observe(el)
  },
  updated(el, binding) {
    setup(el, binding)
    if (reduced() || !el.classList.contains('is-revealed')) observe(el)
  },
  unmounted(el) {
    if (el.__revealIO) {
      el.__revealIO.disconnect()
      el.__revealIO = null
    }
  },
}
