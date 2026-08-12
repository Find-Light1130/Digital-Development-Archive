from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from backend.models import get_db, Student, Score, EmotionLog, Activity, Award, QualityScore, Attendance
from backend.ai_modules.analysis import compute_growth_profile
from backend.constants import SEMESTER_ORDER, semester_from_date
from backend.routes.auth import get_current_user, can_access_student
import backend.cache as cache

router = APIRouter(prefix="/api/student", tags=["student"])

MOOD_TAGS_ALLOWED = ("开心", "平静", "焦虑", "疲惫", "生气", "悲伤")


def _validate_tags(tags):
    """校验并归一化心情标签：接受逗号串或数组，最多 3 个。"""
    if tags is None or tags == "":
        return None
    if isinstance(tags, list):
        items = [str(t) for t in tags]
    else:
        items = str(tags).split(",")
    items = [t.strip() for t in items if t and t.strip()]
    if len(items) > 3:
        raise HTTPException(400, "tags must be at most 3")
    for t in items:
        if t not in MOOD_TAGS_ALLOWED:
            raise HTTPException(400, f"Unknown tag: {t}")
    return ",".join(items)


def _check_access(user, student_id: int, db: Session):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权访问该学生数据")


@router.get("/profile")
def get_student_profile(student_id: int = Query(..., gt=0),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    profile = compute_growth_profile(student_id, db)
    return {
        "student_id": student.id,
        "name": student.name,
        "grade": student.grade,
        "class": student.class_name,
        "growth_index": profile["growth_index"],
        "aspects": profile["aspects"],
        "strengths": profile["strengths"],
        "weakness": profile["weakness"],
        "suggestions": profile["suggestions"],
        "warnings": profile["warnings"],
    }


@router.get("/search")
def search_students(keyword: str = Query(..., min_length=1, max_length=50),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    kw = keyword.strip()
    if not kw:
        raise HTTPException(400, "keyword is required")
    from backend.routes.auth import user_scope
    q = db.query(Student)
    scope = user_scope(user)
    if scope["student_ids"] is not None:
        q = q.filter(Student.id.in_(scope["student_ids"]))
    elif scope["class_names"] is not None:
        q = q.filter(Student.class_name.in_(scope["class_names"]))
    elif scope["grades"] is not None:
        q = q.filter(Student.grade.in_(scope["grades"]))
    students = q.filter(Student.name.contains(kw)).limit(10).all()
    return [
        {"student_id": s.id, "name": s.name, "grade": s.grade, "class": s.class_name}
        for s in students
    ]


@router.get("/scores")
def get_scores(student_id: int = Query(..., gt=0), semester: str = Query(None),
               limit: int = Query(None, ge=1, le=1000), offset: int = Query(0, ge=0),
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    q = db.query(Score).filter(Score.student_id == student_id)
    if semester:
        q = q.filter(Score.semester == semester)
    q = q.order_by(Score.date, Score.id)
    if offset:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    scores = q.all()
    return [
        {
            "id": s.id, "subject": s.subject,
            "score": s.score if s.score is not None else None,
            "max_score": s.max_score if s.max_score is not None else None, "exam_type": s.exam_type,
            "date": str(s.date), "semester": s.semester,
        }
        for s in scores
    ]


@router.get("/summary")
def get_student_summary(student_id: int = Query(..., gt=0),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    activities = db.query(Activity).filter(Activity.student_id == student_id).order_by(Activity.date).all()
    awards = db.query(Award).filter(Award.student_id == student_id).order_by(Award.date).all()
    sem_hours = {}
    for a in activities:
        if not a.semester:
            continue
        entry = sem_hours.setdefault(a.semester, {"total": 0.0, "practice": 0.0})
        entry["total"] += a.hours or 0
        if a.type == "实践":
            entry["practice"] += a.hours or 0
    semester_stats = []
    for sem in sorted(sem_hours.keys(), key=lambda x: SEMESTER_ORDER.get(x, 0)):
        semester_stats.append({
            "semester": sem,
            "total": round(sem_hours[sem]["total"], 1),
            "practice": round(sem_hours[sem]["practice"], 1),
        })
    return {
        "activities": [
            {"id": a.id, "type": a.type, "hours": a.hours, "date": str(a.date), "semester": a.semester}
            for a in activities
        ],
        "awards": [
            {"id": a.id, "title": a.title, "level": a.level, "date": str(a.date)}
            for a in awards
        ],
        "semester_stats": semester_stats,
    }

@router.get("/semesters")
def get_semesters(student_id: int = Query(..., gt=0),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    if not db.query(Student.id).filter(Student.id == student_id).first():
        raise HTTPException(404, "Student not found")
    rows = db.query(Score.semester).filter(
        Score.student_id == student_id,
        Score.semester != None,
    ).distinct().all()
    return sorted([r[0] for r in rows], key=lambda x: SEMESTER_ORDER.get(x, 0))


@router.get("/quality")
def get_student_quality(student_id: int = Query(..., gt=0), semester: str = Query(None),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    q = db.query(QualityScore).filter(QualityScore.student_id == student_id)
    if semester:
        q = q.filter(QualityScore.semester == semester)
    rows = q.order_by(QualityScore.semester, QualityScore.subject, QualityScore.id).all()
    subjects = {}
    for r in rows:
        entry = subjects.setdefault(r.subject, {})
        entry.setdefault(r.semester, []).append({
            "dimension": r.dimension,
            "score": r.score,
            "grade": r.grade,
        })
    return [
        {"subject": subj, "semesters": [
            {"semester": sem, "dimensions": dims}
            for sem, dims in sorted(sem_map.items(), key=lambda x: SEMESTER_ORDER.get(x[0], 0))
        ]}
        for subj, sem_map in subjects.items()
    ]


@router.get("/emotions")
def get_emotions(student_id: int = Query(..., gt=0),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    if not db.query(Student.id).filter(Student.id == student_id).first():
        raise HTTPException(404, "Student not found")
    logs = db.query(EmotionLog).filter(EmotionLog.student_id == student_id).order_by(EmotionLog.date).all()
    return [{
        "id": e.id, "date": str(e.date), "emotion_level": e.emotion_level,
        "tags": e.tags.split(",") if e.tags else [],
    } for e in logs]


@router.post("/emotion")
def submit_emotion(student_id: int, date: str, emotion_level: int, tags: str = None,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_access(user, student_id, db)
    if student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if emotion_level < 1 or emotion_level > 3:
        raise HTTPException(400, "emotion_level must be 1-3")
    norm_tags = _validate_tags(tags)
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid date, expected YYYY-MM-DD")
    if parsed_date > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    if user.role == "student" and user.student_id != student_id:
        raise HTTPException(403, "学生账号仅可提交本人情绪记录")
    if not semester_from_date(student.grade, parsed_date):
        raise HTTPException(400, "Date is out of the student's academic calendar")
    existing = db.query(EmotionLog).filter(
        EmotionLog.student_id == student_id,
        EmotionLog.date == parsed_date,
    ).first()
    if existing:
        existing.emotion_level = emotion_level
        existing.tags = norm_tags
        db.add(existing)
        db.commit()
        cache.invalidate("indices")
        return {"status": "ok", "updated": True}
    log = EmotionLog(student_id=student_id, date=parsed_date, emotion_level=emotion_level, tags=norm_tags)
    db.add(log)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "updated": False}


@router.get("/attendance")
def get_student_attendance(student_id: int = Query(..., gt=0),
                           user=Depends(get_current_user), db: Session = Depends(get_db)):
    """学生出勤明细：逐月出勤率 + 最近缺勤日期列表。"""
    _check_access(user, student_id, db)
    if not db.query(Student.id).filter(Student.id == student_id).first():
        raise HTTPException(404, "Student not found")
    rows = db.query(Attendance).filter(Attendance.student_id == student_id).order_by(Attendance.date).all()
    monthly = {}
    absences = []
    for r in rows:
        ym = r.date.strftime("%Y-%m")
        m = monthly.setdefault(ym, {"total": 0, "present": 0})
        m["total"] += 1
        if r.present:
            m["present"] += 1
        elif r.date <= datetime.now().date():
            absences.append(str(r.date))
    month_stats = [{
        "month": ym,
        "total": m["total"],
        "present": m["present"],
        "absent": m["total"] - m["present"],
        "rate": round(m["present"] / m["total"] * 100, 1) if m["total"] else 0,
    } for ym, m in sorted(monthly.items())]
    total = sum(m["total"] for m in monthly.values())
    present = sum(m["present"] for m in monthly.values())
    return {
        "student_id": student_id,
        "total": total,
        "absent": total - present,
        "rate": round(present / total * 100, 1) if total else 0,
        "monthly": month_stats,
        "absences": absences[-20:],
    }
