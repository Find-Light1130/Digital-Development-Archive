from fastapi import APIRouter, Depends, Query, Path, HTTPException, Body
from sqlalchemy.orm import Session
from collections import defaultdict, Counter
from datetime import datetime
import math
import re
from backend.models import get_db, Student, Activity, Score, QualityScore, Award, ExamPlan, Attendance
from backend.ai_modules.analysis import batch_growth_profiles, compute_growth_profile
from backend.constants import (
    SEMESTER_ORDER, grade_for, semester_from_date,
    MAX_SCORES, SUBJECTS_BY_SEMESTER, EXAM_TYPES, AWARD_LEVELS,
    QUALITY_SUBJECTS, QUALITY_DIMENSIONS, _GRADE_FIRST_SEMESTER,
)
from backend.routes.auth import get_current_user, can_access_class, can_access_student
import backend.cache as cache

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _require_scope(user, db: Session, class_name: str = None, student_id: int = None):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权访问教师端接口")
    if class_name is not None and not can_access_class(db, user, class_name):
        raise HTTPException(403, "无权访问该班级")
    if student_id is not None and can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权访问该学生数据")

SUBJECT_MAX_SCORES = MAX_SCORES

_CLASS_NAME_RE = re.compile(r'^[初高][一二三]\d+班$')

ALLOWED_ACTIVITY_TYPES = {"体育", "实践", "社团", "阅读"}


def _validate_class_name(name: str):
    if not _CLASS_NAME_RE.match(name):
        raise HTTPException(400, f"Invalid class_name format: {name}")


