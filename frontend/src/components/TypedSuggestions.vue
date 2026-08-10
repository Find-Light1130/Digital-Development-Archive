<template>
  <div ref="rootRef" class="typed-suggestions">
    <ul v-if="suggestions.length" class="suggestions-list">
      <li v-for="(s, i) in visibleList" :key="i">
        <span class="dot" :class="{ active: isTyping && i === visibleList.length - 1 }"></span>
        <span class="suggestion-text">{{ visibleText(i) }}</span>
        <span v-if="showCaret(i)" class="caret"></span>
      </li>
    </ul>
    <div v-else class="no-data">暂无建议</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  suggestions: { type: Array, default: () => [] },
})

const rootRef = ref(null)
const currentIndex = ref(-1)
const typedLen = ref(0)
const done = ref(false)
const finalBlink = ref(false)
const inView = ref(false)
let timer = null
let observer = null

const isTyping = computed(() => currentIndex.value >= 0 && !done.value)

const visibleList = computed(() =>
  currentIndex.value < 0 ? [] : props.suggestions.slice(0, currentIndex.value + 1)
)

function visibleText(i) {
  if (i === currentIndex.value) return props.suggestions[i].slice(0, typedLen.value)
  return props.suggestions[i]
}

function showCaret(i) {
  if (i !== visibleList.value.length - 1) return false
  return isTyping.value || finalBlink.value
}

function clearTimer() {
  if (timer) { clearTimeout(timer); timer = null }
}

function typeNext() {
  clearTimer()
  const total = props.suggestions.length
  if (currentIndex.value >= total) {
    done.value = true
    finalBlink.value = true
    timer = setTimeout(() => { finalBlink.value = false }, 2600)
    return
  }
  const s = props.suggestions[currentIndex.value]
  if (typedLen.value < s.length) {
    typedLen.value += 1
    timer = setTimeout(typeNext, 45)
  } else {
    typedLen.value = 0
    currentIndex.value += 1
    timer = setTimeout(typeNext, 200)
  }
}

function start() {
  if (!props.suggestions.length) return
  clearTimer()
  currentIndex.value = 0
  typedLen.value = 0
  done.value = false
  finalBlink.value = false
  timer = setTimeout(typeNext, 80)
}

function stop() {
  clearTimer()
  done.value = true
  finalBlink.value = false
}

function handleIntersect(entries) {
  for (const e of entries) {
    if (e.isIntersecting) {
      inView.value = true
      start()
    } else {
      inView.value = false
      stop()
    }
  }
}

watch(() => props.suggestions, () => {
  if (inView.value) start()
})

onMounted(() => {
  if (!rootRef.value) return
  observer = new IntersectionObserver(handleIntersect, { threshold: 0.2 })
  observer.observe(rootRef.value)
})

onBeforeUnmount(() => {
  clearTimer()
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.suggestions-list { list-style: none; padding: 8px 0; margin: 0; }
.suggestions-list li { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; color: var(--text-muted); font-size: 14px; line-height: 1.6; border-bottom: 1px solid var(--glass-border); min-height: 28px; }
.suggestions-list li:last-child { border: none; }
.dot { width: 5px; height: 5px; min-width: 5px; border-radius: 50%; background: var(--glass-border); margin-top: 8px; transition: background 0.2s; }
.dot.active { background: var(--accent); opacity: 0.5; }
.caret {
  display: inline-block; width: 2px; height: 1em; margin-left: 2px;
  background: var(--accent); align-self: center;
  animation: caret-blink 0.9s step-end infinite;
}
@keyframes caret-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.no-data { padding: 12px 0; color: var(--text-label); font-size: 13px; }
</style>
