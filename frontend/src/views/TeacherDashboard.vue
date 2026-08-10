<template>
  <div class="dashboard" :class="{ 'is-refreshing': loading && overview }">
    <div class="glass-card search-card no-print">
      <div class="search-row">
        <span class="search-label">班级管理面板</span>
        <template v-if="isGradeLeader">
          <el-select v-model="className" placeholder="选择班级" class="glass-select" style="flex:1; min-width:180px">
            <el-option v-for="c in classList" :key="c" :label="c" :value="c" />
          </el-select>
          <el-button type="primary" class="btn-primary" :loading="loading" @click="loadData">查询</el-button>
          <el-button class="btn-secondary" :loading="loading" @click="randomClass">随机班级</el-button>
        </template>
        <template v-else>
          <span class="fixed-class">{{ className || '—' }}</span>
          <el-button type="primary" class="btn-primary" :loading="loading" @click="loadData">刷新</el-button>
        </template>
      </div>
    </div>

    <transition name="rise" appear>
    <div v-if="overview" class="content-wrap">
      <div class="kpi-grid">
        <div class="glass-card kpi-card" v-reveal="{ delay: 0 }">
          <div class="kpi-label">班级</div>
          <div class="kpi-name">{{ overview.class_name }}</div>
        </div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 60 }">
          <div class="kpi-label">学生人数</div>
          <div class="kpi-value"><CountUp :value="overview.student_count" /></div>
        </div>
        <div class="glass-card kpi-card" v-reveal="{ delay: 120 }">
          <div class="kpi-label">班级平均成长指数<GrowthIndexTip /></div>
          <div class="kpi-value"><CountUp :value="overview.avg_growth_index" :decimals="2" /></div>
        </div>
      </div>

      <div v-if="overview.needs_attention?.length" class="glass-card warning-card">
        <svg viewBox="0 0 24 24" width="18" height="18" style="flex-shrink:0">
          <path d="M12 2L2 22h20L12 2z" fill="none" stroke="#e6a23c" stroke-width="1.5"/>
          <circle cx="12" cy="16" r="0.8" fill="#e6a23c"/>
          <rect x="11.2" y="9" width="1.6" height="5" rx="0.5" fill="#e6a23c"/>
        </svg>
        <span style="font-weight:600">{{ overview.needs_attention.length }} 名学生需要关注</span>
      </div>

      <div class="glass-card" style="padding:0">
        <div class="table-header">关注学生列表</div>
        <el-table :data="overview.needs_attention"
                  empty-text="暂无需要关注的学生"
                  highlight-current-row
                  class="glass-table" style="width:100%">
          <el-table-column prop="student_id" label="ID" width="70" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="reason" label="关注原因" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" class="btn-secondary" style="padding:4px 12px;font-size:12px"
                         @click="viewStudent(row.student_id)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="glass-card event-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <circle cx="12" cy="8" r="4" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
          </svg>
          考勤录入
          <span class="card-hint">选日期批量标记到校 / 缺勤</span>
          <span style="flex:1"></span>
          <el-date-picker v-model="attendanceForm.date" type="date" size="small" class="glass-select" style="width:150px"
                          value-format="YYYY-MM-DD" :disabled-date="disableFuture" placeholder="考勤日期" />
          <el-button size="small" class="btn-secondary" :loading="attendanceLoading" @click="loadAttendance">加载名单</el-button>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('attendanceCard') }" @click="toggleCollapse('attendanceCard')" :title="isCollapsed('attendanceCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div v-show="!isCollapsed('attendanceCard')" class="attendance-panel">
          <div class="attendance-summary" v-if="attendanceStats">
            本日 {{ attendanceStats.class_name }}：到校 <b>{{ attendanceStats.present }}</b> 人 / {{ attendanceStats.students.length }} 人，缺勤 <b>{{ attendanceStats.absent }}</b> 人
          </div>
          <el-table :data="attendanceRows" empty-text="请先选择日期并加载名单"
                    highlight-current-row class="glass-table" size="small" style="width:100%;max-height:320px">
            <el-table-column prop="student_id" label="ID" width="70" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column label="考勤" width="140">
              <template #default="{ row }">
                <el-radio-group v-model="row.present" size="small">
                  <el-radio :label="true">到校</el-radio>
                  <el-radio :label="false">缺勤</el-radio>
                </el-radio-group>
              </template>
            </el-table-column>
            <el-table-column prop="rate" label="累计出勤率" width="110">
              <template #default="{ row }"><span :class="{ 'rate-warn': row.rate < 90 }">{{ row.rate }}%</span></template>
            </el-table-column>
          </el-table>
          <div class="attendance-actions" v-if="attendanceRows.length">
            <el-button size="small" class="btn-secondary" @click="markAllPresent">全部到校</el-button>
            <el-button size="small" class="btn-primary" :loading="attendanceSaving" @click="saveAttendance">保存考勤</el-button>
          </div>
        </div>
      </div>

      <div class="glass-card event-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <rect x="3" y="5" width="18" height="16" rx="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M8 3v4M16 3v4M3 10h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M9 15l2 2 4-4" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          行为事件录入
          <span class="card-hint">体育 / 实践 / 社团 / 阅读 · 同日同类型覆盖</span>
          <span style="flex:1"></span>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('eventCard') }" @click="toggleCollapse('eventCard')" :title="isCollapsed('eventCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div class="event-row" v-show="!isCollapsed('eventCard')">
          <el-input-number v-model="eventForm.studentId" :min="1" size="small" class="glass-input"
                           style="width:110px" placeholder="学生证号" :controls="false" />
          <el-select v-model="eventForm.type" size="small" class="glass-select" style="width:110px" placeholder="类型">
            <el-option v-for="t in eventTypes" :key="t" :label="t" :value="t" />
          </el-select>
          <el-date-picker v-model="eventForm.date" type="date" size="small" class="glass-select" style="width:150px"
                          value-format="YYYY-MM-DD" :disabled-date="disableFuture" placeholder="日期" />
          <el-input-number v-model="eventForm.hours" :min="1" :max="24" size="small" class="glass-input"
                           style="width:90px" />
          <el-button size="small" class="btn-primary" :loading="eventSaving" @click="submitEvent">录入</el-button>
        </div>
      </div>

      <div class="glass-card event-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 01-10 0z" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 6H4l2 3M17 6h3l-2 3" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          获奖登记
          <span class="card-hint">校级 / 区级 / 市级 / 省级</span>
          <span style="flex:1"></span>
          <el-button size="small" class="btn-secondary export-btn" :loading="awardsLoading" @click="loadClassAwards">刷新</el-button>
          <el-button size="small" class="btn-secondary export-btn" :disabled="!classAwards.length" @click="exportClassAwards">导出CSV</el-button>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('awardCard') }" @click="toggleCollapse('awardCard')" :title="isCollapsed('awardCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div class="event-row" v-show="!isCollapsed('awardCard')">
          <el-select v-model="awardForm.studentId" filterable remote clearable size="small" class="glass-select"
                     style="width:200px" placeholder="搜索学生姓名/学号" :remote-method="searchStudents" :loading="studentSearching">
            <el-option v-for="s in studentOptions" :key="s.student_id" :label="`${s.name}（${s.student_id}）`" :value="s.student_id" />
          </el-select>
          <el-input v-model="awardForm.title" size="small" class="glass-input" style="width:220px"
                    placeholder="获奖名称，如：学科竞赛一等奖" maxlength="50" />
          <el-select v-model="awardForm.level" size="small" class="glass-select" style="width:100px">
            <el-option v-for="lv in awardLevels" :key="lv" :label="lv" :value="lv" />
          </el-select>
          <el-date-picker v-model="awardForm.date" type="date" size="small" class="glass-select" style="width:150px"
                          value-format="YYYY-MM-DD" :disabled-date="disableFuture" placeholder="获奖日期" />
          <el-button size="small" class="btn-primary" :loading="awardSaving" @click="submitAwardEntry">登记</el-button>
          <template v-if="lastAward">
            <span class="last-award">{{ lastAward.studentName }} · {{ lastAward.title }}（{{ lastAward.level }}）</span>
            <el-button size="small" class="btn-secondary" @click="undoAward">撤销</el-button>
          </template>
        </div>
        <div class="award-list" v-show="!isCollapsed('awardCard')" v-if="classAwards.length">
          <div class="award-list-title">本班获奖记录（{{ classAwards.length }}）</div>
          <div class="award-list-scroll">
            <div v-for="a in classAwards.slice(0, 30)" :key="a.id" class="award-item">
              <span class="award-date">{{ a.date }}</span>
              <span class="award-name">{{ a.name }}</span>
              <span class="award-title">{{ a.title }}</span>
              <span class="award-level" :class="`lvl-${a.level}`">{{ a.level }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="glass-card event-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <rect x="4" y="3" width="16" height="18" rx="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
            <path d="M8 8h8M8 12h8M8 16h4" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <circle cx="17" cy="17" r="2" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
          </svg>
          阅卷端 · 答题卡
          <span class="card-hint">进行中的考试 · 批阅后自动录入成绩</span>
          <span style="flex:1"></span>
          <el-button size="small" class="btn-secondary" :loading="examPlansLoading" @click="loadExamPlans">刷新</el-button>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('gradingCard') }" @click="toggleCollapse('gradingCard')" :title="isCollapsed('gradingCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div class="exam-plan-row" v-show="!isCollapsed('gradingCard')">
          <div v-if="!examPlans.length" class="no-plan">暂无进行中的考试，请等待年级组长下达并举行考试。</div>
          <el-table v-else :data="examPlans" highlight-current-row class="glass-table" size="small"
                    @current-change="onSelectExamPlan" empty-text="暂无考试">
            <el-table-column prop="exam_type" label="考试" width="80" />
            <el-table-column prop="subject" label="科目" width="90" />
            <el-table-column prop="exam_date" label="日期" width="110" />
            <el-table-column prop="semester" label="学期" width="100" />
            <el-table-column label="满分" width="70">
              <template #default="{ row }">{{ row.max_score }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <span class="grading-badge" :class="row.graded ? 'is-graded' : 'is-pending'">
                  {{ row.graded ? '已批阅' : '待批阅' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button size="small" class="btn-primary" style="padding:3px 12px;font-size:12px"
                           @click="openGrading(row)">批阅</el-button>
                <el-button size="small" class="btn-secondary" style="padding:3px 12px;font-size:12px"
                           @click="openExamStats(row)">分析</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="half-grid">
        <div class="glass-card chart-card">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 12h4l2-3 3 4 3-5 2 3 4-1" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="17" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
            </svg>
            班级成长画像
            <span style="flex:1"></span>
            <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('radarCard') }" @click="toggleCollapse('radarCard')" :title="isCollapsed('radarCard') ? '展开' : '折叠'">
              <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
          <v-chart v-show="!isCollapsed('radarCard')" :option="radarOption" style="height:300px" autoresize />
        </div>
        <div class="glass-card chart-card">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 3v18h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="15" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="10" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="13" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <path d="M7 15L12 10L17 13" stroke="var(--accent)" stroke-width="1" fill="none"/>
            </svg>
            各科平均掌握率
            <span class="card-hint">文化课</span>
            <span style="flex:1"></span>
            <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('masteryCard') }" @click="toggleCollapse('masteryCard')" :title="isCollapsed('masteryCard') ? '展开' : '折叠'">
              <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
          <v-chart v-show="!isCollapsed('masteryCard')" :option="masteryOption" style="height:300px" autoresize />
        </div>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M3 12h4l2-3 3 4 3-5 2 3 4-1" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <circle cx="7" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
            <circle cx="12" cy="17" r="1.5" fill="var(--accent)"/>
            <circle cx="17" cy="17" r="1.5" fill="var(--accent)" opacity="0.5"/>
          </svg>
          音体美信素质评估
          <span style="flex:1"></span>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('qualityCard') }" @click="toggleCollapse('qualityCard')" :title="isCollapsed('qualityCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <QualityChart v-show="!isCollapsed('qualityCard')" :subjects="classQuality" />
      </div>

      <div class="glass-card event-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M9 3v18M15 3v18M3 9h18M3 15h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <circle cx="12" cy="12" r="2.5" stroke="var(--accent)" stroke-width="1.5" fill="none"/>
          </svg>
          素质评估录入
          <span class="card-hint">音体美信各维度打分（0-100）</span>
          <span style="flex:1"></span>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('qualityEntryCard') }" @click="toggleCollapse('qualityEntryCard')" :title="isCollapsed('qualityEntryCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div class="quality-entry-body" v-show="!isCollapsed('qualityEntryCard')">
          <div class="event-row">
            <el-select v-model="qualityEntry.studentId" filterable remote clearable size="small" class="glass-select"
                       style="width:200px" placeholder="搜索学生姓名/学号" :remote-method="searchStudents" :loading="studentSearching"
                       @change="qualityEntryDims = []">
              <el-option v-for="s in studentOptions" :key="s.student_id" :label="`${s.name}（${s.student_id}）`" :value="s.student_id" />
            </el-select>
            <el-select v-model="qualityEntry.subject" size="small" class="glass-select" style="width:120px" placeholder="科目"
                       @change="qualityEntryDims = []">
              <el-option v-for="s in qualitySubjects" :key="s" :label="s" :value="s" />
            </el-select>
            <el-select v-model="qualityEntry.semester" size="small" class="glass-select" style="width:130px" placeholder="学期"
                       @change="qualityEntryDims = []">
              <el-option v-for="s in teacherSemesters" :key="s" :label="s" :value="s" />
            </el-select>
            <el-button size="small" class="btn-secondary" :loading="qualityLoadSaving" @click="loadQualityEntry">载入当前分数</el-button>
          </div>
          <div v-if="qualityEntryDims.length" class="quality-dims">
            <div v-for="d in qualityEntryDims" :key="d.dimension" class="quality-dim-row">
              <span class="quality-dim-name">{{ d.dimension }}</span>
              <el-input-number v-model="d.score" :min="0" :max="100" size="small" class="glass-input" style="width:130px" />
              <span class="quality-dim-grade">{{ d.grade }}</span>
            </div>
          </div>
          <div class="attendance-actions" v-if="qualityEntryDims.length">
            <el-button size="small" class="btn-primary" :loading="qualityEntrySaving" @click="saveQualityEntry">保存评估</el-button>
          </div>
        </div>
      </div>

      <div class="glass-card chart-card">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
              <path d="M3 3v18h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="7" cy="15" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <circle cx="12" cy="10" r="1.5" fill="var(--accent)"/>
              <circle cx="17" cy="13" r="1.5" fill="var(--accent)" opacity="0.5"/>
              <path d="M7 15L12 10L17 13" stroke="var(--accent)" stroke-width="1" fill="none"/>
            </svg>
              各科成绩趋势
               <span style="flex:1"></span>
               <el-button size="small" class="btn-secondary export-btn" @click="exportTrendPNG">导出图片</el-button>
               <el-select v-model="currentSemester" placeholder="全部学期" size="small" style="width:180px"
                          class="glass-select" @change="onSemesterChange">
                 <el-option label="全部学期" value="" />
                 <el-option-group v-for="g in teacherSemesterGroups" :key="g.label" :label="g.label">
                   <el-option v-for="s in g.options" :key="s" :label="s" :value="s" />
                 </el-option-group>
               </el-select>
               <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('trendCard') }" @click="toggleCollapse('trendCard')" :title="isCollapsed('trendCard') ? '展开' : '折叠'">
                 <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
               </button>
           </div>
        <div v-show="!isCollapsed('trendCard')">
        <div class="score-toolbar">
          <span class="toolbar-label">科目</span>
          <div class="subject-pills">
            <button v-for="s in teacherAllSubjects" :key="s" :class="['pill', { active: teacherTrendSubject === s }]"
                    :style="teacherTrendSubject === s ? { background: teacherColorOf(s), borderColor: teacherColorOf(s) } : {}"
                    @click="selectTrendSubject(s)">
              {{ s }}
            </button>
          </div>
        </div>
        <div class="split-layout">
          <div class="chart-area">
            <v-chart v-if="teacherTrendHasData" ref="trendChartRef" :option="teacherTrendOption"
                     style="height:400px;width:100%" autoresize />
            <div v-else class="chart-empty" style="height:400px">暂无成绩数据</div>
          </div>
          <div v-if="trendColumns.length" class="table-area">
            <div class="table-header">成绩对照表<span class="card-hint">班级平均分</span>
              <el-button size="small" class="btn-secondary export-btn" style="float:right" @click="exportScoreTable">导出CSV</el-button>
            </div>
            <div class="table-scroll" ref="trendTableRef" v-snap>
              <table class="score-grid">
                <colgroup>
                  <col class="col-corner" />
                  <col v-for="col in trendColumns" :key="col" class="col-data"
                       :style="{ width: trendColWidth + 'px', minWidth: trendColWidth + 'px', maxWidth: trendColWidth + 'px' }" />
                </colgroup>
                <thead>
                  <tr>
                    <th class="corner" rowspan="2">科目</th>
                    <th v-for="g in trendColumnGroups" :key="g.label" class="year-head" :colspan="g.cols.length">{{ g.label }}</th>
                  </tr>
                  <tr>
                    <th v-for="col in trendColumns" :key="col" class="col-head"
                        :class="{ highlight: trendHoveredColumn === col }">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIdx) in trendTableRows" :key="row.subject" class="anim-row"
                      :style="{ animationDelay: rowIdx * 40 + 'ms' }">
                    <td class="row-label">{{ row.subject }}</td>
                    <td v-for="col in trendColumns" :key="col" class="cell"
                        :class="{ highlight: trendHoveredColumn === col }"
                        :style="{ color: teacherColorOf(row.subject) }">
                      {{ row.values[col] ?? '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="teacherFootnotes.length" class="table-note">
              <span class="note-sign">*</span>
              <span>— 表示该学期未测评：{{ teacherFootnotes.join('、') }}</span>
            </div>
          </div>
        </div>
        </div>
      </div>

      <div class="glass-card chart-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:6px;flex-shrink:0">
            <path d="M3 3v18h18" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M5 16l4-5 3 3 5-7" stroke="var(--accent)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          班级数据分布
          <span class="card-hint">点击柱子查看学生</span>
          <span style="flex:1"></span>
          <button type="button" class="collapse-btn" :class="{ collapsed: isCollapsed('distCard') }" @click="toggleCollapse('distCard')" :title="isCollapsed('distCard') ? '展开' : '折叠'">
            <svg class="chevron" viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
        <div v-show="!isCollapsed('distCard')">
        <div class="dist-toolbar">
          <div class="metric-pills">
            <button :class="['pill', { active: distributionMetric === 'growth' }]" @click="distributionMetric = 'growth'">成长指数</button>
            <button :class="['pill', { active: distributionMetric === 'score' }]" @click="distributionMetric = 'score'">各科平均分</button>
          </div>
          <div v-if="distributionMetric === 'score'" class="subject-pills">
            <button v-for="s in teacherAllSubjects" :key="s" class="pill"
                    :class="{ active: distributionSubject === s }"
                    :style="distributionSubject === s ? { background: teacherColorOf(s), borderColor: teacherColorOf(s) } : {}"
                    @click="distributionSubject = s">{{ s }}</button>
          </div>
        </div>
        <DistributionChart :buckets="classDistribution.buckets" :counts="classDistribution.counts"
                           :color="distributionColor" @bucket-click="onBucketClick" />
        <div v-if="classDistribution.total" class="dist-total">共 {{ classDistribution.total }} 名</div>
        </div>
      </div>
    </div>
    </transition>

    <el-dialog v-model="distDialog" :title="`分布下钻 · ${distBucketLabel} 区间`" width="480px">
      <div v-loading="distLoading" :element-loading-background="readCSSVar('--glass-bg-solid')">
        <el-table :data="distStudents" empty-text="该区间暂无学生" max-height="380" size="small" class="glass-table">
          <el-table-column prop="student_id" label="学号" width="80" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="value" label="数值" width="90" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" class="btn-secondary" style="padding:4px 10px;font-size:12px"
                         @click="viewStudent(row.student_id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="gradingDialog" :title="gradingTitle" width="720px" class="glass-dialog">
      <div class="grading-head">
        <span>{{ gradingPlan?.subject }} · {{ gradingPlan?.exam_type }} · {{ gradingPlan?.exam_date }}</span>
        <span class="card-hint">满分 {{ gradingPlan?.max_score }} · 全部学生批阅后自动录入成绩</span>
      </div>
      <div class="grading-grid">
        <div class="grading-row grading-head-row">
          <span class="g-col g-idx">#</span>
          <span class="g-col g-name">姓名</span>
          <span class="g-col g-score">得分</span>
        </div>
        <div v-for="(row, i) in gradingRows" :key="row.student_id" class="grading-row">
          <span class="g-col g-idx">{{ i + 1 }}</span>
          <span class="g-col g-name">{{ row.name }}</span>
          <span class="g-col g-score">
            <el-input-number v-model="row.score" :min="0" :max="gradingPlan?.max_score" size="small"
                             class="glass-input" style="width:120px" :controls="false" placeholder="分数"
                             :ref="(el) => setGradingInputRef(i, el)"
                             @keydown.enter.prevent="onGradingEnter(i)" />
          </span>
        </div>
      </div>
      <template #footer>
        <span class="grading-progress">已填 {{ filledCount }} / {{ gradingRows.length }}</span>
        <el-button class="btn-secondary" @click="gradingDialog = false">取消</el-button>
        <el-button class="btn-primary" :loading="gradingSaving" @click="submitGrading">批阅并自动录入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="examStatsDialog" :title="examStatsTitle" width="640px" class="glass-dialog">
      <template v-if="examStats">
        <div class="stats-kpi-grid">
          <div class="stats-kpi"><div class="stats-kpi-value">{{ examStats.avg }}</div><div class="stats-kpi-label">平均分</div></div>
          <div class="stats-kpi"><div class="stats-kpi-value">{{ examStats.highest }}</div><div class="stats-kpi-label">最高分</div></div>
          <div class="stats-kpi"><div class="stats-kpi-value">{{ examStats.lowest }}</div><div class="stats-kpi-label">最低分</div></div>
          <div class="stats-kpi"><div class="stats-kpi-value">{{ examStats.pass_rate }}%</div><div class="stats-kpi-label">及格率</div></div>
        </div>
        <div class="stats-buckets">
          <div v-for="(cnt, name) in examStats.buckets" :key="name" class="stats-bucket">
            <span class="stats-bucket-name">{{ name }}</span>
            <div class="stats-bucket-bar">
              <div class="stats-bucket-fill" :class="`bucket-${name}`"
                   :style="{ width: pctWidth(cnt) + '%' }"></div>
            </div>
            <span class="stats-bucket-cnt">{{ cnt }} 人</span>
          </div>
        </div>
        <div class="stats-ranks">
          <div class="stats-ranks-title">班级排名（{{ examStats.count }} 人）</div>
          <div class="stats-rank-grid">
            <div v-for="r in examStats.ranking" :key="r.student_id"
                 :class="['stats-rank-row', { 'top3': r.rank <= 3 }]">
              <span class="stats-rank-idx">{{ r.rank }}</span>
              <span class="stats-rank-name">{{ r.name }}</span>
              <span class="stats-rank-score">{{ r.score }}</span>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button class="btn-primary" @click="examStatsDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <PageSkeleton v-if="loading && !overview" :kpis="3" :charts="3" :table="true" />

    <FailCard v-if="!loading && !overview && error" :message="error" @retry="loadData" />

    <EmptyState v-if="!loading && !overview && !error" type="class" title="选择班级后点击查询" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import '../utils/echarts'
import { subjectColor, themeKey, themeTooltip, themePalette, readCSSVar } from '../utils/colors'
import { semesterGroups, semesterSchoolYear } from '../utils/semesters'
import { getClassOverview, getClassSemesters, getClassQuality, getClassDistribution,
         getStudentSearch, submitStudentEvent, submitAward, deleteAward,
         getClassDistributionStudents, getTeacherExamPlans, gradeExamPlan,
         getClassStudents, getClassAttendance, submitAttendance, submitQuality,
         getStudentQuality, getExamPlanStats, getClassAwards, requestErrorText } from '../utils/api'
import { exportCSV } from '../utils/export'
import { getStoredUser } from '../utils/auth'
import { exportChartPNG } from '../utils/export'
import QualityChart from '../components/QualityChart.vue'
import DistributionChart from '../components/DistributionChart.vue'
import GrowthIndexTip from '../components/GrowthIndexTip.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CountUp from '../components/CountUp.vue'
import FailCard from '../components/FailCard.vue'
import EmptyState from '../components/EmptyState.vue'

const router = useRouter()
const route = useRoute()
const className = ref('')
const overview = ref(null)
const loading = ref(false)
const error = ref('')
const teacherSemesters = ref([])
const currentSemester = ref('')
const classQuality = ref([])
const eventSaving = ref(false)
const eventTypes = ['体育', '实践', '社团', '阅读']
const eventForm = ref({ studentId: 1, type: '体育', date: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10), hours: 1 })
const attendanceForm = ref({ date: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10) })
const attendanceRows = ref([])
const attendanceStats = ref(null)
const attendanceLoading = ref(false)
const attendanceSaving = ref(false)
const qualitySubjects = ['音乐', '体育', '美术', '信息技术']
const qualityEntry = ref({ studentId: null, subject: '音乐', semester: '' })
const qualityEntryDims = ref([])
const qualityEntrySaving = ref(false)
const qualityLoadSaving = ref(false)
let requestSeq = 0

