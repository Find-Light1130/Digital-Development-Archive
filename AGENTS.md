# AGENTS.md

## 命令

| 操作 | 命令 |
|------|------|
| 生成模拟数据 | `python data/raw_data_gen.py` |
| 启动后端 | `uvicorn backend.app:app --reload --port 8000` |
| 启动前端 | `cd frontend && npm run dev` |
| 构建前端 | `cd frontend && npm run build` |
| 后端接口测试（需先启动后端） | `python test/backend_tests.py` |
| 前端冒烟测试 | `node test/frontend_tests.js` |
| 数据/画像验证 | `python test/verify.py`、`python test/check.py` |
| 性能验证 | `python test/perf_check.py` |

顺序：先生成数据 → 再启动后端 → 最后启动前端（Vite 代理 `/api` 到 8000）。
也可使用一键脚本：Windows 执行 `start.ps1`，Mac/Linux 执行 `start.sh`（均绑定 127.0.0.1）。

## 架构

- **后端**：FastAPI + SQLAlchemy + SQLite，入口 `backend/app.py`，路由按角色拆分在 `backend/routes/`。
- **共享模块**：`backend/constants.py`（9 档等级阈值/学期顺序/日期→学期映射/每学期科目集与满分/考试类型/获奖级别，等级与科目的唯一来源）、`backend/cache.py`（TTL 300s 缓存，key=`indices`，写操作后需 `invalidate`）。
- **前端**：Vue3 + Element Plus + ECharts，入口 `frontend/src/main.js`，页面在 `frontend/src/views/`。
- **AI**：`backend/ai_modules/analysis.py`（成长指数加权、预警检测、个性化建议、`batch_growth_profiles(ids, db, light=True)` 批量画像）；`backend/ai_modules/` 另有 AI 能力模块（学情报告/成长叙事/特长发现/心理树洞/预警干预闭环/学习路径/试卷分析/教师问数），由 `backend/routes/ai_api.py`（前缀 `/api/ai`）统一暴露，写操作在 `models.py` 的 `interventions`/`companion_chats`/`learning_plans` 表。

## 数据

- 数据库 `data/school.db`（SQLite），由 `raw_data_gen.py` 生成 1050 条学生样本。
- CSV 导出在 `data/sample_data/`。
- 表：`students`, `scores`（九大学科）, `quality_scores`（音体美信多维评估）, `attendance`, `emotions`（含可空 `tags` 心情标签列）, `activities`, `awards`, `exam_plans`（考试规划，状态 `planned→conducted→graded`）, `interventions`（预警干预闭环）, `companion_chats`（心理树洞）, `learning_plans`（个性化学习路径）。
- `class_name` 格式为 `"初一1班"`（年级+序号+班），前端下拉与此格式一致，正则 `^[初高][一二三]\d+班$`。
- 索引：`ix_students_class`、`ix_scores_student_semester`、`ix_quality_student_semester`、`ix_exam_plans_grade_status`、`ix_interventions_status`、`ix_companion_student`、`ix_learning_plan_student`。

## 错误契约

- 查询不存在资源 → 404（`{"detail": "..."}`）；`student_id` 用 `Query/Path(..., gt=0)`（违规 422）；`class_name` 不合法 → 400。
- POST 校验：未来日期、NaN/越界数值、学业日历超范围（`constants.semester_from_date`）均拒绝；同日同类型幂等更新。
- 成绩录入校验：科目须在该生年级学期科目集内（`constants.semester_subjects`）、`0≤score≤满分`（`constants.subject_max`）、`exam_type∈{月考,期中,期末}`；批量任一非法整批拒绝。
- 考试规划校验：`exam_type∈{月考,期中,期末}`、科目须在 `constants.subject_max` 内、年级 ∈ `{初一,初二,初三}`、考试日期须能映射到学期（`constants.semester_from_date` 非空）且科目在该学期科目集内；`planned` 可删除/进行（`exam_date≤今天`），`conducted/graded` 不可删。教师批阅须恰好覆盖本班学生名单。
- 前端不解析 `{error}` 字段，按 `status` 处理。

## 注意事项

- 修改 AI 权重在 `analysis.py` 的 `GROWTH_WEIGHTS` 字典中调整。
- 修改等级阈值/学期映射/每学期科目集与满分在 `backend/constants.py` 中调整（不要在各路由或生成脚本中另写一份）。
- `emotions.tags` 列由 `app.py` 启动时幂等迁移（ALTER TABLE），无需重建库；若删库重建则直接含该列。
- 若数据库损坏或需重建，删除 `data/school.db` 后重新运行 `raw_data_gen.py`。
- 后端测试默认要求后端已在 8765 端口运行（见 `test/backend_tests.py` 顶部说明）。
