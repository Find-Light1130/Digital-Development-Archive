<template>
  <div class="glass-card empty-card">
    <svg viewBox="0 0 48 48" width="48" height="48" class="empty-icon" :class="`t-${type}`">
      <template v-if="type === 'search'">
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M24 16v8M24 28v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </template>
      <template v-else-if="type === 'class'">
        <rect x="8" y="14" width="32" height="20" rx="3" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M8 21h32M16 14v20M32 14v20" stroke="currentColor" stroke-width="1.2" fill="none"/>
      </template>
      <template v-else-if="type === 'chart'">
        <path d="M8 8v32h32" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <path d="M18 30l5-7 4 4 7-9" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </template>
      <template v-else-if="type === 'data'">
        <rect x="12" y="10" width="24" height="28" rx="4" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M20 21h8M20 26h8M20 31h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </template>
      <template v-else-if="type === 'clock'">
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M24 14v10l7 4" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </template>
      <template v-else>
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M24 15v9M24 28v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </template>
    </svg>
    <div class="empty-text">{{ title }}</div>
    <div v-if="hint" class="empty-hint">{{ hint }}</div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'search' },
  title: { type: String, default: '暂无数据' },
  hint: { type: String, default: '' },
})
</script>

<style scoped>
.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 44px 24px;
  gap: 6px;
  text-align: center;
  min-height: 220px;
}
.empty-icon {
  margin-bottom: 10px;
  opacity: 0.28;
  color: var(--text-muted);
}
.empty-text { font-size: 14px; color: var(--text-secondary); }
.empty-hint { font-size: 12px; color: var(--text-label); }
</style>
