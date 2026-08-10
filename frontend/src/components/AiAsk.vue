<template>
  <div class="glass-card chart-card ask-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M9 3h6M10 3v4M14 3v4M5 7h14l-1 12H6L5 7z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      AI 问数助手
      <span class="ask-hint">试试：初一1班数学掌握率 / 谁在掉队 / 红色预警</span>
    </div>

    <div class="ask-body" ref="bodyRef">
      <div v-if="!records.length" class="ask-welcome">
        <p>用一句话问出数据结论，比如：</p>
        <div class="quick-chips">
          <button v-for="q in quickQuestions" :key="q" class="quick-chip" @click="ask(q)">{{ q }}</button>
        </div>
      </div>
      <div v-for="r in records" :key="r.id" class="ask-record">
        <div class="q-bubble">{{ r.q }}</div>
        <div class="a-bubble" :class="{ error: r.error }">{{ r.a }}</div>
      </div>
    </div>

    <div class="ask-input">
      <input v-model="draft" placeholder="输入你的问题…" maxlength="200" @keydown.enter="ask()" />
      <el-button type="primary" size="small" :loading="loading" @click="ask()">提问</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { askAI } from '../utils/api'

const draft = ref('')
const records = ref([])
const loading = ref(false)
const bodyRef = ref(null)

const quickQuestions = ['初一1班数学掌握率', '本班谁在成绩下滑', '红色预警有哪些学生', '本班多少人']

async function ask(text) {
  const q = (text ?? draft.value).trim()
  if (!q) return
  draft.value = ''
  loading.value = true
  try {
    const { data } = await askAI(q)
    records.value.push({ id: Date.now(), q, a: data.answer || '没有找到答案' })
  } catch (e) {
    records.value.push({ id: Date.now(), q, a: '提问失败，请稍后再试', error: true })
  } finally {
    loading.value = false
    nextTick(() => { if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight })
  }
}
</script>

<style scoped>
.ask-card .card-header { flex-wrap: wrap; gap: 6px; }
.ask-hint { margin-left: auto; font-size: 11px; color: var(--text-label); }
.ask-body { min-height: 140px; max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
.ask-welcome { color: var(--text-muted); font-size: 13px; padding: 8px 0; }
.quick-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.quick-chip { border: 1px solid var(--glass-border); background: var(--glass-bg); color: var(--text-secondary); border-radius: 999px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
.ask-record { display: flex; flex-direction: column; gap: 6px; }
.q-bubble { align-self: flex-end; background: var(--accent); color: #fff; border-radius: 12px 12px 2px 12px; padding: 7px 12px; font-size: 13px; max-width: 80%; }
.a-bubble { align-self: flex-start; background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); border-radius: 12px 12px 12px 2px; padding: 7px 12px; font-size: 13px; line-height: 1.7; max-width: 88%; }
.a-bubble.error { color: var(--danger); }
.ask-input { display: flex; gap: 8px; margin-top: 10px; }
.ask-input input { flex: 1; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; color: var(--text-primary); padding: 8px 12px; font-size: 13px; outline: none; }
</style>
