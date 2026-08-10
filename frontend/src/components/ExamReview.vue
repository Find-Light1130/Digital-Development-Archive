<template>
  <el-dialog v-model="visible" title="测评详细总结" width="420px"
             :close-on-click-modal="true" :close-on-press-escape="true" destroy-on-close>
    <template v-if="exam">
      <div class="review-header">
        <div class="review-subject">{{ exam.subject }}</div>
        <div class="review-type">
          <span :class="exam.exam_type === '期末' ? 'tag-final' : exam.exam_type === '期中' ? 'tag-midterm' : 'tag-regular'">
            {{ examTypeText }}
          </span>
        </div>
      </div>

      <div class="review-grid">
        <div class="review-item">
          <div class="review-label">得分</div>
          <div class="review-val highlight">
            {{ exam.score }}<span class="review-unit">/{{ exam.max_score }}</span>
          </div>
        </div>
        <div class="review-item">
          <div class="review-label">得分率</div>
          <div class="review-val">{{ pctText }}</div>
        </div>
        <div class="review-item">
          <div class="review-label">测评日期</div>
          <div class="review-val" style="font-size:14px">{{ exam.date }}</div>
        </div>
      </div>

      <div class="review-section">
        <div class="review-section-title">复盘反思</div>
        <div class="review-content">{{ reviewText }}</div>
      </div>

      <div class="review-section">
        <div class="review-section-title">提升建议</div>
        <div class="review-content">{{ suggestionText }}</div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ modelValue: Boolean, exam: Object })
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const pctOf = () => {
  if (!props.exam) return 0
  const { score, max_score } = props.exam
  if (!score || !max_score) return 0
  return score / max_score
}

const examTypeText = computed(() => {
  if (!props.exam) return ''
  const t = props.exam.exam_type
  if (t === '月考') return '小测验'
  if (t === '期中') return '期中综评'
  if (t === '期末') return '期末综评'
  return t || ''
})

const pctText = computed(() => `${Math.round(pctOf() * 100)}%`)

const reviewText = computed(() => {
  if (!props.exam) return ''
  const { subject } = props.exam
  const pct = pctOf()
  if (pct >= 0.9) return `${subject}科目表现优秀，得分率高达${Math.round(pct * 100)}%。本次测评知识点掌握扎实，建议继续保持当前学习方法，重点关注错题中暴露的细节问题。`
  if (pct >= 0.75) return `${subject}科目整体表现良好，得分率${Math.round(pct * 100)}%。大部分知识点掌握较好，少数薄弱环节需要针对性巩固。建议整理本次错题，归纳易错题型。`
  if (pct >= 0.6) return `${subject}科目成绩处于中等水平，得分率${Math.round(pct * 100)}%。部分知识点掌握不够熟练，建议制定专项复习计划，每天分配15-20分钟进行针对性训练。`
  if (pct >= 0.4) return `${subject}科目成绩偏低，得分率仅${Math.round(pct * 100)}%。基础知识存在较大漏洞，建议从课本基础概念入手，配合基础练习题逐步提升。可寻求老师或同学的帮助。`
  return `${subject}科目成绩亟待提升，得分率${Math.round(pct * 100)}%。建议重新梳理该科目的知识框架，找出最薄弱的知识模块，制定系统的补习计划。`
})

const suggestionText = computed(() => {
  if (!props.exam) return ''
  const { subject } = props.exam
  const pct = pctOf()
  if (pct >= 0.9) return '挑战更高难度题目，拓展知识深度，参加学科竞赛或进阶课程。'
  if (pct >= 0.75) return '针对错题进行归类整理，每周进行一次知识复盘，重点攻克中等难度以上的题目。'
  if (pct >= 0.6) return '回归课本，梳理知识体系，多做基础题型巩固，逐步向中等难度过渡。'
  if (pct >= 0.4) return '建议每天安排30分钟专门学习该科目，从最基本的概念和公式开始，完成课后基础练习题。'
  return '建议与任课老师沟通，获取个性化辅导方案，同时利用在线学习资源补充基础知识。'
})
</script>

<style scoped>
.review-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.review-subject { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.review-type { flex-shrink: 0; }
.tag-final { font-size: 11px; font-weight: 700; color: var(--tag-final); padding: 2px 12px; border-radius: 12px; border: 1px solid var(--tag-final-bg); }
.tag-midterm { font-size: 11px; font-weight: 700; color: var(--tag-midterm); padding: 2px 12px; border-radius: 12px; border: 1px solid var(--tag-midterm-bg); }
.tag-regular { font-size: 11px; color: var(--text-label); border: 1px solid var(--glass-border); padding: 2px 12px; border-radius: 12px; }

.review-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.review-item { text-align: center; padding: 12px 8px; background: var(--glass-bg); border-radius: 10px; }
.review-label { font-size: 11px; color: var(--text-label); margin-bottom: 4px; letter-spacing: 0.3px; }
.review-val { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.review-val.highlight { color: var(--accent); }
.review-unit { font-size: 12px; font-weight: 400; color: var(--text-label); }

.review-section { margin-bottom: 14px; }
.review-section-title { font-size: 13px; font-weight: 600; color: var(--accent); margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid rgba(var(--accent-rgb), 0.15); }
.review-content { font-size: 13px; line-height: 1.8; color: var(--text-muted); background: rgba(var(--accent-rgb), 0.04); padding: 10px 12px; border-radius: 8px; }
</style>
