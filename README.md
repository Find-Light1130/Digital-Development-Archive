# AI数字智育系统

融合成绩、考勤、心理、体育等多源数据，构建学生个人成长画像，利用 AI 分析与规则引擎实现个性化学习建议与实时预警。面向**学生端、教师端、管理端**三个视角，采用模拟数据驱动，聚焦系统设计与演示。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Element Plus + ECharts（vite 构建） |
| 后端 | Python（FastAPI）+ SQLAlchemy |
| 数据库 | SQLite（`data/school.db`） |
| AI/ML | 规则引擎 + 加权评分（`backend/ai_modules/analysis.py`），暂未接入外部 LLM |
| 数据 | Python（NumPy）生成模拟数据 |

## 功能概览

| 端 | 功能 |
| --- | --- |
| 首页 `/` | 系统介绍、四大角色入口、演示账号引导 |
| 登录 `/login` | 用户名密码登录，连续失败限流，会话 7 天 |
| 注册 `/register` | 学生 / 教师自助注册，需管理员审核 |
| 帮助中心 `/help` | 快速开始、角色指南、账号安全与常见问题 |
| 学生端 `/student` | 成长指数、学习报告、成绩趋势（折线图+对照表）、成长画像（雷达图）、情绪曲线（含心情标签、连续记录天数）、情绪日历（热力图，点击日期记录/修改心情）、综合素质（活动/获奖）、个性化建议（打字机式动效）、考试详情弹窗 |
| 教师端 `/teacher` | 班级总览 KPI、关注学生预警列表、班级成长画像、各科平均掌握率、各科成绩趋势（tooltip 含最高/最低/平均）、阅卷端·答题卡（考试规划批阅自动录入，同键幂等覆盖）、获奖登记（含撤销）、数据分布下钻（点击柱子查看学生）、卡片折叠、学生详情下钻 |
| 年级组长 `/grade-leader` | 本年级各班数据总览、年级对比、本年级教师账号审核、本年级考试规划（到日考试可「进行」） |
| 管理端 `/admin` | 全校概览、年级对比、各班平均成长指数、各年级详情表、全校数据分布下钻、用户审核管理、考试规划（下达/删除/进行） |

## 登录与账号

- 角色模型：学生（student）、教师（teacher）、年级组长（grade_leader）、管理员（admin）。
- **学生 / 教师**自助注册后状态为「待审核」，审核通过方可登录；**年级组长 / 管理员**账号由管理员在管理端创建。
- 密码规则：至少 8 位、最多 128 位，且同时包含字母和数字；使用加盐 PBKDF2 哈希存储。
- 登录连续失败 5 次触发 15 分钟限流（429）；会话默认 7 天有效。
- 修改密码：登录后点击右上角用户名 →「修改密码」，修改成功后全部会话失效需重新登录。
- 演示账号（由 `data/raw_data_gen.py` 与后端启动时自动创建）：

| 角色 | 用户名 | 密码 | 绑定 |
| --- | --- | --- | --- |
| 学生 | `stu_demo` | `Student123` | 学生证号 1 |
| 教师 | `teacher_demo` | `Teacher123` | 初一1班 |
| 年级组长 | `grade_leader_demo` | `Leader123` | 初一年级 |
| 管理员 | `admin` | `admin123` | 系统管理员（仅首次创建） |

## 项目结构

```
School Managing System/
├── backend/                     # FastAPI 后端
│   ├── app.py                   # 入口（CORS/CSP/安全头）
│   ├── models.py                # ORM 数据模型（students/scores/quality_scores/attendance/emotions/activities/awards）
│   ├── constants.py             # 共享常量（9 档等级阈值 / 学期顺序 / 日期→学期映射 / 每学期科目集与满分）
│   ├── cache.py                 # 线程安全 TTL 缓存
│   ├── routes/
│   │   ├── auth.py            # 注册/登录/会话/改密/角色范围
│   │   ├── student_api.py     # 学生端 API
│   │   ├── teacher_api.py     # 教师端 API（成绩/获奖/活动录入、分布下钻）
│   │   └── admin_api.py       # 管理端 API
│   └── ai_modules/
│       └── analysis.py          # 成长指数/AI 分析/预警/建议
├── frontend/                    # Vue3 前端
│   └── src/
│       ├── components/          # ScoreChart / RadarChart / QualityChart / EmotionChart / MoodCalendar / ExamReview / ComprehensiveCard / TypedSuggestions
│       ├── views/               # Home / Login / Register / HelpCenter / StudentDashboard / TeacherDashboard / StudentDetail / GradeLeaderDashboard / AdminDashboard
│       ├── router/index.js      # 路由（含角色鉴权守卫）
│       └── utils/               # api.js（axios 封装）、auth.js（令牌/角色）、colors.js（主题工具）
├── data/
│   ├── school.db                # SQLite 数据库
│   ├── raw_data_gen.py          # 模拟数据生成脚本
│   └── sample_data/             # CSV 导出
├── docs/                        # 架构与设计文档
│   ├── architecture.md
│   ├── demo_plan.md
│   └── ui_prototypes/
├── issues/                      # 问题与修复文档
│   ├── 未解决问题清单.md
│   └── 修复与安全升级计划.md
├── test/                        # 验证与自动化测试
│   ├── backend_tests.py         # 后端接口自动化测试
│   ├── frontend_tests.js        # 前端构建冒烟测试
│   ├── check.py
│   ├── verify.py
│   └── perf_check.py
├── AGENTS.md                    # 开发约定与常用命令
├── start.ps1 / start.sh         # 一键启动脚本
└── README.md
```

