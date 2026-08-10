# AI数字智育系统 架构文档

> 更新日期：2026-07-31
> 说明：本文件描述系统当前实现的技术架构、数据模型与核心算法，供后续开发维护参考。

## 1. 总体架构

```
┌──────────────────────────────────────────────────────────┐
│ 前端（Vue 3 + Element Plus + ECharts，端口 3000）           │
│  StudentDashboard / TeacherDashboard / AdminDashboard      │
│  StudentDetail + 组件（ScoreChart / RadarChart / ...）     │
│  utils/api.js（axios）→ 请求 /api/*                        │
└───────────────┬──────────────────────────────────────────┘
                │ Vite 开发服务器代理 /api → 127.0.0.1:8000
┌───────────────▼──────────────────────────────────────────┐
│ 后端（FastAPI，端口 8000，绑定 127.0.0.1）                  │
│  app.py                   入口（CORS / 安全响应头）          │
│  constants.py             共享常量（9 档等级/学期顺序/日期映射）│
│  cache.py                 TTL 缓存（300s）                   │
│  routes/student_api.py    学生端 API                       │
│  routes/teacher_api.py    教师端 API                       │
│  routes/admin_api.py      管理端 API（缓存 + SQL 聚合）      │
│  ai_modules/analysis.py   AI 分析算法                      │
└───────────────┬──────────────────────────────────────────┘
                │ SQLAlchemy（PRAGMA foreign_keys=ON）
┌───────────────▼──────────────────────────────────────────┐
│ SQLite：data/school.db                                    │
│  students / scores / quality_scores / attendance /       │
│  emotions / activities                                    │
└───────────────────────────────────────────────────────────┘
```

## 2. 前端结构

- 路由（`frontend/src/router/index.js`）：`/student`、`/teacher`、`/teacher/student/:id`、`/admin`。
- 页面组件（`frontend/src/views/`）：
  - `StudentDashboard.vue`：学生端首页（输入 ID 查询成长档案）。
  - `StudentDetail.vue`：教师端下钻的学生详情页。
  - `TeacherDashboard.vue`：班级面板（KPI、预警、雷达、掌握率、趋势、对照表）。
  - `AdminDashboard.vue`：全校驾驶舱。
- 通用组件（`frontend/src/components/`）：
  - `ScoreChart.vue`：单科成绩折线图 + 成绩对照表（支持点击查看考试详情）。
  - `RadarChart.vue`：成长画像雷达图。
  - `EmotionChart.vue`：情绪曲线。
  - `ExamReview.vue`：考试详细总结弹窗。
- 工具（`frontend/src/utils/`）：
  - `api.js`：axios 实例，`baseURL = '/api'`。
  - `colors.js`：主题相关工具（`themeTooltip` / `themePalette` / `subjectColor`）。

### 主题系统

- 深色为默认主题，浅色通过 `document.documentElement.setAttribute('data-theme', 'light')` 切换。
- 全部 CSS 变量定义在 `App.vue` 的 `:root` 与 `:root[data-theme="light"]`。
- ECharts 图表读取主题变量：`themeTooltip()` / `themePalette()`；各图表 `option` 内 `void themeKey.value` 以在切换主题时重新计算。

### 班级选择持久化（教师端）

- 班级变化时同步 `?class=` 查询参数并写入 `sessionStorage('teacherClass')`。
- 挂载时优先读取 `route.query.class`，其次 `sessionStorage`。
- 学生详情返回：优先 `router.back()`，兜底跳回 `/teacher?class=`。

## 3. 数据模型（SQLite）

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `students` | id, name, grade, class(班级), age | 学生主表，`class_name` 建索引 |
| `scores` | id, student_id, subject, score, max_score, exam_type, date, semester | 成绩记录（仅九大学科，音体美信已移除），`student_id+semester` 复合索引 |
| `quality_scores` | id, student_id, subject, semester, dimension, score, grade | 音体美信多维评估（每科 4 维度，A+~C- 九档等级），`student_id+semester` 复合索引 |
| `attendance` | id, student_id, date, present | 考勤记录，`student_id` 建索引 |
| `emotions` | id, student_id, date, emotion_level(1-3) | 情绪日志，`student_id` 建索引 |
| `activities` | id, student_id, type, hours, date, semester | 实践活动记录，`student_id` 建索引 |
| `awards` | id, student_id, name, level, date | 获奖记录，`student_id` 建索引 |

- 数据库路径：`data/school.db`；由 `data/raw_data_gen.py` 生成并写入。
- SQLite 连接时启用外键约束（`PRAGMA foreign_keys=ON`）。
- 样本规模：约 1050 名学生；成绩约 14.7 万条、素质评估约 6.72 万条、考勤约 13.65 万条、情绪约 2.73 万条、活动约 1.37 万条。

## 4. 后端分层

### 4.1 入口 `backend/app.py`

- 创建 FastAPI 应用，挂载三个路由模块（student/teacher/admin，前缀 `/api/...`）。
- 中间件：
  - CORS：仅允许 `http://localhost:3000` 与 `http://127.0.0.1:3000`。
  - 安全响应头：`X-Content-Type-Options`、`X-Frame-Options`、`X-XSS-Protection`、`Cache-Control`、`Referrer-Policy`、`Permissions-Policy`、`Content-Security-Policy`。
