<template>
  <div class="glass-card chart-card companion-card">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M4 5h16v11H8l-4 4V5z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linejoin="round"/>
        <path d="M8 9h8M8 12h5" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      心情树洞
      <span v-if="readOnly" class="ro-tag">只读</span>
    </div>

    <div v-if="riskBanner" class="risk-banner">
      {{ riskBanner }}
    </div>

    <div class="chat-body" ref="bodyRef">
      <div v-if="!messages.length && !loading" class="chat-welcome">
        <div class="welcome-emoji">🌱</div>
        <p>这里是只属于你的树洞。今天想聊聊什么？开心、难过、压力……都可以说给我听。</p>
        <div class="quick-chips">
          <button v-for="q in quickQuestions" :key="q" class="quick-chip" :disabled="readOnly" @click="send(q)">{{ q }}</button>
        </div>
      </div>

      <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
        <div class="bubble">{{ m.message }}</div>
        <div v-if="m.risk_flag" class="msg-flag">含风险提示</div>
      </div>

      <div v-if="typing" class="msg assistant"><div class="bubble typing">AI 正在思考<span>.</span><span>.</span><span>.</span></div></div>
    </div>

    <div v-if="!readOnly" class="chat-input">
      <input v-model="draft" placeholder="说点什么…（回车发送）" maxlength="500" @keydown.enter="send()" />
      <el-button type="primary" size="small" :loading="typing" @click="send()">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { getCompanionHistory, sendCompanionMessage } from '../utils/api'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
  readOnly: { type: Boolean, default: false },
})

const messages = ref([])
const draft = ref('')
const typing = ref(false)
const loading = ref(false)
const bodyRef = ref(null)
const riskBanner = ref('')

const quickQuestions = ['最近压力好大', '这次考试考砸了', '我好难过', '很焦虑睡不着', '和同学闹矛盾了']

async function load() {
  loading.value = true
  try {
    const { data } = await getCompanionHistory(props.studentId)
    messages.value = data
    scrollToBottom()
  } catch (e) {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function send(text) {
  const content = (text ?? draft.value).trim()
  if (!content || props.readOnly) return
  draft.value = ''
  typing.value = true
  try {
    const { data } = await sendCompanionMessage(props.studentId, content)
    messages.value.push({ id: 't-' + Date.now(), role: 'user', message: content, risk_flag: false })
    messages.value.push({ id: 't2-' + Date.now(), role: 'assistant', message: data.reply, risk_flag: data.risk_flag })
    if (data.escalate && data.risk && data.risk.reasons && data.risk.reasons.length) {
      riskBanner.value = '提醒：建议同步联系心理老师。系统检测到 ' + data.risk.reasons[0]
    } else if (data.risk_flag) {
      riskBanner.value = '你刚才表达的内容让人担心，请务必联系心理老师或拨打 12355 寻求帮助。'
    }
    scrollToBottom()
  } catch (e) {
    messages.value.push({ id: 'e-' + Date.now(), role: 'assistant', message: '（消息发送失败，请稍后再试）', risk_flag: false })
  } finally {
    typing.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  })
}

load()
defineExpose({ load })
</script>

<style scoped>
.ro-tag { margin-left: auto; font-size: 11px; color: var(--text-label); border: 1px solid var(--glass-border); padding: 1px 8px; border-radius: 999px; }
.risk-banner { margin-bottom: 8px; background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.35); color: var(--danger); font-size: 12px; border-radius: 8px; padding: 8px 12px; }
.chat-body { height: 320px; overflow-y: auto; padding: 4px 2px; display: flex; flex-direction: column; gap: 8px; }
.chat-welcome { text-align: center; color: var(--text-muted); font-size: 13px; margin: auto; }
.welcome-emoji { font-size: 34px; }
.quick-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 12px; }
.quick-chip { border: 1px solid var(--glass-border); background: var(--glass-bg); color: var(--text-secondary); border-radius: 999px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
.quick-chip:disabled { opacity: 0.5; cursor: not-allowed; }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.msg.assistant { justify-content: flex-start; }
.bubble { max-width: 78%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.7; white-space: pre-wrap; }
.msg.user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 2px; }
.msg.assistant .bubble { background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); border-bottom-left-radius: 2px; }
.msg-flag { font-size: 10px; color: var(--danger); margin-top: 2px; }
.typing span { animation: blink 1.2s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 80%, 100% { opacity: 0; } 40% { opacity: 1; } }
.chat-input { display: flex; gap: 8px; margin-top: 10px; }
.chat-input input { flex: 1; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; color: var(--text-primary); padding: 8px 12px; font-size: 13px; outline: none; }
</style>