## 快速开始

顺序：先生成数据 → 再启动后端 → 最后启动前端（Vite 代理 `/api` 到 `127.0.0.1:8000`）。

```bash
# 1. 生成模拟数据（首次或需重建时）
python data/raw_data_gen.py

# 2. 启动后端（依赖见 backend/requirements.txt）
uvicorn backend.app:app --reload --port 8000

# 3. 启动前端
cd frontend
npm install
npm run dev        # 默认 http://localhost:3000
```

也可使用一键脚本：Windows 执行 `start.ps1`，Mac/Linux 执行 `start.sh`。

## 核心 API

基础前缀 `/api`，前端经 Vite 代理转发到 `127.0.0.1:8000`。

| 方法 | 路径 | 参数 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | `username, password, role, name?, student_id?` | 注册（学生/教师），返回待审核 |
| POST | `/api/auth/login` | `username, password` | 登录，返回 `token` 与用户信息 |
| GET | `/api/auth/me` | — | 当前登录用户信息 |
| POST | `/api/auth/logout` | — | 退出登录，销毁会话 |
| POST | `/api/auth/change_password` | `old_password, new_password` | 修改密码（全部会话失效） |
| GET | `/api/student/profile` | `student_id` | 学生成长画像（指数/维度/强弱/建议/预警） |
| GET | `/api/student/scores` | `student_id`, `semester?` | 学生成绩列表 |
| GET | `/api/student/semesters` | `student_id` | 学生各学期列表 |
| GET | `/api/student/emotions` | `student_id` | 情绪记录列表（含心情标签） |
| GET | `/api/student/summary` | `student_id` | 综合素质摘要（活动/获奖/分学期时长） |
| GET | `/api/student/quality` | `student_id` | 素质评估（音体美信×各学期×维度，9 档等级） |
| POST | `/api/student/emotion` | `student_id, date, emotion_level, tags?` | 提交情绪日志（1-3，同日幂等，tags 至多 3 个逗号分隔） |
| GET | `/api/teacher/class/semesters` | `class_name` | 班级可用学期 |
| GET | `/api/teacher/class/students` | `class_name` | 班级花名册 + 当前学期科目/满分（批量录入网格） |
| GET | `/api/teacher/class/overview` | `class_name`, `semester?` | 班级总览（含趋势/掌握率/关注列表） |
| GET | `/api/teacher/class/quality` | `class_name` | 班级素质评估（各科各学期维度均值） |
| GET | `/api/teacher/class/distribution` | `class_name, metric, subject?` | 班级成长/得分分布（分桶） |
| GET | `/api/teacher/class/distribution/students` | `class_name, metric, subject?, bucket` | 班级分布下钻（桶内学生明细） |
| GET | `/api/teacher/student/{id}/details` | — | 学生详情（教师端） |
| POST | `/api/teacher/student_event` | `student_id, date, event_type, value, ...` | 录入学生行为事件（同日同类型幂等） |
| GET | `/api/teacher/exam_plans` | `class_name` | 阅卷端：本班年级已进行/已批阅考试 + 学生名单与已有分数 |
| POST | `/api/teacher/exam_plans/{id}/grade` | `{class_name, scores:[{student_id, score}]}` | 批阅答题卡自动录入（同键幂等覆盖，超分/非本班整批拒绝） |
| POST | `/api/teacher/scores` | `student_id, subject, exam_type, date, score` | 单条成绩录入（同键幂等覆盖，超分/错科/越界拒绝，兼容保留） |
| POST | `/api/teacher/scores/delete` | `student_id, subject, exam_type, date` | 删除成绩记录（更正误录） |
| POST | `/api/teacher/award` | `student_id, title, level, date` | 获奖登记（level：校级/区级/市级/省级） |
| POST | `/api/teacher/award/delete` | `award_id` | 删除获奖记录 |
| GET | `/api/admin/school/overview` | — | 全校概览 |
| GET | `/api/admin/grade_comparison` | — | 年级对比 |
| GET | `/api/admin/subject_mastery` | — | 各年级各学科平均掌握率 |
| GET | `/api/admin/distribution` | `metric, subject?, grade?` | 全校/年级分布（分桶） |
| GET | `/api/admin/distribution/students` | `metric, subject?, grade?, bucket` | 全校分布下钻（桶内学生明细） |
| GET | `/api/admin/users` | `status?` | 用户列表（年级组长仅本年级教师） |
| POST | `/api/admin/users` | `username, password, role, name?, class_name?, grade?` | 管理员创建教师/年级组长 |
| POST | `/api/admin/users/{id}/approve` | — | 审核通过账号 |
| POST | `/api/admin/users/{id}/reject` | — | 驳回账号（销毁其会话） |
| POST | `/api/admin/users/{id}/class` | `class_name` | 管理员设置教师班级 |
| GET | `/api/admin/exam_plans` | `status?` | 考试规划列表（年级组长仅本年级） |
| POST | `/api/admin/exam_plans` | `exam_type, subject, grade, exam_date` | 下达考试规划（科目/日期须在学业日历内） |
| DELETE | `/api/admin/exam_plans/{id}` | — | 删除待进行规划（管理员） |
| POST | `/api/admin/exam_plans/{id}/conduct` | — | 进行考试（planned→conducted，需到考试日期） |

