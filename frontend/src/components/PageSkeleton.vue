<template>
  <div v-if="show" class="page-skeleton">
    <div v-if="kpis" class="sk-kpi-grid" :style="{ gridTemplateColumns: `repeat(${kpis}, 1fr)` }">
      <div v-for="i in kpis" :key="'k' + i" class="glass-card sk-card sk-kpi">
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item variant="text" style="width: 40%; height: 12px; margin: 0 auto" />
            <el-skeleton-item variant="text" style="width: 60%; height: 28px; margin: 8px auto 0" />
          </template>
        </el-skeleton>
      </div>
    </div>

    <div v-if="charts" :class="['sk-chart-grid', { 'sk-half': halfCharts }]">
      <div v-for="i in charts" :key="'c' + i" class="glass-card sk-card sk-chart">
        <el-skeleton animated>
          <template #template>
            <div class="sk-chart-head">
              <el-skeleton-item variant="circle" style="width: 16px; height: 16px" />
              <el-skeleton-item variant="text" style="width: 120px; height: 15px; margin-left: 8px" />
            </div>
            <div class="sk-chart-body">
              <el-skeleton-item variant="rect" style="width: 100%; height: 100%; border-radius: 8px" />
            </div>
          </template>
        </el-skeleton>
      </div>
    </div>

    <div v-if="table" class="glass-card sk-card sk-table">
      <el-skeleton animated :rows="6" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  kpis: { type: Number, default: 4 },
  charts: { type: Number, default: 2 },
  halfCharts: { type: Boolean, default: false },
  table: { type: Boolean, default: false },
})

const show = ref(false)
let timer = null
onMounted(() => { timer = setTimeout(() => { show.value = true }, 150) })
onUnmounted(() => { if (timer) clearTimeout(timer) })
</script>

<style scoped>
.page-skeleton { display: flex; flex-direction: column; gap: 16px; }
.sk-card { padding: 16px 20px; }
.sk-kpi { text-align: center; }
.sk-kpi-grid { display: grid; gap: 14px; }
.sk-chart-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
.sk-chart-grid.sk-half { grid-template-columns: 1fr 1fr; }
.sk-chart-head { display: flex; align-items: center; padding-bottom: 12px; }
.sk-chart-body { height: 240px; }
.sk-table { padding: 14px 20px 20px; }
@media (max-width: 768px) {
  .sk-chart-grid.sk-half { grid-template-columns: 1fr; }
  .sk-kpi-grid { grid-template-columns: 1fr 1fr !important; }
}
</style>