const COLLAPSE_KEY = 'tdCollapsed'
const collapsed = ref(JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}'))
function isCollapsed(key) { return !!collapsed.value[key] }
function toggleCollapse(key) {
  const next = { ...collapsed.value, [key]: !collapsed.value[key] }
  collapsed.value = next
  localStorage.setItem(COLLAPSE_KEY, JSON.stringify(next))
}

const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

function disableFuture(date) {
  return date.getTime() > Date.now()
}

async function submitEvent() {
  const { studentId, type, date, hours } = eventForm.value
  if (!studentId || !type || !date) { ElMessage.warning('请填写完整的信息'); return }
  eventSaving.value = true
  try {
    await submitStudentEvent(studentId, type, date, hours)
    ElMessage.success(`已记录 ${type} ${hours} 小时`)
    await loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '录入失败，请检查学生证号与日期')
  } finally {
    eventSaving.value = false
  }
}

const isGradeLeader = computed(() => getStoredUser()?.role === 'grade_leader')

/* ---- 学生搜索（获奖登记共用） ---- */

const studentOptions = ref([])
const studentSearching = ref(false)

async function searchStudents(kw) {
  if (!kw) { studentOptions.value = []; return }
  studentSearching.value = true
  try {
    const res = await getStudentSearch(kw)
    studentOptions.value = res.data || []
  } catch {
    studentOptions.value = []
  } finally {
    studentSearching.value = false
  }
}