def _bucket(values, lo=0, hi=100, width=5, trim=True):
    """将数值分布到 [lo, hi) 等宽分桶，返回 (labels, counts)；trim=True 时剔除首尾空桶。"""
    counts = defaultdict(int)
    for v in values:
        v = max(lo, min(hi - 0.01, float(v)))
        counts[int((v - lo) // width)] += 1
    if not counts:
        return [], []
    if trim:
        first, last = min(counts), max(counts)
    else:
        first, last = 0, max(int(math.ceil((hi - lo) / width)) - 1, 0)
    labels = [f"{lo + i * width}~{min(lo + (i + 1) * width - 1, hi - 1)}" for i in range(first, last + 1)]
    out = [counts.get(i, 0) for i in range(first, last + 1)]
    return labels, out


def _subject_score_distribution(ids, subject, db, grade=None):
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


def _student_bucket_label(value, lo=0, hi=100, width=5):
    """单个数值的桶标签，与 _bucket 的 labels 格式保持一致。"""
    v = max(lo, min(hi - 0.01, float(value)))
    i = int((v - lo) // width)
    return f"{lo + i * width}~{min(lo + (i + 1) * width - 1, hi - 1)}"


def _parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid date, expected YYYY-MM-DD")


def _validate_score_write(user, db, student_id, subject, exam_type, date_str, score):
    """校验成绩写入参数，返回 (student, semester, parsed_date, max_s)。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权录入成绩")
    if not isinstance(student_id, int) or student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if subject not in MAX_SCORES:
        raise HTTPException(400, f"Unknown subject: {subject}")
    if exam_type not in EXAM_TYPES:
        raise HTTPException(400, "exam_type must be one of 月考/期中/期末")
    try:
        score = float(score)
    except (TypeError, ValueError):
        raise HTTPException(400, "score must be a number")
    if not math.isfinite(score) or score < 0:
        raise HTTPException(400, "score must be a non-negative finite number")
    parsed = _parse_date(date_str)
    if parsed > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    semester = semester_from_date(student.grade, parsed)
    if not semester:
        raise HTTPException(400, "Date is out of the student's academic calendar")
    max_s = MAX_SCORES[subject]
    if score > max_s:
        raise HTTPException(400, f"score must be <= {max_s} for {subject}")
    if subject not in SUBJECTS_BY_SEMESTER.get(semester, []):
        raise HTTPException(400, f"{subject} 不是该生{student.grade}{semester}的科目")
    return student, semester, parsed, max_s


@router.get("/class/distribution")
def get_class_distribution(class_name: str = Query(...), metric: str = Query("growth"),
                           subject: str = Query(None), user=Depends(get_current_user),
                           db: Session = Depends(get_db)):
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    if metric not in ("growth", "score"):
        raise HTTPException(400, "metric must be 'growth' or 'score'")
    students = db.query(Student).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]

    if metric == "growth":
        profiles = batch_growth_profiles(ids, db, light=True)
        values = [p["growth_index"] for sid in ids if (p := profiles.get(sid))]
    else:
        if not subject:
            raise HTTPException(400, "subject is required when metric=score")
        values = _subject_score_distribution(ids, subject, db)

    if metric == "growth":
        labels, counts = _bucket(values)
    else:
        max_s = SUBJECT_MAX_SCORES.get(subject, 100)
        width = max(1, math.ceil((max_s + 1) / 7))
        labels, counts = _bucket(values, 0, max_s + 1, width, trim=False)
    return {
        "class_name": class_name,
        "metric": metric,
        "subject": subject,
        "buckets": labels,
        "counts": counts,
        "total": len(values),
    }


@router.get("/class/semesters")
def get_class_semesters(class_name: str = Query(...), user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student.id).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]
    rows = db.query(Score.semester).filter(
        Score.student_id.in_(ids), Score.semester != None,
    ).distinct().all()
    return sorted([r[0] for r in rows], key=lambda x: SEMESTER_ORDER.get(x, 0))


def _exam_label(exam_type: str, date_str: str) -> str:
    if exam_type == "期中":
        return "期中综评"
    if exam_type == "期末":
        return "期末综评"
    return date_str[5:7] + "月小测验"


def _unique_labels(exam_infos: dict) -> dict:
    """按考试唯一化标签：同一标签（如 期中/期末/X月月考）出现多次时追加 ·M-D。"""
    counts = Counter(info["label"] for info in exam_infos.values())
    result = {}
    for key, info in exam_infos.items():
        if counts[info["label"]] == 1:
            result[key] = info["label"]
        else:
            result[key] = f"{info['label']}·{info['date'][5:7]}-{info['date'][8:10]}"
    return result


def _build_trends(scores_q, semester=None):
    subj_pcts = defaultdict(lambda: defaultdict(list))
    subj_actual = defaultdict(lambda: defaultdict(list))
    subj_max = {}
    exam_infos = {}
    for sc in scores_q:
        if semester and sc.semester != semester:
            continue
        if sc.score is None:
            continue
        pct = sc.score / sc.max_score * 100 if sc.max_score else 50
        date = str(sc.date)
        exam_type = sc.exam_type or "月考"
        key = date + "|" + exam_type
        subj_pcts[sc.subject][key].append(pct)
        subj_actual[sc.subject][key].append(sc.score)
        if sc.subject not in subj_max:
            subj_max[sc.subject] = sc.max_score or SUBJECT_MAX_SCORES.get(sc.subject, 100)
        if key not in exam_infos:
            exam_infos[key] = {
                "label": f"{sc.semester or '未标注'}·{_exam_label(exam_type, date)}",
                "date": date,
            }

    label_map = _unique_labels(exam_infos)

    subj_mastery = {}
    for subj in subj_pcts:
        all_pcts = []
        for vals in subj_pcts[subj].values():
            all_pcts.extend(vals)
        subj_mastery[subj] = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0

    subject_trends = {}
    for subj in subj_pcts:
        sorted_items = sorted(subj_pcts[subj].items(), key=lambda x: x[0])
        subject_trends[subj] = []
        for key, pcts in sorted_items:
            actual_vals = subj_actual[subj].get(key, [])
            avg_score = round(sum(actual_vals) / len(actual_vals), 1) if actual_vals else 0
            group_max = max(actual_vals) if actual_vals else 0
            group_min = min(actual_vals) if actual_vals else 0
            subject_trends[subj].append({
                "label": label_map.get(key, key.split("|", 1)[1]),
                "date": key.split("|", 1)[0],
                "avg": round(sum(pcts) / len(pcts), 1),
                "avg_score": avg_score,
                "max_score": int(subj_max.get(subj, 100)),
                "max": group_max,
                "min": group_min,
            })

    return subject_trends, subj_mastery


@router.get("/class/overview")
def get_class_overview(class_name: str = Query(...), semester: str = Query(None),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")

    ids = [s.id for s in students]
    profiles = batch_growth_profiles(ids, db)

    total_index = 0
    needs_attention = []
    avg_aspects_sum = {}
    profiled_count = 0

    for s in students:
        p = profiles.get(s.id)
        if not p:
            continue
        profiled_count += 1
        total_index += p["growth_index"]
        if p["warnings"]:
            needs_attention.append({
                "student_id": s.id,
                "name": s.name,
                "reason": p["warnings"][0],
            })
        for k, v in p["aspects"].items():
            avg_aspects_sum[k] = avg_aspects_sum.get(k, 0) + v

    avg_index = round(total_index / profiled_count, 1) if profiled_count else 0
    avg_aspects = {k: round(v / profiled_count, 1) for k, v in avg_aspects_sum.items()} if profiled_count else {}

    scores_q = db.query(Score).filter(Score.student_id.in_(ids)).all()
    subject_trends, subject_mastery = _build_trends(scores_q, semester)

    return {
        "class_name": class_name,
        "student_count": len(students),
        "avg_growth_index": avg_index,
        "avg_aspects": avg_aspects,
        "subject_trends": subject_trends,
        "subject_mastery": subject_mastery,
        "needs_attention": needs_attention[:10],
    }


@router.get("/class/quality")
def get_class_quality(class_name: str = Query(...), semester: str = Query(None),
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student.id).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]
    q = db.query(QualityScore).filter(QualityScore.student_id.in_(ids))
    if semester:
        q = q.filter(QualityScore.semester == semester)
    rows = q.all()

    semesters = sorted({r.semester for r in rows}, key=lambda x: SEMESTER_ORDER.get(x, 0))
    subjects = {}
    for r in rows:
        entry = subjects.setdefault(r.subject, {}).setdefault(r.semester, {})
        dim_entry = entry.setdefault(r.dimension, {"scores": [], "grades": defaultdict(int)})
        dim_entry["scores"].append(r.score)
        dim_entry["grades"][r.grade] += 1

    result = []
    for subj in sorted(subjects):
        sem_list = []
        for sem in semesters:
            if sem not in subjects[subj]:
                continue
            dims = []
            for dim in sorted(subjects[subj][sem]):
                d = subjects[subj][sem][dim]
                avg = round(sum(d["scores"]) / len(d["scores"]), 1)
                dims.append({
                    "dimension": dim,
                    "score": avg,
                    "grade": grade_for(avg),
                    "distribution": dict(sorted(d["grades"].items())),
                })
            sem_list.append({"semester": sem, "dimensions": dims})
        result.append({"subject": subj, "semesters": sem_list})
    return {"class_name": class_name, "semesters": semesters, "subjects": result}


@router.get("/student/{student_id}/details")
def get_student_details(student_id: int = Path(..., gt=0), user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    _require_scope(user, db, student_id=student_id)
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
        "trend": profile.get("trend", []),
    }


@router.post("/student_event")
def add_student_event(student_id: int, type: str, date: str, value: float = 1,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权提交活动记录")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    if student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if type not in ALLOWED_ACTIVITY_TYPES:
        raise HTTPException(400, f"Invalid type, must be one of {ALLOWED_ACTIVITY_TYPES}")
    if not math.isfinite(value) or value <= 0 or value > 24:
        raise HTTPException(400, "value must be a finite number between 0 and 24")
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid date, expected YYYY-MM-DD")
    if parsed_date > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    semester = semester_from_date(student.grade, parsed_date)
    if not semester:
        raise HTTPException(400, "Date is out of the student's academic calendar")
    existing = db.query(Activity).filter(
        Activity.student_id == student_id,
        Activity.type == type,
        Activity.date == parsed_date,
    ).first()
    if existing:
        existing.hours = value
        existing.semester = semester
        db.add(existing)
        db.commit()
        cache.invalidate("indices")
        return {"status": "ok", "id": existing.id, "updated": True}
    daily = db.query(Activity).filter(
        Activity.student_id == student_id, Activity.date == parsed_date,
    ).count()
    if daily >= 20:
        raise HTTPException(429, "当日活动记录已达上限，请勿频繁提交")
    act = Activity(student_id=student_id, type=type, hours=value, date=parsed_date, semester=semester)
    db.add(act)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "id": act.id, "updated": False}


@router.get("/class/students")
def get_class_students(class_name: str = Query(...), user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """班级花名册：返回学生列表与当前学期科目/满分（供批量录入网格使用）。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]
    rows = db.query(Score.semester).filter(
        Score.student_id.in_(ids), Score.semester != None,
    ).distinct().all()
    current = sorted([r[0] for r in rows], key=lambda x: SEMESTER_ORDER.get(x, 0))
    current = current[-1] if current else None
    return {
        "class_name": class_name,
        "grade": students[0].grade,
        "current_semester": current,
        "subjects": [{"subject": s, "max_score": MAX_SCORES.get(s, 100)}
                     for s in SUBJECTS_BY_SEMESTER.get(current, [])],
        "students": [{"student_id": s.id, "name": s.name} for s in students],
    }


@router.get("/exam_plans")
def get_teacher_exam_plans(class_name: str = Query(...), user=Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """阅卷端：本班年级已进行（待批阅/已批阅）的考试规划，附本班学生名单与已有分数。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        raise HTTPException(404, "Class not found")
    grade = students[0].grade
    ids = [s.id for s in students]
    plans = (
        db.query(ExamPlan)
        .filter(ExamPlan.grade == grade, ExamPlan.status.in_(["conducted", "graded"]))
        .order_by(ExamPlan.exam_date.desc(), ExamPlan.id.desc())
        .all()
    )
    result = []
    for p in plans:
        rows = db.query(Score).filter(
            Score.student_id.in_(ids), Score.subject == p.subject,
            Score.exam_type == p.exam_type, Score.date == p.exam_date,
        ).all()
        score_map = {r.student_id: r.score for r in rows}
        roster = [{
            "student_id": s.id,
            "name": s.name,
            "score": score_map.get(s.id),
        } for s in students]
        result.append({
            "id": p.id,
            "exam_type": p.exam_type,
            "subject": p.subject,
            "grade": p.grade,
            "exam_date": str(p.exam_date),
            "semester": p.semester,
            "status": p.status,
            "max_score": MAX_SCORES.get(p.subject, 100),
            "graded": bool(rows),
            "students": roster,
        })
    return result


@router.post("/exam_plans/{plan_id}/grade")
def grade_exam_plan(plan_id: int = Path(...), payload: dict = Body(...),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    """批阅答题卡：按考试规划把本班学生成绩自动录入（同键幂等覆盖）。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权批阅成绩")
    class_name = payload.get("class_name")
    scores = payload.get("scores") or []
    if not class_name or not isinstance(scores, list) or not scores:
        raise HTTPException(400, "class_name and non-empty scores required")
    _validate_class_name(class_name)
    if not can_access_class(db, user, class_name):
        raise HTTPException(403, "无权操作该班级")

    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    if plan.status not in ("conducted", "graded"):
        raise HTTPException(400, "该考试尚未进行，不能批阅")
    if plan.subject not in MAX_SCORES:
        raise HTTPException(400, f"Unknown subject: {plan.subject}")

    students = db.query(Student).filter(Student.class_name == class_name).all()
    class_ids = {s.id for s in students}
    if not students or plan.grade != students[0].grade:
        raise HTTPException(400, "该班级不属于本场考试的年级")
    seen_sids = set()
    for i, it in enumerate(scores):
        if not isinstance(it, dict):
            raise HTTPException(400, f"scores[{i}] must be an object")
        sid = it.get("student_id")
        if not isinstance(sid, int):
            raise HTTPException(400, "student_id 必须为整数")
        if sid in seen_sids:
            raise HTTPException(400, f"scores[{i}]: 学生重复，批阅名单不得含重复学生")
        seen_sids.add(sid)
    if seen_sids != class_ids:
        raise HTTPException(400, "批阅名单必须恰好覆盖本班全体学生")

    max_s = MAX_SCORES[plan.subject]
    prepared = []
    for i, it in enumerate(scores):
        if not isinstance(it, dict):
            raise HTTPException(400, f"scores[{i}] must be an object")
        sid = it.get("student_id")
        score = it.get("score")
        if sid not in class_ids:
            raise HTTPException(400, f"scores[{i}]: 学生不在本班")
        try:
            score = float(score)
        except (TypeError, ValueError):
            raise HTTPException(400, f"scores[{i}]: score must be a number")
        if not math.isfinite(score) or not (0 <= score <= max_s):
            raise HTTPException(400, f"scores[{i}]: score out of range [0, {max_s}]")
        prepared.append((sid, score))

    existing = {
        r.student_id: r
        for r in db.query(Score).filter(
            Score.student_id.in_(class_ids), Score.subject == plan.subject,
            Score.exam_type == plan.exam_type, Score.date == plan.exam_date,
        ).all()
    }
    for sid, score in prepared:
        rec = existing.get(sid)
        if rec:
            rec.score = score
            rec.max_score = max_s
            db.add(rec)
        else:
            db.add(Score(
                student_id=sid, subject=plan.subject, score=score, max_score=max_s,
                exam_type=plan.exam_type, date=plan.exam_date, semester=plan.semester,
            ))
    plan.status = "graded"
    plan.graded_at = datetime.now()
    plan.graded_by = user.id
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "count": len(prepared)}


@router.get("/exam_plans/{plan_id}/stats")
def get_exam_plan_stats(plan_id: int = Path(...), class_name: str = Query(...),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    """考试分析：某场考试本班成绩统计（均分/最高/最低/及格率/分数段分布/排名）。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        raise HTTPException(404, "Class not found")
    if students[0].grade != plan.grade:
        raise HTTPException(400, "该班级不属于本场考试的年级")
    ids = [s.id for s in students]
    rows = db.query(Score).filter(
        Score.student_id.in_(ids), Score.subject == plan.subject,
        Score.exam_type == plan.exam_type, Score.date == plan.exam_date,
    ).all()
    scored = [(r.student_id, r.score) for r in rows]
    if not scored:
        raise HTTPException(404, "该考试本班暂无成绩，请先批阅")
    max_s = MAX_SCORES.get(plan.subject, 100)
    n = len(scored)
    avg = sum(r for _, r in scored) / n
    passed = sum(1 for _, r in scored if r >= max_s * 0.6)
    buckets = {"优秀": 0, "良好": 0, "及格": 0, "待提高": 0}
    for _, r in scored:
        ratio = r / max_s
        if ratio >= 0.85:
            buckets["优秀"] += 1
        elif ratio >= 0.7:
            buckets["良好"] += 1
        elif ratio >= 0.6:
            buckets["及格"] += 1
        else:
            buckets["待提高"] += 1
    ranked = sorted(scored, key=lambda kv: (-kv[1], kv[0]))
    by_id = {s.id: s for s in students}
    ranking = [{
        "rank": i + 1,
        "student_id": sid,
        "name": by_id[sid].name,
        "score": sc,
    } for i, (sid, sc) in enumerate(ranked)]
    return {
        "plan_id": plan.id,
        "subject": plan.subject,
        "exam_type": plan.exam_type,
        "exam_date": str(plan.exam_date),
        "semester": plan.semester,
        "max_score": max_s,
        "count": n,
        "avg": round(avg, 1),
        "highest": ranked[0][1],
        "lowest": ranked[-1][1],
        "pass_rate": round(passed / n * 100, 1),
        "buckets": buckets,
        "ranking": ranking,
    }


@router.post("/scores")
def add_score(student_id: int, subject: str, exam_type: str, date: str, score: float,
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    """单条成绩录入。同学生/科目/考试类型/日期 幂等覆盖。"""
    student, semester, parsed, max_s = _validate_score_write(
        user, db, student_id, subject, exam_type, date, score)
    existing = db.query(Score).filter(
        Score.student_id == student_id, Score.subject == subject,
        Score.exam_type == exam_type, Score.date == parsed,
    ).first()
    if existing:
        existing.score = score
        existing.max_score = max_s
        existing.semester = semester
        db.add(existing)
        db.commit()
        cache.invalidate("indices")
        return {"status": "ok", "id": existing.id, "updated": True}
    rec = Score(student_id=student_id, subject=subject, score=score, max_score=max_s,
                exam_type=exam_type, date=parsed, semester=semester)
    db.add(rec)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "id": rec.id, "updated": False}


@router.post("/scores/batch")
def add_scores_batch(payload: dict = Body(...), user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """整班批量成绩录入：任一非法整批拒绝（提交前全部校验，不落库）。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权录入成绩")
    exam_type = payload.get("exam_type")
    date_str = payload.get("date")
    items = payload.get("scores") or []
    if exam_type not in EXAM_TYPES:
        raise HTTPException(400, "exam_type must be one of 月考/期中/期末")
    if not isinstance(items, list) or not items:
        raise HTTPException(400, "scores must be a non-empty list")
    parsed = _parse_date(date_str)
    if parsed > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")

    prepared = []
    seen = set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise HTTPException(400, f"scores[{i}] must be an object")
        student_id = it.get("student_id")
        subject = it.get("subject")
        score = it.get("score")
        key = (student_id, subject, exam_type, str(parsed))
        if key in seen:
            continue
        seen.add(key)
        student, semester, _p, max_s = _validate_score_write(
            user, db, student_id, subject, exam_type, date_str, score)
        prepared.append((student_id, subject, exam_type, parsed, semester, max_s, float(score)))

    if not prepared:
        raise HTTPException(400, "scores list is empty after de-duplication")

    existing = {
        (r.student_id, r.subject): r
        for r in db.query(Score).filter(
            Score.student_id.in_({p[0] for p in prepared}),
            Score.subject.in_({p[1] for p in prepared}),
            Score.exam_type == exam_type, Score.date == parsed,
        ).all()
    }
    for sid, subject, etype, datev, sem, max_s, score in prepared:
        rec = existing.get((sid, subject))
        if rec:
            rec.score = score
            rec.max_score = max_s
            rec.semester = sem
            db.add(rec)
        else:
            db.add(Score(student_id=sid, subject=subject, score=score, max_score=max_s,
                         exam_type=etype, date=datev, semester=sem))
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "count": len(prepared)}


@router.post("/scores/delete")
def delete_score(student_id: int, subject: str, exam_type: str, date: str,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    """删除指定成绩记录（更正误录）。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权删除成绩")
    if student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if exam_type not in EXAM_TYPES:
        raise HTTPException(400, "exam_type must be one of 月考/期中/期末")
    parsed = _parse_date(date)
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    rec = db.query(Score).filter(
        Score.student_id == student_id, Score.subject == subject,
        Score.exam_type == exam_type, Score.date == parsed,
    ).first()
    if not rec:
        raise HTTPException(404, "Score not found")
    db.delete(rec)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "message": "成绩已删除"}


@router.get("/class/awards")
def get_class_awards(class_name: str = Query(...), user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """本班获奖记录（按日期倒序），供获奖列表展示与导出。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]
    by_id = {s.id: s for s in students}
    rows = db.query(Award).filter(Award.student_id.in_(ids)).order_by(Award.date.desc(), Award.id.desc()).all()
    return [{
        "id": a.id,
        "student_id": a.student_id,
        "name": by_id[a.student_id].name,
        "title": a.title,
        "level": a.level,
        "date": str(a.date),
    } for a in rows]


@router.post("/award")
def add_award(student_id: int, title: str, level: str, date: str,
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    """获奖登记。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权登记获奖")
    if student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    title = (title or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    if level not in AWARD_LEVELS:
        raise HTTPException(400, "level must be one of 校级/区级/市级/省级")
    parsed = _parse_date(date)
    if parsed > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    rec = Award(student_id=student_id, title=title, level=level, date=parsed)
    db.add(rec)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "id": rec.id}


@router.post("/award/delete")
def delete_award(award_id: int = Query(..., gt=0), user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """删除获奖记录。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权删除获奖记录")
    rec = db.query(Award).filter(Award.id == award_id).first()
    if not rec:
        raise HTTPException(404, "Award not found")
    if can_access_student(db, user, rec.student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    db.delete(rec)
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "message": "获奖记录已删除"}


@router.get("/class/distribution/students")
def get_class_distribution_students(class_name: str = Query(...), metric: str = Query("growth"),
                                    subject: str = Query(None), bucket: str = Query(...),
                                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    """分布下钻：返回落入指定桶标签的学生明细。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    if metric not in ("growth", "score"):
        raise HTTPException(400, "metric must be 'growth' or 'score'")
    students = db.query(Student).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")
    by_id = {s.id: s for s in students}
    ids = list(by_id)
    if metric == "growth":
        profiles = batch_growth_profiles(ids, db, light=True)
        values = {sid: p["growth_index"] for sid in ids if (p := profiles.get(sid))}
        lo, hi, width = 0, 100, 5
    else:
        if not subject:
            raise HTTPException(400, "subject is required when metric=score")
        values = _subject_avg_map(ids, subject, db)
        max_s = MAX_SCORES.get(subject, 100)
        lo, hi, width = 0, max_s + 1, max(1, math.ceil((max_s + 1) / 7))
    result = [{
        "student_id": sid,
        "name": by_id[sid].name,
        "value": round(v, 1),
        "bucket": _student_bucket_label(v, lo, hi, width),
    } for sid, v in values.items() if _student_bucket_label(v, lo, hi, width) == bucket]
    return {"class_name": class_name, "metric": metric, "subject": subject,
            "bucket": bucket, "students": result}


# ===================== 考勤（查询 / 批量录入） =====================

@router.get("/class/attendance")
def get_class_attendance(class_name: str = Query(...), semester: str = Query(None),
                         date: str = Query(None),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    """班级考勤汇总：每生总出勤率、缺勤次数与学期内最近缺勤日期。
    传 date 时额外返回该日每生 present 状态（供录入表单回显）。"""
    _validate_class_name(class_name)
    _require_scope(user, db, class_name=class_name)
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        raise HTTPException(404, "Class not found")
    ids = [s.id for s in students]
    rows = db.query(Attendance).filter(Attendance.student_id.in_(ids)).all()
    if semester:
        rows = [r for r in rows if semester_from_date(students[0].grade, r.date) == semester]
    by_sid = defaultdict(list)
    for r in rows:
        by_sid[r.student_id].append(r)

    date_map = {}
    if date:
        parsed = _parse_date(date)
        if parsed > datetime.now().date():
            raise HTTPException(400, "Date cannot be in the future")
        for rec in db.query(Attendance).filter(
                Attendance.student_id.in_(ids), Attendance.date == parsed).all():
            date_map[rec.student_id] = rec.present

    result = []
    for s in students:
        recs = by_sid.get(s.id, [])
        total = len(recs)
        present = sum(1 for r in recs if r.present)
        abs_dates = sorted(str(r.date) for r in recs if not r.present)
        item = {
            "student_id": s.id,
            "name": s.name,
            "total": total,
            "absent": total - present,
            "rate": round(present / total * 100, 1) if total else 0,
            "absences": abs_dates[-5:],
        }
        if date:
            item["present"] = date_map.get(s.id, True)
        result.append(item)
    return {
        "class_name": class_name,
        "semester": semester,
        "date": date,
        "students": result,
    }


@router.post("/attendance")
def submit_attendance(payload: dict = Body(...), user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """批量考勤录入：按 班级+日期 幂等 upsert 全部学生。present ∈ {true,false}。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权录入考勤")
    class_name = payload.get("class_name")
    date_str = payload.get("date")
    items = payload.get("students") or []
    _validate_class_name(class_name or "")
    _require_scope(user, db, class_name=class_name)
    if not isinstance(items, list) or not items:
        raise HTTPException(400, "students must be a non-empty list")
    parsed = _parse_date(date_str)
    if parsed > datetime.now().date():
        raise HTTPException(400, "Date cannot be in the future")

    students = db.query(Student).filter(Student.class_name == class_name).all()
    if not students:
        raise HTTPException(404, "Class not found")
    class_ids = {s.id for s in students}

    prepared = {}
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise HTTPException(400, f"students[{i}] must be an object")
        sid = it.get("student_id")
        present = it.get("present")
        if not isinstance(sid, int) or sid <= 0:
            raise HTTPException(400, f"students[{i}]: 学生ID不合法")
        if sid not in class_ids:
            raise HTTPException(400, f"students[{i}]: 学生不在本班")
        if not isinstance(present, bool):
            raise HTTPException(400, f"students[{i}]: present must be boolean")
        prepared[sid] = bool(present)

    existing = {
        r.student_id: r
        for r in db.query(Attendance).filter(
            Attendance.student_id.in_(class_ids), Attendance.date == parsed,
        ).all()
    }
    for sid, present in prepared.items():
        rec = existing.get(sid)
        if rec:
            rec.present = present
            db.add(rec)
        else:
            db.add(Attendance(student_id=sid, date=parsed, present=present))
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "class_name": class_name, "date": date_str, "count": len(prepared)}


# ===================== 素质评估录入 =====================

@router.post("/quality")
def submit_quality(payload: dict = Body(...), user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """素质评估录入：按 (student_id, subject, semester, dimension) upsert score，等级自动按阈值回写。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权录入素质评估")
    student_id = payload.get("student_id")
    subject = payload.get("subject")
    semester = payload.get("semester")
    scores = payload.get("scores") or []
    if not isinstance(student_id, int) or student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if subject not in QUALITY_SUBJECTS:
        raise HTTPException(400, f"Unknown quality subject: {subject}")
    if semester not in SEMESTER_ORDER:
        raise HTTPException(400, "Unknown semester")
    if not isinstance(scores, dict) or not scores:
        raise HTTPException(400, "scores must be a non-empty dict of {dimension: score}")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权操作该学生数据")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    first = _GRADE_FIRST_SEMESTER.get(student.grade)
    idx = SEMESTER_ORDER.get(semester, 0)
    if not first or idx < SEMESTER_ORDER[first] or idx > SEMESTER_ORDER[first] + 1:
        raise HTTPException(400, f"{semester} 不在该生{student.grade}的学业跨度内")
    allowed_dims = QUALITY_DIMENSIONS.get(subject, [])
    prepared = {}
    for dim, score in scores.items():
        if dim not in allowed_dims:
            raise HTTPException(400, f"Unknown dimension: {dim}")
        try:
            score = float(score)
        except (TypeError, ValueError):
            raise HTTPException(400, f"{dim}: score must be a number")
        if not math.isfinite(score) or not (0 <= score <= 100):
            raise HTTPException(400, f"{dim}: score out of range [0, 100]")
        prepared[dim] = round(score, 1)

    existing = {
        r.dimension: r
        for r in db.query(QualityScore).filter(
            QualityScore.student_id == student_id, QualityScore.subject == subject,
            QualityScore.semester == semester,
        ).all()
    }
    for dim, score in prepared.items():
        rec = existing.get(dim)
        if rec:
            rec.score = score
            rec.grade = grade_for(score)
            db.add(rec)
        else:
            db.add(QualityScore(student_id=student_id, subject=subject, semester=semester,
                                dimension=dim, score=score, grade=grade_for(score)))
    db.commit()
    cache.invalidate("indices")
    return {"status": "ok", "count": len(prepared)}
