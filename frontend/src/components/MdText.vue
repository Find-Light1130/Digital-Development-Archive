<template>
  <div class="md-body" v-html="html"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  text: { type: String, default: '' },
})

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const html = computed(() => {
  const escaped = escapeHtml(props.text)
  return marked.parse(escaped, { breaks: true, gfm: true })
})
</script>

<style scoped>
.md-body { font-size: 13px; line-height: 1.7; color: var(--text-secondary); word-break: break-word; }
.md-body :deep(p) { margin: 0 0 6px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3),
.md-body :deep(h4) { font-weight: 700; color: var(--text-primary); margin: 8px 0 4px; }
.md-body :deep(h1) { font-size: 16px; }
.md-body :deep(h2) { font-size: 15px; }
.md-body :deep(h3) { font-size: 14px; }
.md-body :deep(h4) { font-size: 13px; }
.md-body :deep(ul),
.md-body :deep(ol) { margin: 4px 0; padding-left: 20px; }
.md-body :deep(li) { margin: 2px 0; }
.md-body :deep(strong) { color: var(--text-primary); font-weight: 700; }
.md-body :deep(em) { font-style: italic; }
.md-body :deep(code) { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; color: var(--accent); background: rgba(var(--accent-rgb), 0.08); padding: 1px 5px; border-radius: 5px; }
.md-body :deep(pre) { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; padding: 8px 12px; overflow-x: auto; margin: 6px 0; }
.md-body :deep(pre code) { background: transparent; padding: 0; color: var(--text-secondary); }
.md-body :deep(blockquote) { border-left: 3px solid var(--glass-border); margin: 6px 0; padding: 2px 10px; color: var(--text-muted); }
.md-body :deep(a) { color: var(--accent); text-decoration: none; }
.md-body :deep(hr) { border: none; border-top: 1px solid var(--glass-border); margin: 8px 0; }
.md-body :deep(table) { border-collapse: collapse; margin: 6px 0; }
.md-body :deep(th),
.md-body :deep(td) { border: 1px solid var(--glass-border); padding: 4px 8px; font-size: 12px; }
</style>