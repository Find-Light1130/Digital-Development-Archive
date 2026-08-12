<template>
  <div class="glass-card chart-card ai-report">
    <div class="card-header">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
        <path d="M12 3l1.9 4.6 4.6 1.9-4.6 1.9L12 16l-1.9-4.6-4.6-1.9 4.6-1.9L12 3zM19 14l.9 2.1 2.1.9-2.1.9L19 20l-.9-2.1-2.1-.9 2.1-.9L19 14z" fill="var(--accent)"/>
      </svg>
      AI 学情诊断 · {{ reportTitle }}
    </div>

    <div v-if="loading" class="report-loading">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else-if="report">
      <div class="ai-summary">{{ report.summary || report.paragraph }}</div>

      <!-- 学生级：科目掌握度矩阵 -->
      <div v-if="scope === 'student' && report.subjects" class="subj-block">
        <div class="sub-title">科目掌握度</div>
        <div class="subj-grid">
          <div v-for="s in report.subjects" :key="s.subject" class="subj-card" :class="'tone-' + toneOf(s)">
            <div class="subj-name">{{ s.subject }}</div>
            <div class="subj-val">{{ s.mastery }}<span class="subj-unit">%</span></div>
            <div class="subj-trend" :class="s.trend">{{ trendText(s.trend) }}</div>
            <div class="subj-note">{{ s.verdict }}</div>
          </div>
        </div>
      </div>

      <!-- 班级级：科目平均掌握率排行 -->
      <div v-if="scope === 'class' && report.subjects" class="subj-block">
        <div class="sub-title">各科平均掌握率</div>
        <div class="rank-row" v-for="r in report.subjects" :key="r.subject">
          <span class="rank-name">{{ r.subject }}</span>
          <div class="rank-bar"><i :style="{ width: r.avg + '%' }"></i></div>
          <span class="rank-val">{{ r.avg }}%</span>
        </div>
      </div>

      <!-- 年级级：班级对比 -->
      <div v-if="scope === 'grade' && report.classes" class="subj-block">
        <div class="sub-title">各班平均成长指数</div>
        <div class="rank-row" v-for="c in report.classes" :key="c.class_name">
          <span class="rank-name">{{ c.class_name }}</span>
          <div class="rank-bar"><i :style="{ width: c.avg_growth_index + '%' }"></i></div>
          <span class="rank-val">{{ c.avg_growth_index }}</span>
        </div>
      </div>

      <div v-if="report.strengths && report.strengths.length" class="pill-row">
        <span class="pill pill-strong">优势：{{ report.strengths.join('、') }}</span>
      </div>
      <div v-if="report.weaknesses && report.weaknesses.length" class="pill-row">
        <span class="pill pill-weak">薄弱：{{ report.weaknesses.join('、') }}</span>
      </div>

      <div v-if="report.prediction" class="prediction">
        <b>走势预测：</b>{{ report.prediction }}
      </div>

      <div v-if="report.suggestions && report.suggestions.length" class="sugg-block">
        <div class="sub-title">行动建议</div>
        <ul class="sugg-list">
          <li v-for="(s, i) in report.suggestions" :key="i"><span class="idx">{{ i + 1 }}</span>{{ s }}</li>
        </ul>
      </div>

      <div v-if="report.teaching_suggestions && report.teaching_suggestions.length" class="sugg-block">
        <div class="sub-title">教学建议</div>
        <ul class="sugg-list">
          <li v-for="(s, i) in report.teaching_suggestions" :key="i"><span class="idx">{{ i + 1 }}</span>{{ s }}</li>
        </ul>
      </div>

      <div v-if="report.needs_attention_count != null" class="attention-line">
        需关注学生：<b>{{ report.needs_attention_count }}</b> 人
      </div>
    </template>

    <EmptyState v-else icon="search" title="报告生成失败" :hint="error || '暂无足够数据生成报告'" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getLearningReport } from '../utils/api'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  scope: { type: String, required: true }, // student / class / grade
  studentId: { type: [Number, String], default: null },
  className: { type: String, default: null },
  grade: { type: String, default: null },
})