/* ---- 获奖登记 ---- */

const awardForm = ref({ studentId: null, title: '', level: '校级', date: today() })
const awardSaving = ref(false)
const lastAward = ref(null)
const awardLevels = ['校级', '区级', '市级', '省级']
const classAwards = ref([])
const awardsLoading = ref(false)

async function loadClassAwards() {
  if (!className.value) return
  awardsLoading.value = true
  try {
    const res = await getClassAwards(className.value)
    classAwards.value = res.data || []
  } catch (e) {
    classAwards.value = []
  } finally {
    awardsLoading.value = false
  }
}

function exportClassAwards() {
  if (!classAwards.value.length) { ElMessage.warning('暂无获奖记录可导出'); return }
  const rows = classAwards.value.map((a) => ({ 学生: a.name, 获奖名称: a.title, 级别: a.level, 日期: a.date }))
  exportCSV(rows, `获奖记录_${className.value || '班级'}_${new Date().toISOString().slice(0, 10)}`)
}

async function submitAwardEntry() {
  const { studentId, title, level, date } = awardForm.value
  if (!studentId || !title.trim() || !date) { ElMessage.warning('请填写完整的信息'); return }
  awardSaving.value = true
  try {
    const res = await submitAward({ studentId, title, level, date })
    const name = studentOptions.find(s => s.student_id === studentId)?.name
    lastAward.value = { id: res.data.id, studentName: name || studentId, title: title.trim(), level, date }
    ElMessage.success(`已登记 ${name || '该生'} 获奖`)
    awardForm.value.title = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '登记失败，请检查输入')
  } finally {
    awardSaving.value = false
  }
}