> 错误契约：未登录 401；越权 403；查询不存在资源 404（`{"detail": ...}`），参数非法 400/422；`student_id` 须为正整数。

## 数据说明

- 数据库：`data/school.db`（SQLite），由 `data/raw_data_gen.py` 生成 1050 名学生样本。
- 表：`students`（学生）、`scores`（成绩，仅九大学科）、`quality_scores`（音体美信多维评估）、`attendance`（考勤）、`emotions`（情绪，含 `tags` 心情标签列）、`activities`（活动）、`awards`（获奖）、`exam_plans`（考试规划，管理端下达 → 年级组长进行 → 教师批阅）。
- `class_name` 格式为 `"初一1班"`（年级+序号+班），前端下拉与其一致。
- 考试安排：`EXAM_WEEKS = [4, 8, 10, 14, 18]`（见 `data/raw_data_gen.py`），依次为 月考/月考/期中/月考/期末。9 月开学学期：月考 9/10 月末、期中 11 月中、月考 12 月初、期末 1 月；2 月开学学期（2.16）：月考 3/4 月中、期中 4 月底、月考 5 月底、期末 6 月底。
- 成绩趋势标签格式为「学期·考试」（如 `初一上·期中`），后端 `_unique_labels` 对重复标签兜底追加 `·MM-DD` 保证唯一。

## AI 分析说明

核心逻辑在 `backend/ai_modules/analysis.py`：

- **成长指数**：多维加权（`GROWTH_WEIGHTS`），维度含学习能力、心理健康、体育健康、实践能力、兴趣发展。
- **知识掌握率**：按 `date` 排序取最近 3 次考试得分率均值。
- **整体趋势**：对全部成绩做线性回归斜率（`_overall_trend`），阈值 ±1.0/次判升降。
- **预警**：整学期单调递减 → `{科目}本学期成绩持续下滑`；否则整体斜率下降 → `{科目}成绩整体呈下滑趋势`。
- **个性化建议**：按科目/维度模板化生成（`_dynamic_suggestions`）。

> 修改权重只需调整 `analysis.py` 中的 `GROWTH_WEIGHTS` 字典。

## 主题与视觉

- 支持深/浅两套主题，主题变量定义在 `frontend/src/App.vue` 的 `:root` / `:root[data-theme="light"]`。
- ECharts 图表通过 `frontend/src/utils/colors.js` 的 `themeTooltip()` / `themePalette()` 读取主题变量，切换主题即时刷新。

## 测试与验证

```bash
python test/backend_tests.py   # 后端接口自动化测试（199 项：错误契约/幂等/学期推导/9 档等级/账号安全/角色隔离/成绩获奖录入/分布下钻）
node test/frontend_tests.js    # 前端构建冒烟测试（构建 + 产物 + 源码静态检查 + 检修回归）
python test/verify.py          # 数据与 AI 逻辑校验（真检查，失败非零退出）
python test/check.py           # 数据库结构抽查（真检查，失败非零退出）
python test/perf_check.py      # 批量画像性能验证（真检查，失败非零退出）
cd frontend && npm run build   # 前端构建（编译校验）
```

> 本项目为原型系统，使用模拟数据，旨在验证多维数据融合与智能分析的可行性。详细的架构说明见 `docs/architecture.md`，演示脚本见 `docs/demo_plan.md`，未解决问题见 `issues/未解决问题清单.md`。
