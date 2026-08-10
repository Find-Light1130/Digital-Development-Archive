"""AI 能力路由：学情报告、成长叙事、特长发现、心理树洞、情绪风险、
预警干预闭环、学习路径、试卷分析、批阅辅助、教师问数。"""

import json
from datetime import datetime, date

from fastapi import APIRouter, Depends, Query, Path, HTTPException, Body
from sqlalchemy.orm import Session

from backend.models import get_db, Student, Score, ExamPlan, Intervention, CompanionChat, LearningPlan
from backend.routes.auth import get_current_user, can_access_student, can_access_class, user_scope
from backend.ai_modules import (
    learning_report, narrative, talent, emotion_companion, intervention,
    learning_path, paper_analysis, nl_query,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _require_staff(user):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role == "student":
        raise HTTPException(403, "学生账号无权使用该功能")


def _check_student(user, db, student_id):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if can_access_student(db, user, student_id) is False:
        raise HTTPException(403, "无权访问该学生数据")


def _check_class(user, db, class_name):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if not can_access_class(db, user, class_name):
        raise HTTPException(403, "无权访问该班级")


def _dump_intervention(r: Intervention):
    return {
        "id": r.id,
        "student_id": r.student_id,
        "category": r.category,
        "level": r.level,
        "title": r.title,
        "plan_text": r.plan_text,
        "target": r.target,
        "milestones": json.loads(r.milestones) if r.milestones else [],
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "closed_at": r.closed_at.isoformat() if r.closed_at else None,
        "baseline_index": r.baseline_index,
        "current_index": r.current_index,
        "effect": r.effect,
        "follow_notes": json.loads(r.follow_notes) if r.follow_notes else [],
    }


def _dump_plan(p: LearningPlan):
    return {
        "id": p.id,
        "student_id": p.student_id,
        "semester": p.semester,
        "week_start": str(p.week_start),
        "title": p.title,
        "goals": json.loads(p.goals) if p.goals else [],
        "items": json.loads(p.items) if p.items else [],
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ---------------------------------------------------------------- 学情报告

@router.get("/learning-report")
def get_learning_report(scope: str = Query(...), student_id: int = Query(None, gt=0),
                        class_name: str = Query(None), grade: str = Query(None),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    """学生/班级/年级三级 AI 学情诊断报告。"""
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if scope == "student":
        if not student_id:
            raise HTTPException(400, "student_id is required")
        _check_student(user, db, student_id)
        return learning_report.student_report(db, student_id)
    if scope == "class":
        if not class_name:
            raise HTTPException(400, "class_name is required")
        _check_class(user, db, class_name)
        return learning_report.class_report(db, class_name)
    if scope == "grade":
        _require_staff(user)
        g = grade or (user.grade if user.role == "grade_leader" else None)
        if not g:
            raise HTTPException(400, "grade is required")
        if user.role == "grade_leader" and g != user.grade:
            raise HTTPException(403, "年级组长仅可查看本年级")
        return learning_report.grade_report(db, g)
    raise HTTPException(400, "scope must be student/class/grade")


@router.get("/growth-narrative")
def get_growth_narrative(student_id: int = Query(..., gt=0),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_student(user, db, student_id)
    result = narrative.growth_narrative(db, student_id)
    if not result:
        raise HTTPException(404, "学生不存在")
    return result


@router.get("/talent")
def get_talent(student_id: int = Query(..., gt=0),
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_student(user, db, student_id)
    result = talent.talent_analysis(db, student_id)
    if not result:
        raise HTTPException(404, "学生不存在")
    return result


# ---------------------------------------------------------------- 心理树洞

@router.get("/emotion-risk")
def get_emotion_risk(student_id: int = Query(..., gt=0),
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_student(user, db, student_id)
    if not db.query(Student.id).filter(Student.id == student_id).first():
        raise HTTPException(404, "学生不存在")
    return emotion_companion.emotion_risk(db, student_id)


@router.get("/companion/history")
def get_companion_history(student_id: int = Query(..., gt=0), limit: int = Query(50, ge=1, le=200),
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_student(user, db, student_id)
    rows = db.query(CompanionChat).filter(CompanionChat.student_id == student_id) \
        .order_by(CompanionChat.created_at.desc()).limit(limit).all()
    return [{
        "id": r.id, "role": r.role, "message": r.message, "intent": r.intent,
        "risk_flag": bool(r.risk_flag),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in reversed(rows)]


@router.post("/companion/chat")
def companion_chat(payload: dict = Body(...), user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """树洞对话：仅限学生本人发起。"""
    student_id = payload.get("student_id")
    message = (payload.get("message") or "").strip()
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if user.role != "student" or user.student_id != student_id:
        raise HTTPException(403, "树洞仅支持学生本人使用")
    if not student_id or student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    if not message or len(message) > 500:
        raise HTTPException(400, "message must be 1-500 chars")
    if not db.query(Student.id).filter(Student.id == student_id).first():
        raise HTTPException(404, "学生不存在")

    result = emotion_companion.companion_reply(db, student_id, message)
    db.add(CompanionChat(student_id=student_id, role="user", message=message,
                         intent=result["intent"], risk_flag=1 if result.get("risk_flag") else 0))
    db.add(CompanionChat(student_id=student_id, role="assistant", message=result["reply"],
                         intent=result["intent"], risk_flag=1 if result.get("risk_flag") else 0))
    db.commit()
    return result


# ---------------------------------------------------------------- 预警干预闭环

@router.get("/warning-board")
def get_warning_board(class_name: str = Query(None), grade: str = Query(None),
                      level: str = Query(None),
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    """预警看板：按范围返回风险分级学生列表。"""
    _require_staff(user)
    q = db.query(Student)
    if class_name:
        _check_class(user, db, class_name)
        q = q.filter(Student.class_name == class_name)
    elif grade:
        if user.role == "grade_leader" and grade != user.grade:
            raise HTTPException(403, "年级组长仅可查看本年级")
        q = q.filter(Student.grade == grade)
    elif user.role == "teacher":
        q = q.filter(Student.class_name == user.class_name)
    elif user.role == "grade_leader":
        q = q.filter(Student.grade == user.grade)
    students = q.order_by(Student.id).all()
    if not students:
        return []
    risks = intervention.assess_risks(db, [s.id for s in students])
    if level:
        risks = [r for r in risks if r["risk_level"] == level]
    return risks


@router.get("/interventions")
def list_interventions(student_id: int = Query(None, gt=0), status: str = Query(None),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_staff(user)
    q = db.query(Intervention)
    if student_id:
        _check_student(user, db, student_id)
        q = q.filter(Intervention.student_id == student_id)
    elif user.role == "teacher":
        ids = [s.id for s in db.query(Student).filter(Student.class_name == user.class_name).all()]
        q = q.filter(Intervention.student_id.in_(ids))
    elif user.role == "grade_leader":
        ids = [s.id for s in db.query(Student).filter(Student.grade == user.grade).all()]
        q = q.filter(Intervention.student_id.in_(ids))
    if status:
        q = q.filter(Intervention.status == status)
    rows = q.order_by(Intervention.created_at.desc()).all()
    return [_dump_intervention(r) for r in rows]


@router.post("/interventions")
def create_intervention(payload: dict = Body(...), user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """为风险学生创建干预方案（AI 自动生成方案文本，可覆盖调整）。"""
    _require_staff(user)
    student_id = payload.get("student_id")
    if not isinstance(student_id, int) or student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    _check_student(user, db, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    risk = intervention.student_risk(db, student_id)
    warnings = (risk or {}).get("warnings") or []
    plan = intervention.build_intervention_plan(warnings)
    if not plan:
        raise HTTPException(400, "该学生暂无明确预警信号，无需干预")

    baseline = payload.get("baseline_index")
    if baseline is None:
        from backend.ai_modules.analysis import compute_growth_profile
        profile = compute_growth_profile(student_id, db)
        baseline = round(profile["growth_index"], 1) if profile else None

    rec = Intervention(
        student_id=student_id,
        category=plan["category"],
        level=(risk or {}).get("risk_level", "yellow"),
        title=plan["title"],
        plan_text=payload.get("plan_text") or plan["plan_text"],
        target=plan["target"],
        milestones=json.dumps(plan["milestones"], ensure_ascii=False),
        status="open",
        created_by=user.id,
        baseline_index=baseline,
        follow_notes=json.dumps([], ensure_ascii=False),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _dump_intervention(rec)


@router.post("/interventions/{plan_id}/follow")
def follow_intervention(plan_id: int = Path(...), payload: dict = Body(...),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    """记录跟进并标记为进行中。"""
    _require_staff(user)
    rec = db.query(Intervention).filter(Intervention.id == plan_id).first()
    if not rec:
        raise HTTPException(404, "干预方案不存在")
    _check_student(user, db, rec.student_id)
    notes = json.loads(rec.follow_notes) if rec.follow_notes else []
    note = (payload.get("note") or "").strip()
    if note:
        notes.append({"time": datetime.now().isoformat(), "note": note, "by": user.name or user.username})
    rec.follow_notes = json.dumps(notes, ensure_ascii=False)
    rec.status = "in_progress"
    db.commit()
    db.refresh(rec)
    return _dump_intervention(rec)


@router.post("/interventions/{plan_id}/close")
def close_intervention(plan_id: int = Path(...), user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """关闭干预：自动对比干预前后成长指数，输出效果。"""
    _require_staff(user)
    rec = db.query(Intervention).filter(Intervention.id == plan_id).first()
    if not rec:
        raise HTTPException(404, "干预方案不存在")
    _check_student(user, db, rec.student_id)
    effect = intervention.compute_effect(db, rec.student_id, rec.baseline_index)
    rec.current_index = effect["current"]
    rec.effect = effect["delta"]
    rec.status = "closed"
    rec.closed_at = datetime.now()
    db.commit()
    db.refresh(rec)
    return _dump_intervention(rec)


# ---------------------------------------------------------------- 学习路径

@router.get("/learning-path")
def get_learning_path(student_id: int = Query(..., gt=0),
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    _check_student(user, db, student_id)
    row = db.query(LearningPlan).filter(LearningPlan.student_id == student_id) \
        .order_by(LearningPlan.created_at.desc()).first()
    if row:
        return _dump_plan(row)
    preview = learning_path.generate_plan(db, student_id)
    if not preview:
        raise HTTPException(404, "暂无成绩数据，无法生成学习计划")
    return {"preview": True, **preview}


@router.post("/learning-path/generate")
def generate_learning_path(payload: dict = Body(...), user=Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """重新生成并保存本周学习计划。"""
    student_id = payload.get("student_id")
    if not isinstance(student_id, int) or student_id <= 0:
        raise HTTPException(400, "Invalid student_id")
    _check_student(user, db, student_id)
    plan = learning_path.generate_plan(db, student_id)
    if not plan:
        raise HTTPException(400, "该学生暂无成绩数据，无法生成学习计划")
    rec = LearningPlan(
        student_id=student_id,
        semester=plan["semester"],
        week_start=date.fromisoformat(plan["week_start"]),
        title=plan["title"],
        goals=json.dumps(plan["goals"], ensure_ascii=False),
        items=json.dumps(plan["items"], ensure_ascii=False),
        status="active",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _dump_plan(rec)


@router.post("/learning-path/{plan_id}/toggle")
def toggle_learning_item(plan_id: int = Path(...), payload: dict = Body(...),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    """勾选/取消一个学习任务。"""
    key = payload.get("item_key")
    done = bool(payload.get("done"))
    if not key:
        raise HTTPException(400, "item_key is required")
    _require_staff(user)
    rec = db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    if not rec:
        raise HTTPException(404, "学习计划不存在")
    _check_student(user, db, rec.student_id)
    items = json.loads(rec.items) if rec.items else []
    for it in items:
        if it.get("key") == key:
            it["done"] = done
            break
    rec.items = json.dumps(items, ensure_ascii=False)
    db.commit()
    db.refresh(rec)
    return _dump_plan(rec)


# ---------------------------------------------------------------- 试卷分析 / 批阅辅助

@router.get("/paper-analysis")
def get_paper_analysis(plan_id: int = Query(..., gt=0), class_name: str = Query(...),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_staff(user)
    _check_class(user, db, class_name)
    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    result = paper_analysis.paper_analysis(db, plan, class_name)
    if not result:
        raise HTTPException(404, "该考试本班暂无成绩，请先批阅")
    return result


@router.get("/grade-hints")
def get_grade_hints(plan_id: int = Query(..., gt=0), class_name: str = Query(...),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    """批阅辅助：按学生历史成绩给出本场考试预估得分区间，供异常分数检测。"""
    _require_staff(user)
    _check_class(user, db, class_name)
    plan = db.query(ExamPlan).filter(ExamPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "考试规划不存在")
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    ids = [s.id for s in students]
    rows = db.query(Score).filter(
        Score.student_id.in_(ids), Score.subject == plan.subject, Score.score != None,
    ).all()
    from collections import defaultdict
    per = defaultdict(list)
    for r in rows:
        per[r.student_id].append(r.score / r.max_score * 100 if r.max_score else 0)
    from backend.constants import MAX_SCORES
    max_score = MAX_SCORES.get(plan.subject, 100)
    hints = {}
    for s in students:
        pcts = per.get(s.id, [])
        if pcts:
            avg_pct = sum(pcts) / len(pcts)
            expected = round(avg_pct / 100 * max_score, 1)
            lo = round(max(0, (avg_pct - 12) / 100 * max_score), 1)
            hi = round(min(max_score, (avg_pct + 12) / 100 * max_score), 1)
        else:
            expected, lo, hi = None, 0, max_score
        hints[s.id] = {"name": s.name, "expected": expected, "range": [lo, hi]}
    return {"subject": plan.subject, "max_score": max_score, "hints": hints}


# ---------------------------------------------------------------- 教师问数

@router.get("/ask")
def ask(user=Depends(get_current_user), db: Session = Depends(get_db), q: str = Query(..., min_length=1, max_length=200)):
    _require_staff(user)
    result = nl_query.answer_query(db, user, q)
    return result
