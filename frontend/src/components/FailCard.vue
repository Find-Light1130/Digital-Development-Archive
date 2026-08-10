<template>
  <div class="glass-card error-card">
    <svg viewBox="0 0 48 48" width="44" height="44" class="error-icon">
      <circle cx="24" cy="24" r="20" fill="none" stroke="var(--warning)" stroke-width="1.8" opacity="0.4"/>
      <path d="M24 15v11" stroke="var(--warning)" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="24" cy="32" r="1.6" fill="var(--warning)"/>
    </svg>
    <div class="error-title">数据加载失败</div>
    <div class="error-text">{{ message }}</div>
    <el-button type="primary" class="btn-primary retry-btn" @click="$emit('retry')">
      <svg viewBox="0 0 24 24" width="14" height="14" style="margin-right:5px">
        <path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v4h-4" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      重新加载
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: '请检查后端是否运行后重试' },
})
defineEmits(['retry'])
</script>

<style scoped>
.error-card { padding: 48px 24px; display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center; }
.error-icon { margin-bottom: 6px; animation: warnPulse 1.6s ease-in-out infinite; }
@keyframes warnPulse {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.12); opacity: 1; }
}
.error-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.error-text { font-size: 13px; color: var(--text-label); margin-bottom: 12px; }
.retry-btn { margin-top: 4px; }
.retry-btn:hover svg { animation: spin 0.6s ease; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
