<template>
  <span>{{ display }}</span>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 700 },
  decimals: { type: Number, default: 0 },
})

const display = ref(format(props.value))
let rafId = null
let mounted = false
let shown = 0

function format(v) {
  return props.decimals > 0
    ? v.toFixed(props.decimals)
    : Math.round(v).toString()
}

function animate() {
  if (rafId) cancelAnimationFrame(rafId)
  const to = Number(props.value) || 0
  const from = mounted ? shown : 0
  if (to === from) {
    display.value = format(to)
    return
  }
  const start = performance.now()
  const dur = props.duration
  const step = (now) => {
    const t = Math.min(1, (now - start) / dur)
    const eased = 1 - Math.pow(1 - t, 3)
    display.value = format(from + (to - from) * eased)
    if (t < 1) rafId = requestAnimationFrame(step)
    else shown = to
  }
  rafId = requestAnimationFrame(step)
}

watch(() => props.value, () => {
  mounted = true
  animate()
})
onMounted(animate)
onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = null
})
</script>
