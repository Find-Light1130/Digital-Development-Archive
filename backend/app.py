import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.models import init_db, User
from backend.routes.auth import router as auth_router, _hash_password
from backend.routes.student_api import router as student_router
from backend.routes.teacher_api import router as teacher_router
from backend.routes.admin_api import router as admin_router
from backend.routes.ai_api import router as ai_router

_DOCS_ENABLED = os.environ.get("ENABLE_DOCS") == "1"
app = FastAPI(
    title="AI数字智育系统",
    version="1.0.0",
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: http: https:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response


app.include_router(student_router)
app.include_router(teacher_router)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(ai_router)


@app.on_event("startup")
def on_startup():
    init_db()
    _migrate_users()
    _migrate_emotion_tags()
    _migrate_indexes()
    _seed_default_admin()
    _seed_demo_exam_plans()
    try:
        from backend.routes.admin_api import start_cache_warmup
        start_cache_warmup()
    except Exception:
        pass


def _migrate_indexes():
    """幂等迁移：为既有库补充 scores 幂等反查索引（CREATE INDEX IF NOT EXISTS）。"""
    from backend.models import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_scores_student_subject_exam_date "
            "ON scores (student_id, subject, exam_type, date)"
        ))
        db.commit()
    finally:
        db.close()


def _migrate_emotion_tags():
    """幂等迁移：emotions 表补充 tags 列（SQLite ALTER TABLE）。"""
    from backend.models import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        cols = [row[1] for row in db.execute(text("PRAGMA table_info(emotions)")).all()]
        if "tags" not in cols:
            db.execute(text("ALTER TABLE emotions ADD COLUMN tags VARCHAR"))
            db.commit()
    finally:
        db.close()


def _migrate_users():
    """幂等迁移：users 表补充 class_name / grade 列（SQLite ALTER TABLE）。"""
    from backend.models import SessionLocal, User
    from sqlalchemy import text
    db = SessionLocal()
    try:
        cols = [row[1] for row in db.execute(text("PRAGMA table_info(users)")).all()]
        if "class_name" not in cols:
            db.execute(text("ALTER TABLE users ADD COLUMN class_name VARCHAR"))
        if "grade" not in cols:
            db.execute(text("ALTER TABLE users ADD COLUMN grade VARCHAR"))
        db.commit()
    finally:
        db.close()


def _seed_default_admin():
    """种子化默认管理员账号：仅首次创建 admin / admin123（控制台提示尽快改密），不再每次启动重置密码。"""
    from backend.models import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            db.add(User(
                username="admin",
                password_hash=_hash_password("admin123"),
                role="admin",
                name="系统管理员",
                status="approved",
                created_at=datetime.now(),
            ))
            db.commit()
            print("[startup] 已创建默认管理员 admin / admin123，请登录后尽快修改密码。")
    finally:
        db.close()


def _seed_demo_exam_plans():
    """幂等种子：若 exam_plans 为空，为初一下学期生成几场演示考试规划，
    便于演示 管理员下达 → 年级组长进行 → 教师批阅 闭环。"""
    from backend.models import SessionLocal, ExamPlan
    from backend.constants import EXAM_TYPES, MAX_SCORES, SUBJECTS_BY_SEMESTER, semester_from_date
    from datetime import date, timedelta, datetime
    db = SessionLocal()
    try:
        if db.query(ExamPlan).first():
            return
        today = date.today()
        admin = db.query(User).filter(User.role == "admin").first()
        created_by = admin.id if admin else None
        # 以 初一下 为当前学期（教师 demo 为初一1班，年级组长为初一年级）
        semester = "初一下"
        subjects = SUBJECTS_BY_SEMESTER[semester]
        exam_types = EXAM_TYPES
        count = 0
        # 期中考（已进行，教师可批阅）
        for idx, subject in enumerate(subjects[:3]):
            exam_date = today - timedelta(days=20 - idx * 3)
            if semester_from_date("初一", exam_date) != semester:
                continue
            db.add(ExamPlan(
                exam_type=exam_types[1], subject=subject, grade="初一",
                exam_date=exam_date, semester=semester, status="conducted",
                created_by=created_by, conducted_at=datetime.now(),
            ))
            count += 1
        # 期末考（规划中，年级组长可进行）
        for idx, subject in enumerate(subjects[:2]):
            exam_date = today + timedelta(days=7 + idx)
            if semester_from_date("初一", exam_date) != semester:
                continue
            db.add(ExamPlan(
                exam_type=exam_types[2], subject=subject, grade="初一",
                exam_date=exam_date, semester=semester, status="planned",
                created_by=created_by,
            ))
            count += 1
        if count:
            db.commit()
            print(f"[startup] 已生成 {count} 场演示考试规划（初一 · 初一下）")
    except Exception as e:
        db.rollback()
        print(f"[startup] 生成演示考试规划失败: {e}")
    finally:
        db.close()


@app.get("/")
def root():
    return {"name": "AI数字智育系统", "version": "1.0.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
