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
| 意图模型训练 | `python backend/ai_modules/train_model.py` |
| 安装依赖 | `pip install -r requirements.txt`（含 `llama-cpp-python`） |

顺序：先生成数据 → 再启动后端 → 最后启动前端（Vite 代理 `/api` 到 8000）。
也可使用一键脚本：Windows 执行 `start.ps1`，Mac/Linux 执行 `start.sh`（均绑定 127.0.0.1）。

## GitHub Pages 部署（静态前端）

- 前端可构建后发布到 GitHub Pages（纯静态托管，FastAPI 后端需另行部署，GH Pages 无后端/无代理）。
- 构建配置：`vite.config.js` 已设 `base: './'`（相对路径，适配仓库子路径）；路由为 hash 模式（`createWebHashHistory`，深链接无需服务端重写）。
- 前端 API 地址由构建时环境变量 `VITE_API_BASE` 决定（见 `frontend/.env.example`）：默认 `/api`（本地 dev 代理），部署到 GH Pages 时须指向后端绝对地址（如 `https://host/api`）。
- 后端跨域：`backend/app.py` 的 `ALLOWED_ORIGINS` 可通过 `CORS_ORIGINS` 环境变量追加（逗号分隔），部署后端时须包含 GH Pages 站点 origin。
- 自动部署：`.github/workflows/deploy.yml` 在 push master 时构建 `frontend/dist` 并发布 GH Pages（从仓库 Settings→Pages 启用，Source 选 GitHub Actions）。

## 架构

- **后端**：FastAPI + SQLAlchemy + SQLite，入口 `backend/app.py`，路由按角色拆分在 `backend/routes/`。
- **共享模块**：`backend/constants.py`（9 档等级阈值/学期顺序/日期→学期映射/每学期科目集与满分/考试类型/获奖级别，等级与科目的唯一来源）、`backend/cache.py`（TTL 300s 缓存，key=`indices`，写操作后需 `invalidate`）。
- **前端**：Vue3 + Element Plus + ECharts，入口 `frontend/src/main.js`，页面在 `frontend/src/views/`。
- **AI**：`backend/ai_modules/analysis.py`（成长指数加权、预警检测、个性化建议、`batch_growth_profiles(ids, db, light=True)` 批量画像）；`backend/ai_modules/` 另有 AI 能力模块（学情报告/成长叙事/特长发现/心理树洞/预警干预闭环/学习路径/试卷分析/教师问数），由 `backend/routes/ai_api.py`（前缀 `/api/ai`）统一暴露，写操作在 `models.py` 的 `interventions`/`companion_chats`/`learning_plans` 表。
- **本地 LLM 层**：`backend/ai_modules/llm.py` 懒加载单例（`models/qwen2.5-0.5b-instruct-q4_k_m.gguf`，约 490MB，缺失时自动从 hf-mirror 下载，可用 `LLM_MODEL_URL`/`LLM_MODEL_FILE`/`LLM_N_THREADS` 覆盖）；**`generate`/`generate_stream` 全程持有进程级 `_gen_lock` 串行推理**——llama.cpp 单实例并发推理会 GGML_ASSERT 直接 abort 整个进程（曾导致后端整体崩溃、登录全挂），严禁并发调用；`llm_understanding.py`（意图/槽位 LLM 语义理解 + `enforce_scope` 权限收敛，模型不可用降级 `intent_model.py` TF-IDF 质心分类器，语料 `corpus.py`、训练 `train_model.py`）；`fact_blocks.py`（精确数据事实块，数字/名单一律来自数据层防幻觉）；`llm_polish.py`（文案润色，数字/结论禁止改动）；`thinking.py`（SSE 分阶段状态机）；`emotion_companion_llm.py`（树洞 LLM 共情回复 + 危机关键词红线，危机永不交给模型裁决）。流式接口 `/api/ai/ask/stream` 与 `/api/ai/companion/chat/stream` 走 SSE（`event: stage/token/done`），前端 `frontend/src/utils/api.js` 的 `consumeSSE` 消费。

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
- LLM 权重与意图模型工件不入库：`models/*.gguf`（约 490MB，首次启动自动下载）、`backend/ai_modules/model/*.npz|meta.json`（由 `train_model.py` 生成）。改语料后需重训意图模型。
