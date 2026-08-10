<template>
  <span class="gi-tip">
    <el-popover placement="bottom" trigger="hover" :width="300" :offset="10">
      <template #reference>
        <span class="gi-icon" tabindex="0" aria-label="成长指数说明">?</span>
      </template>
      <div class="gi-content">
        <div class="gi-title">成长指数说明</div>
        <p class="gi-p">
          0–100 分，综合反映学生德智体美劳五方面的成长状况，分数越高代表综合素质发展越好。
        </p>
        <div class="gi-sub">计算公式</div>
        <div class="gi-formula">
          成长指数 = 学习能力×25% + 心理健康×25% + 体育健康×30% + 实践能力×10% + 兴趣发展×10%
        </div>
        <div class="gi-sub">各维度来源</div>
        <ul class="gi-list">
          <li>学习能力：近 3 次测评得分率均值</li>
          <li>心理健康：近 30 次情绪记录均值映射</li>
          <li>体育健康：体育活动累计时长折算</li>
          <li>实践能力：实践活动累计时长折算</li>
          <li>兴趣发展：社团 / 阅读参与度折算</li>
        </ul>
      </div>
    </el-popover>
  </span>
</template>

<style scoped>
.gi-tip { display: inline-flex; align-items: center; margin-left: 4px; }
.gi-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; border-radius: 50%;
  border: 1px solid var(--accent); color: var(--accent);
  font-size: 10px; font-weight: 700; line-height: 1;
  cursor: help; opacity: 0.75; transition: opacity 0.2s, transform 0.2s;
  vertical-align: middle;
}
.gi-icon:hover { opacity: 1; transform: scale(1.15); }
.gi-title { font-weight: 700; font-size: 13px; color: var(--text-primary); margin-bottom: 6px; }
.gi-p { font-size: 12px; line-height: 1.7; color: var(--text-secondary); margin: 0 0 8px; }
.gi-sub {
  font-size: 11px; font-weight: 600; color: var(--accent);
  margin: 8px 0 4px; letter-spacing: 0.5px;
}
.gi-formula {
  font-size: 12px; line-height: 1.7; color: var(--text-secondary);
  background: rgba(var(--accent-rgb), 0.06); border-radius: 8px;
  padding: 8px 10px; font-variant-numeric: tabular-nums;
}
.gi-list { margin: 4px 0 0; padding-left: 18px; font-size: 12px; line-height: 1.8; color: var(--text-muted); }
</style>