const report = ref(null)
const loading = ref(false)
const error = ref('')

const reportTitle = { student: '学生画像', class: '班级画像', grade: '年级画像' }[props.scope]

function toneOf(s) {
  if (s.mastery >= 80) return 'good'
  if (s.mastery >= 65) return 'mid'
  return 'bad'
}

function trendText(t) {
  return { up: '上升', down: '下滑', stable: '平稳' }[t] || t
}

async function load() {
  loading.value = true
  error.value = ''
  report.value = null
  try {
    const { data } = await getLearningReport({
      scope: props.scope,
      studentId: props.studentId,
      className: props.className,
      grade: props.grade,
    })
    report.value = data
  } catch (e) {
    error.value = e?.response?.status === 404 ? '暂无足够数据生成报告' : '报告加载失败'
  } finally {
    loading.value = false
  }
}

load()
watch(() => [props.scope, props.studentId, props.className, props.grade], load)
defineExpose({ load })
</script>

<style scoped>
.ai-report { padding-bottom: 16px; }
.report-loading { padding: 8px 2px; }
.ai-summary { font-size: 14px; line-height: 1.9; color: var(--text-secondary); background: var(--glass-bg); border: 1px solid var(--glass-border); border-left: 3px solid var(--accent); border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; }
.sub-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin: 12px 0 8px; }
.subj-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 10px; }
.subj-card { border: 1px solid var(--glass-border); border-radius: 10px; padding: 10px; background: var(--glass-bg); }
.subj-name { font-size: 12px; color: var(--text-muted); }
.subj-val { font-size: 22px; font-weight: 700; margin: 2px 0; }
.subj-unit { font-size: 12px; color: var(--text-label); }
.tone-good .subj-val { color: var(--success); }
.tone-mid .subj-val { color: var(--warning); }
.tone-bad .subj-val { color: var(--danger); }
.subj-trend { font-size: 11px; }
.subj-trend.up { color: var(--success); }
.subj-trend.down { color: var(--danger); }
.subj-trend.stable { color: var(--text-label); }
.subj-note { font-size: 11px; color: var(--text-muted); margin-top: 4px; min-height: 28px; }
.rank-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 13px; }
.rank-name { width: 90px; color: var(--text-secondary); flex-shrink: 0; }
.rank-bar { flex: 1; height: 10px; background: var(--glass-border); border-radius: 5px; overflow: hidden; }
.rank-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-soft, var(--accent))); border-radius: 5px; opacity: 0.85; }
.rank-val { width: 52px; text-align: right; color: var(--text-primary); font-weight: 600; flex-shrink: 0; }
.pill-row { margin: 8px 0; }
.pill { display: inline-block; font-size: 12px; padding: 4px 10px; border-radius: 999px; margin-right: 6px; }
.pill-strong { background: rgba(52, 211, 153, 0.12); color: var(--success); border: 1px solid rgba(52, 211, 153, 0.3); }
.pill-weak { background: rgba(248, 113, 113, 0.12); color: var(--danger); border: 1px solid rgba(248, 113, 113, 0.3); }
.prediction { margin: 10px 0; font-size: 13px; color: var(--text-secondary); background: linear-gradient(90deg, var(--glass-bg), transparent); padding: 8px 12px; border-radius: 8px; border: 1px dashed var(--glass-border); }
.sugg-list { list-style: none; padding: 0; margin: 0; }
.sugg-list li { display: flex; gap: 8px; align-items: flex-start; padding: 6px 0; font-size: 13px; color: var(--text-secondary); line-height: 1.6; border-bottom: 1px dashed var(--glass-border); }
.sugg-list li:last-child { border: none; }
.idx { min-width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; margin-top: 2px; }
.attention-line { margin-top: 10px; font-size: 13px; color: var(--warning); }
</style>