- 直接运行（`python backend/app.py`）时绑定 `127.0.0.1:8000`。

### 4.2 路由模块

- `routes/student_api.py`：成长画像、成绩、学期、素质评估、情绪（含 POST 提交）、报告、建议、活动。
- `routes/teacher_api.py`：班级学期、班级总览（含趋势/掌握率/预警）、班级素质评估、学生详情、行为事件录入。
- `routes/admin_api.py`：全校概览、年级对比、学科掌握率（SQL 聚合）；成长指数结果缓存 300 秒（`backend/cache.py`，key=`indices`）。

### 4.3 输入校验与错误契约（安全）

- 统一错误契约：查询资源不存在返回 `HTTPException(404, "Student not found"/"Class not found")`；参数非法返回 400/422；前端按 `status` 处理，不再解析 `{error}` 字段。
- `student_id` 均声明为 `Query(..., gt=0)` / `Path(..., gt=0)`，非法值自动 422。
- POST 接口 `date` 使用 `datetime.strptime(..., "%Y-%m-%d")` 严格校验，并拒绝未来日期（超时区当天）；`add_student_event` 还校验数值有限（拒 NaN）、范围（0~24）以及学业日历（`constants.semester_from_date`，超出返回 400）。
- 学生/班级不存在返回 404；`class_name` 须匹配 `^[初高][一二三]\d+班$`（否则 400）。
- 数值范围校验（如 `emotion_level ∈ [1,3]`）。

### 4.4 共享常量（`backend/constants.py`）

- `GRADE_LEVELS`：素质等级 9 档阈值（A+≥93 … C-<45），与 `raw_data_gen.py`、`teacher_api.py`、前端 `QualityChart.vue` 唯一对齐来源。
- `SEMESTER_ORDER`：初一上…初三下 的排序与索引。
- `semester_from_date(grade, date)`：按年级起始学期与固定日期区间（9-1 开学 / 2-16 开学）推导学期，超范围返回 `None`。

## 5. AI 分析（`backend/ai_modules/analysis.py`）

### 5.1 成长指数

- 五个维度：学习能力、心理健康、体育健康、实践能力、兴趣发展。
- 权重定义在 `GROWTH_WEIGHTS` 字典；综合指数 = 各维度加权平均（0-100）。

### 5.2 知识掌握率

- 每科目取最近 3 次考试（按 `date` 排序）得分率均值；无成绩科目默认 50。

### 5.3 整体趋势

- `_overall_trend(vals)`：对得分率序列做一元线性回归，斜率 < -1.0/次 判「下滑」、> +1.0/次 判「上升」、否则「平稳」。
- 替代了旧的「前 2 次 vs 后 2 次均值比较」逻辑。

### 5.4 预警规则（`_detect_warnings`）

- 科目在**最近一个学期**所有考试单调递减（`_is_monotonic_decreasing`）→ `{科目}本学期成绩持续下滑，需关注`。
- 否则整体斜率下降 → `{科目}成绩整体呈下滑趋势，建议关注`。

### 5.5 个性化建议（`_dynamic_suggestions`）

- 按「持续下滑 / 整体下滑 / 上升」与各维度短板分档，从模板池随机抽取（每档 2-6 条）。
- 各维度独立建议：体育（运动量）、心理（情绪调节）、实践（动手实验）、兴趣（跨学科思维）。

## 6. 考试时间安排

`data/raw_data_gen.py` 中 `EXAM_WEEKS = [4, 8, 10, 14, 18]`，依次对应 月考/月考/期中/月考/期末：

| 周序 | 4 | 8 | 10 | 14 | 18 |
| --- | --- | --- | --- | --- | --- |
| 考试 | 月考 | 月考 | 期中 | 月考 | 期末 |
| 9 月开学（9.1） | 9 月末 | 10 月末 | 11 月中 | 12 月初 | 1 月 |
| 2 月开学（2.16） | 3 月中 | 4 月中 | 4 月底 | 5 月底 | 6 月底 |

- 保证每学期月考月份唯一（9/10/12、3/4/5）。
- 成绩趋势标签格式为「学期·考试」（如 `初一上·期中`）；后端 `_unique_labels` 对重复标签兜底追加 `·MM-DD` 保证唯一。

## 7. 请求流程示例

1. 学生端输入 ID → `GET /api/student/profile?student_id=214`。
2. 后端 `compute_growth_profile` 批量化加载成绩/情绪/考勤/活动 → 计算指数、预警、建议。
3. 前端展示雷达图 + 建议列表；`ScoreChart` 请求 `GET /api/student/scores?student_id=214&semester=初一下`。
4. 点击折线图数据点 → `ExamReview` 弹窗展示该次考试各科成绩。

## 8. 已知限制与后续方向

详见 `issues/未解决问题清单.md`。主要方向：登录/角色权限系统（暂缓）、ECharts 按需引入减小包体、Firefox 滚动条样式、更多考试场景下标签布局的回归验证。