async function undoAward() {
  if (!lastAward.value) return
  try {
    await deleteAward(lastAward.value.id)
    ElMessage.success('已撤销登记')
    lastAward.value = null
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '撤销失败')
  }
}

/* ---- 考勤录入 ---- */

async function loadAttendance() {
  if (!className.value) return
  const date = attendanceForm.value.date
  if (!date) { ElMessage.warning('请选择考勤日期'); return }
  attendanceLoading.value = true
  attendanceRows.value = []
  attendanceStats.value = null
  try {
    const [rosterRes, attRes] = await Promise.all([
      getClassStudents(className.value),
      getClassAttendance(className.value, undefined, date),
    ])
    const roster = rosterRes.data?.students || []
    const rates = {}
    const datePresence = {}
    for (const s of (attRes.data?.students || [])) {
      rates[s.student_id] = s.rate
      if (s.present !== undefined) datePresence[s.student_id] = s.present
    }
    const rows = roster.map((s) => ({
      student_id: s.student_id,
      name: s.name,
      present: datePresence[s.student_id] ?? true,
      rate: rates[s.student_id] ?? 0,
    }))
    attendanceRows.value = rows
    updateAttendanceStats()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '考勤名单加载失败')
  } finally {
    attendanceLoading.value = false
  }
}

function updateAttendanceStats() {
  const rows = attendanceRows.value
  const present = rows.filter((r) => r.present).length
  attendanceStats.value = rows.length
    ? { class_name: className.value, students: rows, present, absent: rows.length - present }
    : null
}

function markAllPresent() {
  attendanceRows.value.forEach((r) => { r.present = true })
  updateAttendanceStats()
}

async function saveAttendance() {
  const rows = attendanceRows.value
  if (!rows.length) { ElMessage.warning('请先加载名单'); return }
  attendanceSaving.value = true
  try {
    const res = await submitAttendance(className.value, attendanceForm.value.date,
      rows.map((r) => ({ student_id: r.student_id, present: r.present })))
    ElMessage.success(`已保存 ${res.data?.count || rows.length} 名学生考勤`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '考勤保存失败')
  } finally {
    attendanceSaving.value = false
  }
}

/* ---- 素质评估录入 ---- */

const QUALITY_DIM_FALLBACK = {
  '音乐': ['音乐素养', '演唱演奏', '节奏感知', '欣赏能力', '舞台表现'],
  '体育': ['体能素质', '运动技能', '协调能力', '团队协作', '体育精神'],
  '美术': ['艺术素养', '创作能力', '审美感知', '技法运用', '艺术表达'],
  '信息技术': ['信息素养', '编程能力', '操作技能', '创新应用', '数字素养'],
}

async function loadQualityEntry() {
  const { studentId, subject, semester } = qualityEntry.value
  if (!studentId) { ElMessage.warning('请先选择学生'); return }
  if (!semester) { ElMessage.warning('请选择学期'); return }
  qualityLoadSaving.value = true
  qualityEntryDims.value = []
  try {
    const res = await getStudentQuality(studentId, semester)
    const list = res.data || []
    const entry = list.find((c) => c.subject === subject)
    const semEntry = entry?.semesters?.find((s) => s.semester === semester)
    if (semEntry?.dimensions?.length) {
      qualityEntryDims.value = semEntry.dimensions.map((d) => ({ dimension: d.dimension, score: d.score, grade: d.grade }))
    } else {
      qualityEntryDims.value = (QUALITY_DIM_FALLBACK[subject] || []).map((d) => ({ dimension: d, score: 80, grade: 'B+' }))
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '素质分数加载失败')
  } finally {
    qualityLoadSaving.value = false
  }
}

