from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime
import math
from backend.models import get_db, Student, Score, SubjectStats, User, ExamPlan, Session as AuthSession
from backend.ai_modules.analysis import batch_growth_profiles
from backend.constants import SEMESTER_ORDER, EXAM_TYPES, MAX_SCORES, SUBJECTS_BY_SEMESTER, semester_from_date, semester_ranges, semester_subjects
from backend.routes.teacher_api import _bucket, _student_bucket_label, SUBJECT_MAX_SCORES
from backend.routes.auth import (
    get_current_user, _user_payload_admin, _validate_credentials, _hash_password, user_scope,
)
import backend.cache as cache
import threading
from fastapi import Header

router = APIRouter(prefix="/api/admin", tags=["admin"])

_indices_lock = threading.Lock()

ROLE_LABELS = {"student": "学生", "teacher": "教师", "grade_leader": "年级组长", "admin": "管理员"}

GRADE_NAMES = ("初一", "初二", "初三")


def _require_admin(authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.status != "approved" or user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


def _require_admin_or_grade_leader(authorization: str = Header(None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.status != "approved" or user.role not in ("admin", "grade_leader"):
        raise HTTPException(403, "需要管理员或年级组长权限")
    return user


def _dump_user(u):
    data = _user_payload_admin(u)
    data["role_label"] = ROLE_LABELS.get(u.role, u.role)
    return data


@router.get("/users")
def list_users(status: str = Query(None), _=Depends(_require_admin_or_grade_leader),
               db: Session = Depends(get_db)):
    q = db.query(User)
    if status in ("pending", "approved", "rejected"):
        q = q.filter(User.status == status)
    if _.role == "grade_leader":
        q = q.filter(User.role == "teacher", User.grade == _.grade)
    users = q.order_by(User.created_at.desc(), User.id.desc()).all()
    return [_dump_user(u) for u in users]


def _check_user_review_permission(actor, user):
    if actor.role == "admin":
        return
    if actor.role == "grade_leader":
        if user.role != "teacher" or user.grade != actor.grade:
            raise HTTPException(403, "年级组长只能审核本年级教师")
        return
    raise HTTPException(403, "需要管理员或年级组长权限")


def _revoke_user_sessions(db: Session, user_id: int):
    db.query(AuthSession).filter(AuthSession.user_id == user_id).delete()
    db.commit()


@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, _=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    _check_user_review_permission(_, user)
    user.status = "approved"
    db.commit()
    return {"message": "已通过审核", "user": _dump_user(user)}


@router.post("/users/{user_id}/reject")
def reject_user(user_id: int, _=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    _check_user_review_permission(_, user)
    user.status = "rejected"
    _revoke_user_sessions(db, user.id)
    return {"message": "已驳回", "user": _dump_user(user)}


@router.post("/users/{user_id}/class")
def set_user_class(user_id: int, class_name: str = Body(..., embed=True),
                   _=Depends(_require_admin), db: Session = Depends(get_db)):
    from backend.routes.teacher_api import _validate_class_name
    _validate_class_name(class_name)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role not in ("teacher", "grade_leader"):
        raise HTTPException(400, "仅支持给教师/年级组长设置班级")
    user.class_name = class_name
    user.grade = class_name[0] + class_name[1]
    db.commit()
    return {"message": "已设置班级", "user": _dump_user(user)}


@router.post("/users")
def create_user(username: str = Body(...), password: str = Body(...), role: str = Body(...),
                name: str = Body(None), class_name: str = Body(None), grade: str = Body(None),
                student_id: int = Body(None), _=Depends(_require_admin), db: Session = Depends(get_db)):
    from backend.routes.auth import ROLES
    username = str(username).strip()
    _validate_credentials(username, password)
    role = (role or "").strip().lower()
    if role not in ("teacher", "grade_leader"):
        raise HTTPException(400, "管理员仅可创建 teacher / grade_leader 账号")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "该用户名已被注册")
    if role == "grade_leader":
        if grade not in GRADE_NAMES:
            raise HTTPException(400, "年级组长需填写合法年级（初一/初二/初三）")
        class_name = None
    else:
        if class_name:
            from backend.routes.teacher_api import _validate_class_name
            _validate_class_name(class_name)
            grade = class_name[0] + class_name[1]
        else:
            grade = None
    user = User(
        username=username,
        password_hash=_hash_password(str(password)),
        role=role,
        name=name or username,
        student_id=None,
        class_name=class_name,
        grade=grade,
        status="approved",
        created_at=datetime.now(),
    )
    db.add(user)
    db.commit()
    return {"message": "账号创建成功", "user": _dump_user(user)}


def _get_indices(db, grade=None):
    key = f"indices:{grade or '*'}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    with _indices_lock:
        cached = cache.get(key)
        if cached is not None:
            return cached
        gen_before = cache.generation("indices")
        students = db.query(Student).all() if not grade else \
            db.query(Student).filter(Student.grade == grade).all()
        ids = [s.id for s in students]
        if not ids:
            cache.put(key, {})
            return {}
        profiles = batch_growth_profiles(ids, db, light=True)
        by_id = {s.id: s for s in students}
        result = {
            sid: {
                "growth_index": p["growth_index"],
                "grade": by_id[sid].grade,
                "class_name": by_id[sid].class_name,
            }
            for sid, p in profiles.items()
        }
        # 计算期间若有写操作已 invalidate，则丢弃本次陈旧结果，避免覆盖新数据
        if cache.generation("indices") == gen_before:
            cache.put(key, result)
        return result


def _warm_cache():
    try:
        from backend.models import SessionLocal
        db = SessionLocal()
        _get_indices(db)
        db.close()
        print(f"[admin] Cache warmed: {len(cache.get('indices:*') or {})} indices")
    except Exception as e:
        print(f"[admin] Cache warm failed: {e}")


def start_cache_warmup():
    threading.Thread(target=_warm_cache, daemon=True).start()


@router.get("/school/overview")
def get_school_overview(_=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    profiles = _get_indices(db, grade=(_.grade if _.role == "grade_leader" else None))

    grade_totals = defaultdict(float)
    grade_counts = defaultdict(int)
    total_idx = 0
    for p in profiles.values():
        if _.role == "grade_leader" and p["grade"] != _.grade:
            continue
        total_idx += p["growth_index"]
        grade_totals[p["grade"]] += p["growth_index"]
        grade_counts[p["grade"]] += 1

    grades = {}
    for g in grade_totals:
        grades[g] = {
            "avg_growth_index": round(grade_totals[g] / grade_counts[g], 1),
            "student_count": grade_counts[g],
        }

    count = sum(grade_counts.values())
    return {
        "total_students": count,
        "avg_growth_index": round(total_idx / count, 1) if count else 0,
        "grades": grades,
    }


@router.get("/subject_mastery")
def get_subject_mastery(_=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    """各年级 × 学科平均分（实时聚合，与教师端统一用「平均分」口径）。
    音体美信不在 scores 表，自然剔除。"""
    raw = db.query(
        Student.grade, Student.class_name, Score.subject,
        func.avg(Score.score), func.max(Score.max_score), func.count(Score.id),
    ).join(
        Student, Student.id == Score.student_id
    ).filter(
        Score.score != None, Score.max_score != None, Score.max_score > 0,
    ).group_by(Student.grade, Student.class_name, Score.subject).all()
    rows = [
        SubjectStats(grade=g, class_name=c, subject=s,
                     avg_score=round(avg, 1), max_score=max_s, count=n)
        for g, c, s, avg, max_s, n in raw
    ]

    acc = {}
    for r in rows:
        if _.role == "grade_leader" and r.grade != _.grade:
            continue
        key = (r.grade, r.subject)
        e = acc.setdefault(key, {"sum": 0.0, "count": 0, "max_score": r.max_score})
        e["sum"] += r.avg_score * r.count
        e["count"] += r.count

    subjects = sorted({k[1] for k in acc})
    grades = sorted({k[0] for k in acc}, key=lambda g: SEMESTER_ORDER.get(g + "上", 0))
    out = [
        {
            "grade": g, "subject": s,
            "avg_score": round(acc[(g, s)]["sum"] / acc[(g, s)]["count"], 1),
            "max_score": acc[(g, s)]["max_score"],
            "avg_rate": round(acc[(g, s)]["sum"] / acc[(g, s)]["count"] / acc[(g, s)]["max_score"] * 100, 1),
            "count": acc[(g, s)]["count"],
        }
        for g in grades for s in subjects if (g, s) in acc
    ]
    return {"grades": grades, "subjects": subjects, "rows": out}


@router.get("/grade_comparison")
def get_grade_comparison(_=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    profiles = _get_indices(db, grade=(_.grade if _.role == "grade_leader" else None))

    classes_map = {}
    for sid, p in profiles.items():
        if _.role == "grade_leader" and p["grade"] != _.grade:
            continue
        cls = p["class_name"]
        if cls not in classes_map:
            classes_map[cls] = {"total": 0, "count": 0, "grade": p["grade"]}
        classes_map[cls]["total"] += p["growth_index"]
        classes_map[cls]["count"] += 1

    return sorted(
        ({"class_name": cls, "grade": st["grade"],
          "avg_growth_index": round(st["total"] / st["count"], 1),
          "student_count": st["count"]}
         for cls, st in classes_map.items()),
        key=lambda x: x["class_name"],
    )


def _subject_avg_list(ids, subject, db, grade=None):
    """按学生维度取某科全部考试平均分（绝对分值），返回可分布数值列表。"""
    q = db.query(Score.student_id, Score.score).filter(
        Score.student_id.in_(ids), Score.subject == subject,
        Score.score != None,
    )
    if grade:
        q = q.join(Student, Student.id == Score.student_id).filter(Student.grade == grade)
    acc = defaultdict(list)
    for sid, sc in q.all():
        acc[sid].append(sc)
    return [sum(v) / len(v) for v in acc.values()]


@router.get("/distribution")
def get_distribution(metric: str = Query("growth"), subject: str = Query(None),
                     grade: str = Query(None), _=Depends(_require_admin_or_grade_leader),
                     db: Session = Depends(get_db)):
    if metric not in ("growth", "score"):
        raise HTTPException(400, "metric must be 'growth' or 'score'")

    if _.role == "grade_leader":
        grade = _.grade

    if metric == "growth":
        profiles = _get_indices(db, grade=grade)
        values = [p["growth_index"] for p in profiles.values() if not grade or p["grade"] == grade]
        labels, counts = _bucket(values)
    else:
        if not subject:
            raise HTTPException(400, "subject is required when metric=score")
        q = db.query(Student.id)
        if grade:
            q = q.filter(Student.grade == grade)
        ids = [s.id for s in q.all()]
        values = _subject_avg_list(ids, subject, db) if ids else []
        max_s = SUBJECT_MAX_SCORES.get(subject, 100)
        width = max(1, math.ceil((max_s + 1) / 7))
        labels, counts = _bucket(values, 0, max_s + 1, width, trim=False)

    return {
        "metric": metric,
        "subject": subject,
        "grade": grade,
        "buckets": labels,
        "counts": counts,
        "total": len(values),
    }


@router.get("/distribution/students")
def get_distribution_students(metric: str = Query("growth"), subject: str = Query(None),
                              grade: str = Query(None), bucket: str = Query(...),
                              _=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    """全校/年级分布下钻：返回落入指定桶标签的学生明细。"""
    if metric not in ("growth", "score"):
        raise HTTPException(400, "metric must be 'growth' or 'score'")
    if _.role == "grade_leader":
        grade = _.grade

    if metric == "growth":
        profiles = _get_indices(db, grade=grade)
        ids = [sid for sid, p in profiles.items() if not grade or p["grade"] == grade]
        values = {sid: profiles[sid]["growth_index"] for sid in ids}
        lo, hi, width = 0, 100, 5
    else:
        if not subject:
            raise HTTPException(400, "subject is required when metric=score")
        q = db.query(Student)
        if grade:
            q = q.filter(Student.grade == grade)
        students = q.all()
        ids = [s.id for s in students]
        values = _subject_avg_map(ids, subject, db, grade)
        max_s = SUBJECT_MAX_SCORES.get(subject, 100)
        lo, hi, width = 0, max_s + 1, max(1, math.ceil((max_s + 1) / 7))

    studs = db.query(Student).filter(Student.id.in_(ids)).all() if ids else []
    by_id = {s.id: s for s in studs}
    result = [{
        "student_id": sid,
        "name": by_id[sid].name,
        "class_name": by_id[sid].class_name,
        "value": round(v, 1),
        "bucket": _student_bucket_label(v, lo, hi, width),
    } for sid, v in values.items() if by_id.get(sid) and _student_bucket_label(v, lo, hi, width) == bucket]
    return {"metric": metric, "subject": subject, "grade": grade, "bucket": bucket, "students": result}


def _subject_avg_map(ids, subject, db, grade=None):
    """按学生维度取某科平均分，返回 {student_id: avg}。"""
    q = db.query(Score.student_id, Score.score).filter(
        Score.student_id.in_(ids), Score.subject == subject,
        Score.score != None,
    )
    if grade:
        q = q.join(Student, Student.id == Score.student_id).filter(Student.grade == grade)
    acc = defaultdict(list)
    for sid, sc in q.all():
        acc[sid].append(sc)
    return {sid: sum(v) / len(v) for sid, v in acc.items()}


# ===================== 考试规划（管理员下达 → 年级组长进行 → 教师批阅自动录入） =====================

def _exam_plan_payload(p: ExamPlan) -> dict:
    return {
        "id": p.id,
        "exam_type": p.exam_type,
        "subject": p.subject,
        "grade": p.grade,
        "exam_date": str(p.exam_date),
        "semester": p.semester,
        "status": p.status,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "conducted_at": p.conducted_at.isoformat() if p.conducted_at else None,
        "graded_at": p.graded_at.isoformat() if p.graded_at else None,
    }


@router.get("/exam_plans")
def list_exam_plans(status: str = Query(None), grade: str = Query(None),
                    _=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    """考试规划列表（管理员看全校；年级组长仅本年级）。"""
    q = db.query(ExamPlan)
    if _.role == "grade_leader":
        grade = _.grade
    if grade:
        q = q.filter(ExamPlan.grade == grade)
    if status:
        q = q.filter(ExamPlan.status == status)
    plans = q.order_by(ExamPlan.exam_date.desc(), ExamPlan.id.desc()).all()
    return [_exam_plan_payload(p) for p in plans]


@router.get("/exam_plans/meta")
def get_exam_plan_meta(_=Depends(_require_admin_or_grade_leader)):
    """考试规划元数据：各年级各学期日期区间与开考科目，供前端日期/科目联动。"""
    ranges = semester_ranges()
    order = sorted(SEMESTER_ORDER, key=lambda x: SEMESTER_ORDER[x])
    grades = []
    for g in GRADE_NAMES:
        semesters = [s for s in order if s.startswith(g)]
        grades.append({
            "grade": g,
            "semesters": [{
                "semester": sem,
                "start": ranges[sem]["start"],
                "end": ranges[sem]["end"],
                "subjects": semester_subjects(sem),
                "max_scores": {s: MAX_SCORES.get(s, 100) for s in semester_subjects(sem)},
            } for sem in semesters],
        })
    return {"grades": grades}


@router.post("/exam_plans")
def create_exam_plan(exam_type: str = Query(...), subject: str = Query(...), grade: str = Query(...),
                     exam_date: str = Query(...), _=Depends(_require_admin), db: Session = Depends(get_db)):
    """管理员下达考试规划（状态 planned）。"""
    if exam_type not in EXAM_TYPES:
        raise HTTPException(400, f"Unknown exam_type: {exam_type}")
    if subject not in MAX_SCORES:
        raise HTTPException(400, f"Unknown subject: {subject}")
    if grade not in GRADE_NAMES:
        raise HTTPException(400, "grade must be one of 初一/初二/初三")
    try:
        parsed = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")
    semester = semester_from_date(grade, parsed)
    if not semester:
        raise HTTPException(400, "该日期不在学业日历内，请选择合法考试日期")
    if subject not in SUBJECTS_BY_SEMESTER.get(semester, []):
        raise HTTPException(400, f"{semester} 不开设 {subject} 科目")
    dup = db.query(ExamPlan).filter(
        ExamPlan.grade == grade, ExamPlan.subject == subject,
        ExamPlan.exam_type == exam_type, ExamPlan.exam_date == parsed,
    ).first()
    if dup:
        raise HTTPException(400, "同日同类型同科目考试规划已存在")
    plan = ExamPlan(
        exam_type=exam_type, subject=subject, grade=grade,
        exam_date=parsed, semester=semester, status="planned",
        created_by=_.id, created_at=datetime.now(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _exam_plan_payload(plan)


@router.delete("/exam_plans/{plan_id}")
def delete_exam_plan(plan_id: int = Path(...),
                     _=Depends(_require_admin), db: Session = Depends(get_db)):
    """删除考试规划（仅管理员，且仅未进行的规划可删除）。"""
    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    if plan.status != "planned":
        raise HTTPException(400, "已进行/已批阅的考试不能删除")
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.post("/exam_plans/{plan_id}/conduct")
def conduct_exam(plan_id: int = Path(...),
                 _=Depends(_require_admin_or_grade_leader), db: Session = Depends(get_db)):
    """年级组长进行考试：planned → conducted（仅考试日期当天或之后）。"""
    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    if _.role == "grade_leader" and plan.grade != _.grade:
        raise HTTPException(403, "仅能进行本年级的考试")
    if plan.status != "planned":
        raise HTTPException(400, "该考试已进行或已批阅，无法重复进行")
    if plan.exam_date > datetime.now().date():
        raise HTTPException(400, "考试日期尚未到达，暂不能进行")
    plan.status = "conducted"
    plan.conducted_at = datetime.now()
    plan.conducted_by = _.id
    db.commit()
    db.refresh(plan)
    return _exam_plan_payload(plan)
