<template>
  <div class="dashboard help-page">
    <div class="help-toolbar no-print">
      <span class="help-title">帮助中心</span>
      <span class="help-sub">从注册到使用，覆盖四大角色与常见问题</span>
    </div>

    <div class="content-wrap">
      <!-- 快速开始 -->
      <section class="glass-card help-section" v-reveal="{ direction: 'up', delay: 0 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke="var(--accent)" stroke-width="1.6" fill="none" stroke-linejoin="round"/>
          </svg>
          快速开始
        </div>
        <div class="help-body">
          <p class="lead">系统面向 <b>学生 / 教师 / 年级组长 / 管理员</b> 四个角色提供专属工作台。学生、教师可自助注册，
            审核通过后登录使用；年级组长与管理员账号由管理员统一创建。</p>
          <div class="step-row">
            <div class="step" v-for="s in steps" :key="s.n">
              <span class="step-n">{{ s.n }}</span>
              <div>
                <div class="step-title">{{ s.title }}</div>
                <div class="step-desc">{{ s.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 角色指南 -->
      <section class="help-section" v-reveal="{ direction: 'up', delay: 60 }">
        <div class="section-title">角色指南</div>
        <div class="role-grid">
          <div class="glass-card role-card" v-for="r in roles" :key="r.key">
            <div class="role-head">
              <span class="role-icon" :style="{ background: r.bg }">
                <svg v-html="r.icon" width="20" height="20" viewBox="0 0 24 24" fill="none"></svg>
              </span>
              <span class="role-name">{{ r.name }}</span>
            </div>
            <ul class="role-list">
              <li v-for="f in r.features" :key="f">{{ f }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 账号与安全 -->
      <section class="glass-card help-section" v-reveal="{ direction: 'up', delay: 80 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" stroke="var(--accent)" stroke-width="1.6" fill="none" stroke-linejoin="round"/>
          </svg>
          账号与安全
        </div>
        <el-collapse class="help-collapse">
          <el-collapse-item v-for="q in accountFaq" :key="q.q" :title="q.q" :name="q.q">
            <p v-for="(line, i) in q.a" :key="i" class="faq-line">{{ line }}</p>
          </el-collapse-item>
        </el-collapse>
      </section>

      <!-- 功能常见问题 -->
      <section class="glass-card help-section" v-reveal="{ direction: 'up', delay: 100 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <circle cx="12" cy="12" r="9" stroke="var(--accent)" stroke-width="1.6" fill="none"/>
            <path d="M9.5 9a2.5 2.5 0 1 1 3.4 2.3c-.8.3-.9 1-.9 1.7" stroke="var(--accent)" stroke-width="1.6" fill="none" stroke-linecap="round"/>
            <circle cx="12" cy="17" r="1" fill="var(--accent)"/>
          </svg>
          常见问题
        </div>
        <el-collapse class="help-collapse">
          <el-collapse-item v-for="q in featureFaq" :key="q.q" :title="q.q" :name="q.q">
            <p v-for="(line, i) in q.a" :key="i" class="faq-line">{{ line }}</p>
          </el-collapse-item>
        </el-collapse>
      </section>

      <!-- 错误提示说明 -->
      <section class="glass-card help-section" v-reveal="{ direction: 'up', delay: 120 }">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M12 3a9 9 0 1 0 9 9 9 9 0 0 0-9-9z" stroke="var(--accent)" stroke-width="1.6" fill="none"/>
            <path d="M12 8v5M12 16.5v.01" stroke="var(--accent)" stroke-width="1.8" fill="none" stroke-linecap="round"/>
          </svg>
          常见提示与含义
        </div>
        <div class="table-scroll">
          <table class="acct-table">
            <thead><tr><th>提示</th><th>含义 / 处理方法</th></tr></thead>
            <tbody>
              <tr v-for="e in errors" :key="e.code">
                <td><code>{{ e.code }}</code> {{ e.label }}</td>
                <td>{{ e.how }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
const steps = [
  { n: '1', title: '注册账号', desc: '学生 / 教师自助注册，实名绑定学生证号' },
  { n: '2', title: '等待审核', desc: '教师由管理员审核，年级组长 / 管理员由管理员创建' },
  { n: '3', title: '登录使用', desc: '审核通过后登录，进入对应角色工作台' },
]

const IC = {
  student: '<path d="M3 9.5l9-4.5 9 4.5-9 4.5-9-4.5z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M7 11.6v3.5c0 1.6 2.2 2.9 5 2.9s5-1.3 5-2.9v-3.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/>',
  teacher: '<rect x="4" y="4.5" width="16" height="11" rx="2" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M9 18.5h6M12 15.5v3" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
  grade_leader: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M9 12l2.2 2.2L15.5 9.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  admin: '<path d="M3 9.5l9-4.5 9 4.5-9 4.5-9-4.5z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M7 11.6v3.5c0 1.6 2.2 2.9 5 2.9s5-1.3 5-2.9v-3.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M21 12v3" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
}

const roles = [
  {
    key: 'student', icon: IC.student, bg: 'linear-gradient(135deg,#047857,#34d399)', name: '学生端',
    features: [
      '查看成长指数与五维画像（学习 / 心理 / 体育 / 实践 / 兴趣）',
      '九大学科成绩趋势折线图与对照表，点击查看考试详情',
      '音体美信素质评估（4 维度 × 9 档等级）',
      '综合素质：活动、获奖、分学期实践时长',
      '记录每日情绪（1-3 分），查看情绪曲线与个性化建议',
    ],
  },
  {
    key: 'teacher', icon: IC.teacher, bg: 'linear-gradient(135deg,#2563eb,#60a5fa)', name: '教师端',
    features: [
      '班级总览 KPI：平均成长指数、各维度均值、关注学生预警',
      '各科平均掌握率条形图（仅九大学科）',
      '各科成绩趋势，悬浮查看每次考试最高 / 最低 / 平均分',
      '学生详情下钻，返回时保留班级选择',
      '录入学生行为事件（体育 / 实践 / 社团 / 阅读，当日同类型幂等）',
    ],
  },
  {
    key: 'grade_leader', icon: IC.grade_leader, bg: 'linear-gradient(135deg,#6d28d9,#a78bfa)', name: '年级组长',
    features: [
      '查看本年级全部班级的班级总览与成长分布',
      '各学科平均掌握率、年级对比数据',
      '本年级教师账号审核（通过 / 驳回）',
      '仅限本年级数据，跨年级访问将被拒绝',
    ],
  },
  {
    key: 'admin', icon: IC.admin, bg: 'linear-gradient(135deg,#b45309,#fbbf24)', name: '管理端',
    features: [
      '全校 KPI 与各年级、班级平均成长指数对比',
      '各学科平均掌握率表与全校数据分布',
      '用户审核：通过 / 驳回待审核账号',
      '创建教师 / 年级组长账号，并为教师设置班级',
    ],
  },
]

const accountFaq = [
  {
    q: '密码有什么要求？',
    a: ['密码长度至少 8 位、最多 128 位，且需同时包含字母和数字。', '忘记密码请联系管理员重置（原型系统未提供自助找回）。'],
  },
  {
    q: '注册后为什么无法登录？',
    a: ['新注册账号状态为"待审核"，需管理员或年级组长审核通过后才能登录。', '登录时若提示"账号待审核"或"审核未通过"，请联系管理员处理。'],
  },
  {
    q: '如何修改密码？',
    a: ['登录后点击右上角用户名，选择"修改密码"。', '修改成功后当前账号的全部会话将失效，需使用新密码重新登录。'],
  },
  {
    q: '登录失败次数过多怎么办？',
    a: ['同一 IP + 用户名连续输错 5 次后，将触发 15 分钟登录限流（提示 429）。', '请稍后再试，或检查账号密码是否正确。'],
  },
  {
    q: '管理员可以创建哪些账号？',
    a: ['管理员可创建教师与年级组长账号（年级组长需指定年级）。', '学生账号只能自助注册；管理员、年级组长账号不可自助注册。'],
  },
  {
    q: '数据安全如何保障？',
    a: ['密码使用加盐 PBKDF2 哈希存储，登录令牌为服务端会话，默认 7 天有效。', '接口按角色做访问控制，学生仅本人、教师仅本班、年级组长仅本年级。'],
  },
]

const featureFaq = [
  {
    q: '成长指数是怎么计算的？',
    a: ['由学习能力、心理健康、体育健康、实践能力、兴趣发展五个维度加权得出，权重在分析模块中统一配置。'],
  },
  {
    q: '为什么趋势图里同一个考试标签出现多次？',
    a: ['跨学期会出现同名考试（如"期中"），系统会对重复标签追加日期（如"期中·04-27"）以保证唯一。'],
  },
  {
    q: '音体美信的等级是怎么评定的？',
    a: ['音乐 / 体育 / 美术 / 信息技术采用 A+~C- 共 9 档等级，阈值在系统常量中统一维护，各页面口径一致。'],
  },
  {
    q: '情绪记录和活动记录可以重复提交吗？',
    a: ['同一学生同一天的重复提交会覆盖原记录（幂等），不会产生重复数据；不同活动类型同日可并存。'],
  },
  {
    q: '哪些科目会计入成绩趋势？',
    a: ['仅九大学科（语文 / 数学 / 英语 / 物理 / 化学 / 生物 / 历史 / 道德与法治 / 地理），音体美信走素质评估。'],
  },
  {
    q: '出现"未找到对应数据"或"无权访问"怎么办？',
    a: ['"未找到"表示资源不存在（如学生证号错误、班级不存在）；"无权访问"表示当前账号不在该数据范围内，请确认账号角色与数据范围匹配。'],
  },
]

const errors = [
  { code: '401', label: '未登录 / 会话失效', how: '登录已过期或未登录，请重新登录。' },
  { code: '403', label: '权限不足', how: '当前角色无权访问该资源，请确认账号角色与数据范围。' },
  { code: '404', label: '数据不存在', how: '学生 / 班级 / 用户不存在，请核对编号与名称。' },
  { code: '400 / 422', label: '参数不合法', how: '日期格式、数值范围或班级名格式有误，请按页面提示修改。' },
  { code: '429', label: '请求过于频繁', how: '当日记录数已达上限或登录失败过多，请稍后再试。' },
  { code: '409', label: '信息冲突', how: '用户名已存在或学生证号已被绑定，请更换后重试。' },
]
</script>

<style scoped>
.help-page { display: flex; flex-direction: column; gap: 20px; }
.help-toolbar { display: flex; align-items: baseline; gap: 12px; }
.help-title { font-size: 22px; font-weight: 800; color: var(--text-primary); }
.help-sub { font-size: 13px; color: var(--text-label); }

.content-wrap { display: flex; flex-direction: column; gap: 18px; }

.help-section { padding: 22px 24px; border-radius: 18px; }
.card-header {
  display: flex; align-items: center; font-size: 16px; font-weight: 700; color: var(--text-primary);
  padding-bottom: 12px; margin-bottom: 14px; border-bottom: 1px solid var(--glass-border);
}
.section-title { font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 4px 0 14px; }
.section-title::after {
  content: ''; display: block; width: 40px; height: 4px; margin-top: 8px; border-radius: 3px;
  background: linear-gradient(90deg, var(--accent), #60a5fa);
}

.help-body .lead { font-size: 14px; line-height: 1.9; color: var(--text-secondary); margin: 0; }
.help-body .lead b { color: var(--accent); }

.step-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 18px; }
.step {
  display: flex; gap: 12px; align-items: flex-start; padding: 16px; border-radius: 14px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
}
.step-n {
  flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; color: #fff;
  background: linear-gradient(135deg, var(--accent), #60a5fa);
}
.step-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.step-desc { margin-top: 4px; font-size: 12px; line-height: 1.6; color: var(--text-muted); }

.table-scroll { overflow-x: auto; }
.acct-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.acct-table th {
  text-align: left; padding: 10px 12px; color: var(--text-secondary); font-weight: 500;
  border-bottom: 1px solid var(--glass-border); white-space: nowrap;
}
.acct-table td { padding: 10px 12px; color: var(--text-secondary); border-bottom: 1px solid rgba(128,128,128,0.08); }
.acct-table tr:last-child td { border-bottom: none; }
.acct-table code {
  font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; color: var(--accent);
  background: rgba(var(--accent-rgb), 0.08); padding: 2px 6px; border-radius: 5px;
}
.hint { margin-top: 12px; font-size: 12px; color: var(--text-muted); line-height: 1.8; }

.role-tag {
  display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap;
}
.role-student { color: #34d399; background: rgba(52, 211, 153, 0.14); }
.role-teacher { color: #60a5fa; background: rgba(96, 165, 250, 0.14); }
.role-grade_leader { color: #a78bfa; background: rgba(167, 139, 250, 0.14); }
.role-admin { color: #fbbf24; background: rgba(251, 191, 36, 0.14); }

.entry-link { color: var(--accent); text-decoration: none; font-weight: 600; }
.entry-link:hover { text-decoration: underline; }

.role-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.role-card { padding: 20px; border-radius: 18px; }
.role-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.role-icon {
  width: 38px; height: 38px; border-radius: 11px; display: flex; align-items: center; justify-content: center;
  color: #fff; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
}
.role-name { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.role-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 9px; }
.role-list li {
  position: relative; padding-left: 16px; font-size: 12.5px; line-height: 1.65; color: var(--text-secondary);
}
.role-list li::before {
  content: ''; position: absolute; left: 0; top: 8px; width: 6px; height: 6px;
  border-radius: 2px; background: var(--accent); transform: rotate(45deg);
}

.help-collapse { border: none; --el-collapse-border-color: transparent; }
.help-collapse :deep(.el-collapse-item__header) {
  background: transparent; color: var(--text-secondary); font-size: 14px; font-weight: 600;
  border-bottom: 1px solid var(--glass-border); padding: 14px 4px;
}
.help-collapse :deep(.el-collapse-item__header:hover) { color: var(--accent); }
.help-collapse :deep(.el-collapse-item__arrow) { color: var(--text-label); }
.help-collapse :deep(.el-collapse-item__wrap) { background: transparent; border-bottom: none; }
.help-collapse :deep(.el-collapse-item__content) { padding: 6px 4px 14px; color: var(--text-muted); }
.faq-line { margin: 0 0 6px; font-size: 13px; line-height: 1.85; }

@media (max-width: 1024px) {
  .role-grid { grid-template-columns: 1fr 1fr; }
  .step-row { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .role-grid { grid-template-columns: 1fr; }
  .step-row { grid-template-columns: 1fr; }
}
</style>