async function saveQualityEntry() {
  const { studentId, subject, semester } = qualityEntry.value
  if (!studentId) { ElMessage.warning('请先选择学生'); return }
  if (!semester) { ElMessage.warning('请选择学期'); return }
  if (!qualityEntryDims.value.length) { ElMessage.warning('请先载入维度'); return }
  qualityEntrySaving.value = true
  try {
    const scores = {}
    for (const d of qualityEntryDims.value) scores[d.dimension] = d.score
    const res = await submitQuality({ studentId, subject, semester, scores })
    ElMessage.success(`已保存 ${subject} ${semester} 评估（${res.data?.count || '多项'}）`)
    await loadClassQuality()
    await loadQualityEntry()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '素质评估保存失败')
  } finally {
    qualityEntrySaving.value = false
  }
}

/* ---- 阅卷端 · 答题卡 ---- */

const examPlans = ref([])
const examPlansLoading = ref(false)
const gradingDialog = ref(false)
const gradingPlan = ref(null)
const gradingRows = ref([])
const gradingSaving = ref(false)

async function loadExamPlans() {
  if (!className.value) return
  examPlansLoading.value = true
  try {
    const res = await getTeacherExamPlans(className.value)
    examPlans.value = res.data || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '考试任务加载失败')
    examPlans.value = []
  } finally {
    examPlansLoading.value = false
  }
}

function onSelectExamPlan() {}

const gradingTitle = computed(() =>
  gradingPlan.value ? `${gradingPlan.value.subject} · ${gradingPlan.value.exam_type} 批阅` : '批阅'
)

const filledCount = computed(() => gradingRows.value.filter((r) => r.score != null && r.score !== '').length)

const gradingInputRefs = []
function setGradingInputRef(i, el) {
  gradingInputRefs[i] = el
}

function onGradingEnter(i) {
  const next = gradingRows.value[i + 1]
  if (!next) {
    const btn = document.querySelector('.glass-dialog .el-dialog__footer .btn-primary')
    if (btn) btn.focus()
    return
  }
  const el = gradingInputRefs[i + 1]
  if (el && typeof el.focus === 'function') el.focus()
  else if (el && el.$el) {
    const input = el.$el.querySelector('input')
    if (input) input.focus()
  }
}

function openGrading(plan) {
  gradingPlan.value = plan
  gradingRows.value = (plan.students || []).map((s) => ({ student_id: s.student_id, name: s.name, score: s.score ?? null }))
  gradingDialog.value = true
}

async function submitGrading() {
  if (!gradingPlan.value) return
  const missing = gradingRows.value.filter((r) => r.score == null || r.score === '')
  if (missing.length) {
    ElMessage.warning(`还有 ${missing.length} 名学生未填写分数`)
    return
  }
  gradingSaving.value = true
  try {
    const scores = gradingRows.value.map((r) => ({ student_id: r.student_id, score: r.score }))
    await gradeExamPlan(gradingPlan.value.id, className.value, scores)
    ElMessage.success(`已批阅 ${scores.length} 名学生，成绩已自动录入`)
    gradingDialog.value = false
    await loadExamPlans()
    await loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '批阅失败，请检查分数是否超范围')
  } finally {
    gradingSaving.value = false
  }
}

/* ---- 考试分析 ---- */

const examStatsDialog = ref(false)
const examStatsLoading = ref(false)
const examStats = ref(null)
const examStatsPlan = ref(null)

const examStatsTitle = computed(() =>
  examStatsPlan.value ? `${examStatsPlan.value.subject} · ${examStatsPlan.value.exam_type} 分析` : '考试分析'
)

function pctWidth(cnt) {
  if (!examStats.value || !examStats.value.count) return 0
  return Math.max(4, Math.round(cnt / examStats.value.count * 100))
}

async function openExamStats(plan) {
  examStatsPlan.value = plan
  examStatsDialog.value = true
  examStatsLoading.value = true
  examStats.value = null
  try {
    const res = await getExamPlanStats(plan.id, className.value)
    examStats.value = res.data
  } catch (e) {
    examStatsDialog.value = false
    ElMessage.error(e?.response?.data?.detail || '考试分析加载失败')
  } finally {
    examStatsLoading.value = false
  }
}

/* ---- 分布下钻 ---- */

const distDialog = ref(false)
const distLoading = ref(false)
const distBucketLabel = ref('')
const distStudents = ref([])

async function onBucketClick(label) {
  distBucketLabel.value = label
  distDialog.value = true
  distLoading.value = true
  distStudents.value = []
  try {
    const subject = distributionMetric.value === 'score' ? distributionSubject.value : undefined
    const res = await getClassDistributionStudents(className.value, distributionMetric.value, subject, label)
    distStudents.value = res.data.students || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '下钻查询失败')
  } finally {
    distLoading.value = false
  }
}

const teacherSemesterGroups = computed(() => semesterGroups(teacherSemesters.value))

function buildClassList() {
  const u = getStoredUser()
  if (!u) return []
  if (u.role === 'teacher') {
    return u.class_name ? [u.class_name] : []
  }
  if (u.role === 'grade_leader') {
    const g = u.grade
    const list = []
    for (let c = 1; c <= 7; c++) list.push(`${g}${c}班`)
    return list
  }
  const list = []
  for (let g of ['初一', '初二', '初三']) {
    for (let c = 1; c <= 7; c++) list.push(`${g}${c}班`)
  }
  return list
}

const classList = buildClassList()

async function loadData() {
  if (!className.value) { ElMessage.warning('请先选择班级'); return }
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  currentSemester.value = ''
  teacherSemesters.value = []
  classQuality.value = []
  overview.value = null
  teacherTrendSubject.value = ''
  distributionSubject.value = ''
  classDistribution.value = { buckets: [], counts: [], total: 0 }
  try {
    const [oRes, semRes, qRes] = await Promise.all([
      getClassOverview(className.value),
      getClassSemesters(className.value),
      getClassQuality(className.value),
    ])
    if (seq !== requestSeq) return
    overview.value = oRes.data
    teacherSemesters.value = semRes.data || []
    classQuality.value = qRes.data?.subjects || []
    loadDistribution()
    loadExamPlans()
    loadClassAwards()
  } catch (e) {
    if (seq !== requestSeq) return
    error.value = requestErrorText(e, '未找到该班级')
    ElMessage.error(error.value)
    overview.value = null
  } finally { if (seq === requestSeq) loading.value = false }
}

async function onSemesterChange() {
  if (!className.value) return
  const seq = ++requestSeq
  loading.value = true
  teacherTrendSubject.value = ''
  try {
    const [res, qRes] = await Promise.all([
      getClassOverview(className.value, currentSemester.value || undefined),
      getClassQuality(className.value, currentSemester.value || undefined),
    ])
    if (seq !== requestSeq) return
    overview.value = res.data
    classQuality.value = qRes.data?.subjects || []
  } catch (e) {
    if (seq !== requestSeq) return
    error.value = requestErrorText(e, '未找到该班级')
    ElMessage.error(error.value)
    overview.value = null
    classQuality.value = []
  } finally { if (seq === requestSeq) loading.value = false }
}

function randomClass() {
  className.value = classList[Math.floor(Math.random() * classList.length)]
  loadData()
}

function viewStudent(id) {
  router.push({ path: `/teacher/student/${id}`, query: { class: className.value } })
}

const distributionMetric = ref('growth')
const distributionSubject = ref('')
const classDistribution = ref({ buckets: [], counts: [], total: 0 })
let distSeq = 0

const distributionColor = computed(() =>
  distributionMetric.value === 'score'
    ? teacherColorOf(distributionSubject.value || (teacherAllSubjects.value[0] || ''))
    : ''
)

async function loadDistribution() {
  if (!className.value) return
  const metric = distributionMetric.value
  if (metric === 'score' && !distributionSubject.value) {
    const list = teacherAllSubjects.value
    if (!list.length) return
    distributionSubject.value = list[0]
    return
  }
  const seq = ++distSeq
  const subject = metric === 'score' ? distributionSubject.value : undefined
  try {
    const res = await getClassDistribution(className.value, metric, subject)
    if (seq !== distSeq) return
    classDistribution.value = res.data
  } catch (e) {
    if (seq === distSeq) classDistribution.value = { buckets: [], counts: [], total: 0 }
  }
}

