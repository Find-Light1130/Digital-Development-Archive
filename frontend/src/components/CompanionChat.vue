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
      <div v-if="!messages.length && !typing" class="chat-welcome">
        <div class="welcome-emoji">🌱</div>
        <p>这里是只属于你的树洞。今天想聊聊什么？开心、难过、压力……都可以说给我听。</p>
        <div class="quick-chips">
          <button v-for="q in quickQuestions" :key="q" class="quick-chip" :disabled="readOnly" @click="send(q)">{{ q }}</button>
        </div>
      </div>

      <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
        <div class="bubble" :class="{ 'bubble-md': m.role === 'assistant' }">
          <MdText v-if="m.role === 'assistant'" :text="m.message" />
          <template v-else>{{ m.message }}</template>
        </div>
      </div>

      <div v-if="typingStage" class="msg assistant">
        <div class="bubble typing-stage">
          <span class="spinner"></span>{{ typingStage }}
        </div>
      </div>
      <div v-if="streaming" class="msg assistant">
        <div class="bubble streaming bubble-md"><MdText :text="streamText" /><span class="caret"></span></div>
      </div>
    </div>

    <div v-if="!readOnly" class="chat-input">
      <input v-model="draft" placeholder="说点什么…（回车发送）" maxlength="500" @keydown.enter="send()" :disabled="typing" />
      <el-button type="primary" size="small" :loading="typing" @click="send()">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'
import { getCompanionHistory, companionChatStream } from '../utils/api'
import MdText from './MdText.vue'

const props = defineProps({
  studentId: { type: [Number, String], required: true },
  readOnly: { type: Boolean, default: false },
})

const messages = ref([])
const draft = ref('')
const typing = ref(false)
const typingStage = ref('')
const streaming = ref(false)
const streamText = ref('')
const loading = ref(false)
const bodyRef = ref(null)
const riskBanner = ref('')
let abortController = null

const quickQuestions = ['最近压力好大', '这次考试考砸了', '我好难过', '很焦虑睡不着', '和同学闹矛盾了']

const STAGE_LABELS = { searching: '正在理解你的心情…', generating: '正在为你回复…' }

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
  if (!content || props.readOnly || typing.value) return
  draft.value = ''
  typing.value = true
  riskBanner.value = ''
  messages.value.push({ id: 'u-' + Date.now(), role: 'user', message: content, risk_flag: false })

  let done = null
  abortController = new AbortController()
  try {
    await companionChatStream(props.studentId, content, {
      onStage: (p) => {
        typingStage.value = STAGE_LABELS[p.stage] || p.label || '正在思考…'
        scrollToBottom()
      },
      onToken: (p) => {
        typingStage.value = ''
        streaming.value = true
        streamText.value += (p.text || '')
        scrollToBottom()
      },
      onDone: (p) => {
        done = p
      },
    }, abortController.signal)
    typingStage.value = ''
    streaming.value = false
    const reply = done?.reply || streamText.value
    if (reply) messages.value.push({ id: 'a-' + Date.now(), role: 'assistant', message: reply, risk_flag: !!done?.risk_flag })
    streamText.value = ''
    if (done?.escalate && done?.risk?.reasons?.length) {
      riskBanner.value = '提醒：建议同步联系心理老师。系统检测到 ' + done.risk.reasons[0]
    } else if (done?.risk_flag) {
      riskBanner.value = '你刚才表达的内容让人担心，请务必联系心理老师或拨打 12355 寻求帮助。'
    }
    scrollToBottom()
  } catch (e) {
    if (e?.name === 'AbortError') return
    typingStage.value = ''
    streaming.value = false
    messages.value.push({ id: 'e-' + Date.now(), role: 'assistant', message: '（消息发送失败，请稍后再试）', risk_flag: false })
    streamText.value = ''
    scrollToBottom()
  } finally {
    typing.value = false
  }
}

onBeforeUnmount(() => {
  if (abortController) abortController.abort()
})

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
.bubble-md { white-space: normal; }
.msg.user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 2px; }
.msg.assistant .bubble { background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); border-bottom-left-radius: 2px; }
.typing-stage { display: flex; align-items: center; gap: 7px; color: var(--text-label); font-size: 12px; }
.spinner { width: 12px; height: 12px; border: 2px solid var(--glass-border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.streaming .caret { display: inline-block; width: 2px; height: 14px; background: var(--accent); margin-left: 2px; vertical-align: text-bottom; animation: blink 0.9s step-end infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.chat-input { display: flex; gap: 8px; margin-top: 10px; }
.chat-input input { flex: 1; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; color: var(--text-primary); padding: 8px 12px; font-size: 13px; outline: none; }
</style>