watch([distributionMetric, distributionSubject], loadDistribution)

watch(() => route.query.class, (val) => {
  if (!val || isGradeLeader.value === false) return
  if (val !== className.value) {
    className.value = val
    loadData()
  }
})

watch(className, (val) => {
  if (!val) return
  sessionStorage.setItem('teacherClass', val)
  if (route.query.class !== val) {
    router.replace({ query: { ...route.query, class: val } })
  }
})

onMounted(() => {
  const u = getStoredUser()
  const fromQuery = route.query.class
  let target = ''
  if (fromQuery && isGradeLeader.value) target = fromQuery
  else if (u?.role === 'teacher' && u?.class_name) target = u.class_name
  else target = sessionStorage.getItem('teacherClass') || ''
  if (target && target !== className.value) {
    className.value = target
    loadData()
  }
})

const teacherTrendSubject = ref('')
const teacherAllSubjects = computed(() => {
  const t = overview.value?.subject_trends
  return t ? Object.keys(t) : []
})
function teacherColorOf(s) {
  return subjectColor(s, teacherAllSubjects.value)
}
function selectTrendSubject(s) {
  teacherTrendSubject.value = s
}

const trendChartRef = ref(null)

watch(teacherAllSubjects, (vals) => {
  if (!vals.length) {
    teacherTrendSubject.value = ''
    return
  }
  if (!teacherTrendSubject.value || !vals.includes(teacherTrendSubject.value)) {
    teacherTrendSubject.value = vals[0]
  }
})

const radarOption = computed(() => {
  const aspects = overview.value?.avg_aspects
  if (!aspects) return {}
  void themeKey.value
  const accent = readCSSVar('--accent')
  const accentRGB = readCSSVar('--accent-rgb')
  const textMuted = readCSSVar('--text-muted')
  const indicators = Object.keys(aspects).map((k) => ({ name: k, max: 100 }))
  return {
    tooltip: {},
    radar: {
      indicator: indicators,
      shape: 'circle',
      center: ['50%', '50%'],
      radius: '62%',
      splitArea: { areaStyle: { color: [`rgba(${accentRGB},0.02)`, `rgba(${accentRGB},0.06)`] } },
      axisLine: { lineStyle: { color: `rgba(${accentRGB},0.25)` } },
      axisName: { color: textMuted, fontSize: 12 },
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 8,
      data: [{
        value: Object.values(aspects),
        name: '班级画像',
        areaStyle: { color: `rgba(${accentRGB},0.25)` },
        lineStyle: { color: accent, width: 2 },
        itemStyle: { color: accent },
        emphasis: { itemStyle: { color: accent, shadowBlur: 8, shadowColor: `rgba(${accentRGB},0.5)` } },
      }],
    }],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

const QUALITY_SUBJECTS = ['音乐', '体育', '美术', '信息技术']

const masteryOption = computed(() => {
  const m = overview.value?.subject_mastery
  if (!m) return {}
  void themeKey.value
  const academic = Object.fromEntries(Object.entries(m).filter(([k]) => !QUALITY_SUBJECTS.includes(k)))
  const entries = Object.entries(academic).sort((a, b) => b[1] - a[1])
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  const wrapLabel = (name) => name.length > 2 ? name.slice(0, 2) + '\n' + name.slice(2) : name
  return {
    tooltip: {
      trigger: 'axis', confine: true,
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
      formatter: (p) => {
        const it = p[0]
        return `<b>${it.name}</b><br/>掌握率: <b>${it.value}%</b>`
      },
    },
    grid: { left: 50, right: 20, bottom: 96, top: 10 },
    xAxis: {
      type: 'category',
      data: entries.map(([k]) => k),
      axisLabel: {
        color: pal.axisLabel, fontSize: 11, interval: 0, rotate: 0,
        lineHeight: 15, align: 'center', formatter: wrapLabel,
      },
      axisTick: { alignWithLabel: true },
      axisLine: { lineStyle: { color: pal.axisLine } },
    },
    yAxis: {
      type: 'value', min: 0, max: 100, name: '掌握率',
      axisLabel: { color: pal.axisLabel, fontSize: 10, formatter: '{value}%' },
      nameTextStyle: { color: pal.name, fontSize: 11 },
      splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } },
    },
    series: [{
      type: 'bar',
      data: entries.map(([k, v]) => ({
        value: v,
        itemStyle: { color: subjectColor(k, teacherAllSubjects.value), borderRadius: [6, 6, 0, 0] },
      })),
      barWidth: 40,
      universalTransition: true,
      animationDelay: (i) => i * 80,
    }],
    animationDuration: 650,
    animationDurationUpdate: 600,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
  }
})

const teacherTrendData = computed(() => {
  const trends = overview.value?.subject_trends
  if (!trends || !teacherTrendSubject.value) return { labels: [], values: [], raw: [] }
  const data = trends[teacherTrendSubject.value] || []
  return {
    labels: data.map((d) => d.label),
    values: data.map((d) => d.avg_score),
    raw: data,
  }
})

const teacherTrendHasData = computed(() =>
  teacherTrendData.value.labels.length > 0 && !!teacherTrendSubject.value
)

const teacherTrendOption = computed(() => {
  const td = teacherTrendData.value
  if (!td.labels.length || !teacherTrendSubject.value) return {}
  void themeKey.value
  const color = teacherColorOf(teacherTrendSubject.value)
  const tooltipTheme = themeTooltip()
  const pal = themePalette()
  const light = document.documentElement.getAttribute('data-theme') === 'light'
  const textPrimary = light ? '#1a202c' : '#e2e8f0'
  const textSecondary = light ? '#2d3748' : '#c8d0d8'
  const textMuted = light ? '#718096' : '#5a6a7a'
  const divider = light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.06)'
  return {
    tooltip: {
      trigger: 'axis', confine: true, triggerOn: 'mousemove|click',
      backgroundColor: tooltipTheme.backgroundColor,
      borderColor: tooltipTheme.borderColor,
      textStyle: tooltipTheme.textStyle,
      axisPointer: { ...tooltipTheme.axisPointer, snap: true },
      formatter: (p) => {
        const d = td.raw[p[0].dataIndex]
        if (!d) return ''
        const vals = td.raw.map((r) => r.avg_score).filter((v) => v != null)
        const overall = vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length * 10) / 10 : null
        const meanLine = overall != null
          ? `<div style="color:${textSecondary};margin-top:4px">总体均值: <b>${overall}</b></div>`
          : ''
        return `<div style="font-weight:600;color:${textPrimary}">${teacherTrendSubject.value}</div>`
          + meanLine
          + `<div style="color:${textSecondary};margin-top:4px">班级均分: <b>${d.avg_score}/${d.max_score}</b></div>`
          + `<div style="font-size:11px;color:${textMuted};margin-top:4px;border-top:1px solid ${divider};padding-top:4px">最高: ${d.max}/${d.max_score} &nbsp; 最低: ${d.min}/${d.max_score}</div>`
      },
    },
    grid: { left: 56, right: 20, bottom: 40, top: 20 },
    xAxis: {
      type: 'category', data: td.labels,
      axisLabel: { fontSize: 10, color: pal.axisLabel, interval: 'auto' },
      axisLine: { lineStyle: { color: pal.axisLine } },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value', min: 0, max: td.raw.length ? Math.max(...td.raw.map(r => r.max_score)) : 100, name: '平均分',
      nameLocation: 'middle',
      nameGap: 35,
      nameTextStyle: { fontSize: 11, color: pal.name },
      splitLine: { lineStyle: { color: pal.splitLine, type: 'dashed' } },
      axisLabel: { fontSize: 10, color: pal.name },
    },
    series: [{
      type: 'line', smooth: false, symbol: 'circle', symbolSize: 12,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      emphasis: { scale: 20 / 12, itemStyle: { color, shadowBlur: 16, shadowColor: color } },
      data: td.labels.map((l, i) => ({
        id: l,
        value: td.values[i],
      })),
      animationDelay: (i) => i * 50,
    }],
    animationDuration: 900,
    animationDurationUpdate: 800,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
    stateAnimation: { duration: 300, easing: 'cubicOut' },
  }
})

function exportTrendPNG() {
  exportChartPNG(trendChartRef.value && trendChartRef.value.chart, `${teacherTrendSubject.value || '成绩'}_趋势`)
}

/* ---- 成绩对照表 ---- */

const trendTableRef = ref(null)
const trendHoveredColumn = ref('')

const trendColumns = computed(() => {
  const t = overview.value?.subject_trends
  if (!t) return []
  const map = new Map()
  for (const subj of Object.values(t)) {
    for (const d of subj) {
      if (!map.has(d.label)) map.set(d.label, d.date)
    }
  }
  return [...map.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]) || a[0].localeCompare(b[0]))
    .map(([label]) => label)
})

const trendColumnGroups = computed(() => {
  const groups = []
  let current = null
  for (const col of trendColumns.value) {
    const sem = col.split('·')[0]
    const year = semesterSchoolYear(sem)
    const label = year ? `${year} 学年` : '其他'
    if (!current || current.label !== label) {
      current = { label, cols: [] }
      groups.push(current)
    }
    current.cols.push(col)
  }
  return groups
})

const trendTableRows = computed(() => {
  const t = overview.value?.subject_trends
  if (!t || !trendColumns.value.length) return []
  return teacherAllSubjects.value.map((subj) => {
    const values = {}
    for (const d of (t[subj] || [])) values[d.label] = d.avg_score
    return { subject: subj, values }
  })
})

function exportScoreTable() {
  const cols = trendColumns.value
  if (!cols.length) { ElMessage.warning('暂无成绩数据可导出'); return }
  const rows = trendTableRows.value.map((r) => {
    const row = { 科目: r.subject }
    for (const c of cols) row[c] = r.values[c] ?? '—'
    return row
  })
  exportCSV(rows, `成绩对照表_${className.value || '班级'}_${new Date().toISOString().slice(0, 10)}`)
}

const teacherFootnotes = computed(() => {
  if (!trendColumns.value.length) return []
  const notes = []
  for (const row of trendTableRows.value) {
    const has = (c) => row.values[c] != null
    const idx = trendColumns.value.findIndex(has)
    const lastIdx = trendColumns.value.map(has).lastIndexOf(true)
    if (idx < 0) continue
    const startLabel = trendColumns.value[idx].split('·')[0]
    const endLabel = trendColumns.value[lastIdx].split('·')[0]
    const parts = []
    if (idx > 0) parts.push(`${startLabel}起测评`)
    if (lastIdx < trendColumns.value.length - 1) parts.push(`${endLabel}后停测`)
    if (parts.length) notes.push(`${row.subject}（${parts.join('、')}）`)
  }
  return notes
})

const trendColWidth = 76

/* ---- 悬停竖线跟随 ---- */

function trendColumnAt(x) {
  const chart = trendChartRef.value && trendChartRef.value.chart
  const cd = teacherTrendData.value
  if (!chart || !cd.labels.length) return ''
  let best = -1
  let bestDiff = Infinity
  for (let i = 0; i < cd.labels.length; i++) {
    const cx = chart.convertToPixel({ xAxisIndex: 0 }, i)
    if (cx == null || Number.isNaN(cx)) continue
    const d = Math.abs(cx - x)
    if (d < bestDiff) { bestDiff = d; best = i }
  }
  return best >= 0 ? cd.labels[best] : ''
}

function onTrendChartMove(e) {
  const col = trendColumnAt(e.offsetX)
  if (col !== trendHoveredColumn.value) trendHoveredColumn.value = col
}

function onTrendChartOut() {
  trendHoveredColumn.value = ''
}

let trendZrBound = false

function bindTrendZr() {
  const chart = trendChartRef.value && trendChartRef.value.chart
  if (!chart || trendZrBound) return
  trendZrBound = true
  const zr = chart.getZr()
  zr.on('mousemove', onTrendChartMove)
  zr.on('mouseout', onTrendChartOut)
  zr.on('globalout', onTrendChartOut)
}

watch([teacherTrendHasData, teacherTrendOption], () => {
  if (teacherTrendHasData.value) {
    bindTrendZr()
    if (!trendZrBound) nextTick(bindTrendZr)
  } else {
    trendZrBound = false
  }
})

function scrollTrendTableToCol() {
  const el = trendTableRef.value
  const col = trendHoveredColumn.value
  if (!el || !col) return
  const heads = el.querySelectorAll('th.col-head')
  const idx = trendColumns.value.findIndex((c) => c === col)
  if (idx < 0 || idx >= heads.length) return
  const cont = el.getBoundingClientRect()
  const th = heads[idx].getBoundingClientRect()
  const corner = el.querySelector('.corner')
  const stickyW = corner ? corner.getBoundingClientRect().width : 76
  const contentX = th.left - cont.left + el.scrollLeft
  const viewStart = el.scrollLeft + stickyW
  const viewEnd = el.scrollLeft + el.clientWidth
  if (contentX >= viewStart && contentX + th.width <= viewEnd) return
  const maxScroll = el.scrollWidth - el.clientWidth
  let target = contentX - stickyW - (el.clientWidth - stickyW - th.width) / 2
  target = Math.max(0, Math.min(target, maxScroll))
  el.scrollTo({ left: target, behavior: 'smooth' })
}

watch(trendHoveredColumn, scrollTrendTableToCol)
watch(teacherTrendSubject, () => { trendHoveredColumn.value = '' })
watch(() => overview.value, () => { trendHoveredColumn.value = '' })
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; transition: opacity 0.3s ease; }
.dashboard.is-refreshing { opacity: 0.6; }
.search-card { padding: 16px 20px; }
.search-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.search-label { font-weight: 600; color: var(--accent); font-size: 15px; white-space: nowrap; }
.fixed-class { font-size: 15px; font-weight: 700; color: var(--text-primary); white-space: nowrap; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.kpi-card { padding: 20px; text-align: center; }
.kpi-name { font-size: 22px; font-weight: 700; color: var(--accent); }
.warning-card { padding: 14px 20px; border-left: 4px solid var(--warning) !important; display: flex; align-items: center; gap: 10px; }
.table-header { font-weight: 600; font-size: 15px; color: var(--accent); padding: 14px 20px 8px; }
.half-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { padding: 6px var(--card-pad) 14px; }
.card-header { display: flex; align-items: center; font-weight: 600; font-size: 15px; color: var(--accent); padding: 10px 0 4px; }
.card-hint { margin-left: 8px; font-size: 10px; font-weight: 400; color: var(--text-label); background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 8px; padding: 1px 8px; }
.event-card { padding: 6px 20px 16px; }
.event-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 8px 12px; border-radius: 12px; background: var(--glass-bg); border: 1px solid var(--glass-border); }

.card-hint { font-size: 11px; color: var(--text-muted); margin-left: 6px; font-weight: normal; }
.quality-entry-body { padding: 12px; }
.quality-dims { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.quality-dim-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 10px; background: var(--glass-bg); border: 1px solid var(--glass-border); }
.quality-dim-name { font-size: 12px; color: var(--text-muted); min-width: 72px; }
.quality-dim-grade { font-size: 12px; font-weight: 600; color: var(--accent); min-width: 34px; text-align: center; }

.award-list { padding: 0 12px 12px; }
.award-list-title { font-size: 12px; font-weight: 600; color: var(--text-label); padding: 8px 2px 4px; }
.award-list-scroll { max-height: 220px; overflow-y: auto; border: 1px solid var(--glass-border); border-radius: 10px; }
.award-item { display: flex; align-items: center; gap: 10px; padding: 6px 12px; font-size: 12px; border-bottom: 1px solid var(--glass-border); }
.award-item:last-child { border-bottom: none; }
.award-date { color: var(--text-muted); width: 92px; flex-shrink: 0; font-size: 11px; }
.award-name { color: var(--text-primary); width: 90px; flex-shrink: 0; }
.award-title { flex: 1; min-width: 0; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.award-level { font-size: 11px; padding: 1px 8px; border-radius: 8px; flex-shrink: 0; }
.lvl-校级 { color: var(--text-muted); background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.3); }
.lvl-区级 { color: #60a5fa; background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.3); }
.lvl-市级 { color: #34d399; background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.3); }
.lvl-省级 { color: #fbbf24; background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.3); }

.score-toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 0 6px; }
.toolbar-label { font-size: 12px; color: var(--text-label); font-weight: 500; flex-shrink: 0; }
.subject-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.pill {
  font-size: 11px; padding: 2px 10px; border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.pill:hover { border-color: rgba(var(--accent-rgb), 0.4); color: var(--accent); }
.pill.active { color: var(--pill-active-text); }

.dist-toolbar { display: flex; flex-direction: column; gap: 8px; padding: 8px 0 6px; }
.metric-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.dist-total { text-align: right; font-size: 11px; color: var(--text-label); padding: 6px 2px 0; }

.collapse-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; margin-left: 8px; padding: 0;
  border-radius: 8px; border: 1px solid var(--glass-border);
  background: var(--glass-bg); color: var(--text-label); cursor: pointer;
  font-family: inherit; transition: all 0.2s; flex-shrink: 0;
}
.collapse-btn:hover { color: var(--accent); border-color: rgba(var(--accent-rgb), 0.4); }
.collapse-btn .chevron { transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.collapse-btn.collapsed .chevron { transform: rotate(-90deg); }

.last-award { font-size: 12px; color: var(--text-secondary); background: rgba(var(--accent-rgb), 0.08); border: 1px solid rgba(var(--accent-rgb), 0.2); border-radius: 10px; padding: 4px 10px; }

.attendance-panel { padding: 8px 12px 12px; }
.attendance-summary { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; padding: 8px 12px; border-radius: 10px; background: var(--glass-bg); border: 1px solid var(--glass-border); }
.attendance-summary b { color: var(--accent); }
.rate-warn { color: var(--danger); font-weight: 600; }
.attendance-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 10px; }

.no-plan { font-size: 12px; color: var(--text-muted); padding: 10px 4px; }
.grading-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 9px; }
.grading-badge.is-pending { color: #fbbf24; background: rgba(251, 191, 36, 0.15); }
.grading-badge.is-graded { color: #34d399; background: rgba(52, 211, 153, 0.15); }
.grading-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 0 2px 10px; color: var(--text-secondary); font-size: 13px; }
.grading-head .card-hint { margin-left: 0; }
.grading-grid { max-height: 420px; overflow-y: auto; border: 1px solid var(--glass-border); border-radius: 12px; }
.grading-row { display: flex; align-items: center; padding: 6px 12px; border-bottom: 1px solid var(--glass-border); }
.grading-row:last-child { border-bottom: none; }
.grading-row:nth-child(even) { background: rgba(var(--accent-rgb), 0.03); }
.grading-head-row { background: var(--glass-bg) !important; font-weight: 600; font-size: 11px; color: var(--text-label); position: sticky; top: 0; z-index: 1; }
.g-col { flex-shrink: 0; }
.g-idx { width: 40px; color: var(--text-muted); font-size: 11px; }
.g-name { flex: 1; min-width: 0; color: var(--text-primary); font-size: 13px; }
.g-score { width: 140px; text-align: right; }

.stats-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
.stats-kpi { text-align: center; padding: 12px 8px; border-radius: 12px; background: var(--glass-bg); border: 1px solid var(--glass-border); }
.stats-kpi-value { font-size: 22px; font-weight: 700; color: var(--accent); }
.stats-kpi-label { font-size: 11px; color: var(--text-label); margin-top: 2px; }
.stats-buckets { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.stats-bucket { display: flex; align-items: center; gap: 10px; }
.stats-bucket-name { width: 52px; font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }
.stats-bucket-bar { flex: 1; height: 10px; border-radius: 6px; background: var(--glass-bg); border: 1px solid var(--glass-border); overflow: hidden; }
.stats-bucket-fill { height: 100%; border-radius: 6px; transition: width 0.4s ease; }
.bucket-优秀 { background: linear-gradient(90deg, #34d399, #10b981); }
.bucket-良好 { background: linear-gradient(90deg, #60a5fa, #3b82f6); }
.bucket-及格 { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.bucket-待提高 { background: linear-gradient(90deg, #f87171, #ef4444); }
.stats-bucket-cnt { width: 42px; text-align: right; font-size: 11px; color: var(--text-muted); flex-shrink: 0; }
.stats-ranks { border: 1px solid var(--glass-border); border-radius: 12px; }
.stats-ranks-title { padding: 10px 14px 6px; font-size: 12px; font-weight: 600; color: var(--text-label); }
.stats-rank-grid { max-height: 260px; overflow-y: auto; padding: 0 4px 8px; }
.stats-rank-row { display: flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 8px; font-size: 12px; }
.stats-rank-row.top3 { background: rgba(var(--accent-rgb), 0.08); }
.stats-rank-idx { width: 28px; color: var(--text-muted); text-align: center; font-weight: 600; }
.stats-rank-row.top3 .stats-rank-idx { color: var(--accent); }
.stats-rank-name { flex: 1; min-width: 0; color: var(--text-primary); }
.stats-rank-score { color: var(--accent); font-weight: 600; }


.chart-area { flex: 1; min-width: 0; width: auto; }

.split-layout { display: flex; flex-direction: row; gap: 16px; align-items: flex-start; }
.table-area {
  width: 420px;
  flex-shrink: 0;
  display: flex; flex-direction: column;
}
.table-area .table-header { font-size: 13px; font-weight: 600; color: var(--accent); padding: 10px 14px 6px; border-bottom: 1px solid var(--glass-border); }
.table-scroll { overflow-x: auto; padding: 0 4px 8px 0; scrollbar-width: thin; scrollbar-color: var(--text-label) transparent; }
.score-grid { border-collapse: collapse; font-size: 11px; table-layout: fixed; }
.score-grid th,
.score-grid td {
  box-sizing: border-box;
  height: 36px;
  padding: 0 4px;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score-grid .corner { text-align: left; padding-left: 14px; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; color: var(--text-secondary); }
.score-grid .col-corner { width: 76px; min-width: 76px; max-width: 76px; }
.score-grid .year-head { font-size: 10px; color: var(--text-muted); font-weight: 600; border-bottom: 2px solid var(--glass-border); }
.score-grid td { border-bottom: 1px solid var(--glass-border); color: var(--text-secondary); transition: background 0.15s; }
.score-grid .row-label { text-align: left; padding-left: 14px; font-weight: 600; position: sticky; left: 0; background: var(--glass-bg-solid); z-index: 2; }
.score-grid td.highlight { background: rgba(var(--accent-rgb), 0.10) !important; }
.score-grid th.highlight { background: rgba(var(--accent-rgb), 0.14) !important; }
.score-grid tr:hover td:not(.highlight):not(.row-label) { background: rgba(var(--accent-rgb), 0.06); }
.score-grid tr:hover .row-label,
.score-grid tr:hover .corner { background: linear-gradient(rgba(var(--accent-rgb), 0.06), rgba(var(--accent-rgb), 0.06)), linear-gradient(var(--glass-bg-solid), var(--glass-bg-solid)); }
.table-note { display: flex; gap: 4px; padding: 8px 10px 2px; font-size: 10px; line-height: 1.5; color: var(--text-label); }
.table-note .note-sign { color: var(--accent); }
.table-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
.table-scroll::-webkit-scrollbar-track { background: transparent; }
.table-scroll::-webkit-scrollbar-thumb { background: var(--text-label); border-radius: 3px; }
.table-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

@keyframes table-row-in {
  from { opacity: 0; transform: translateX(10px); }
  to { opacity: 1; transform: translateX(0); }
}
.score-grid tbody tr { animation: table-row-in 0.45s cubic-bezier(0.22, 0.61, 0.36, 1) both; }

@media (max-width: 768px) {
  .kpi-grid { grid-template-columns: 1fr; }
  .half-grid { grid-template-columns: 1fr; }
  .split-layout { flex-direction: column; }
  .table-area { width: 100%; flex-shrink: 1; }
}
</style>

