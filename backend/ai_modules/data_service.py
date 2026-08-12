"""AI 问数全量数据服务：对 students/scores/quality_scores/attendance/emotions/
activities/awards/exam_plans 等全表做聚合统计，供智能AI助手按意图生成答案。

统一基于 common.py 的批量加载与统计口径，避免各模块重复查询。
"""

from collections import defaultdict

from backend.ai_modules import analysis
from backend.ai_modules.common import (
    load_scores, load_emotions, load_activities, load_attendance,
    load_awards, load_quality, subject_mastery, avg_score, _avg,
)
from backend.ai_modules.analysis import batch_growth_profiles


# ---------------------------------------------------------------- 考勤

def attendance_summary(db, student_ids):
    """每人出勤率：{student_id: {"rate": 0-100, "absent": n, "total": n}}。"""
    data = load_attendance(db, student_ids)
    result = {}
    for sid, rows in data.items():
        if not rows:
            continue
        total = len(rows)
        present = sum(1 for r in rows if r.present)
        result[sid] = {
            "rate": round(present / total * 100, 1),
            "absent": total - present,
            "total": total,
        }
    return result


def low_attendance_students(db, student_ids, threshold=90.0, limit=8):
    """出勤率低于阈值的名单，按出勤率升序。返回 [(student, rate)]。"""
    from backend.ai_modules.common import load_students
    att = attendance_summary(db, student_ids)
    students = load_students(db, student_ids)
    rows = []
    for sid, info in att.items():
        if info["rate"] < threshold:
            rows.append((students.get(sid), info["rate"], info["absent"]))
    rows.sort(key=lambda x: x[1])
    return rows[:limit]


# ---------------------------------------------------------------- 情绪

def emotion_stats(db, student_ids):
    """每人近期情绪：均值 + 风险等级。复用 emotion_companion.emotion_risk 口径。"""
    from backend.ai_modules.emotion_companion import emotion_risk
    result = {}
    for sid in student_ids:
        risk = emotion_risk(db, sid)
        if risk.get("recent"):
            result[sid] = risk
    return result


def low_emotion_students(db, student_ids, limit=8):
    """情绪风险（medium/high）名单。返回 [(student, level, reason)]。"""
    from backend.ai_modules.common import load_students
    students = load_students(db, student_ids)
    rows = []
    for sid, risk in emotion_stats(db, student_ids).items():
        if risk["level"] in ("medium", "high"):
            reason = risk["reasons"][0] if risk["reasons"] else risk["level"]
            rows.append((students.get(sid), risk["level"], reason))
    order = {"high": 0, "medium": 1}
    rows.sort(key=lambda x: order.get(x[1], 9))
    return rows[:limit]


# ---------------------------------------------------------------- 素质 / 音体美信

def quality_summary(db, student_ids):
    """每人音体美信各科最近一次等级：{student_id: {subject: grade}}。"""
    data = load_quality(db, student_ids)
    result = {}
    for sid, rows in data.items():
        best = {}
        for r in rows:
            cur = best.get(r.subject)
            # 取最近一次记录（id 越大越新）
            if cur is None or r.id > cur.id:
                best[r.subject] = r
        result[sid] = {subj: r.grade for subj, r in best.items()}
    return result


def quality_subject_ranking(db, student_ids, subject):
    """按某素质科目等级排序（A+ > A > A- > ...）。返回 [(student, grade)]。"""
    from backend.ai_modules.common import load_students
    from backend.constants import GRADE_LEVELS
    grade_rank = {g: i for i, (_, g) in enumerate(GRADE_LEVELS)}
    students = load_students(db, student_ids)
    rows = []
    for sid, subs in quality_summary(db, student_ids).items():
        g = subs.get(subject)
        if g:
            rows.append((students.get(sid), g, grade_rank.get(g, 99)))
    rows.sort(key=lambda x: (x[2], x[0].id if x[0] else 0))
    return rows


def quality_best(db, student_ids, subject):
    """某素质科目等级最高的学生（并列取全部）。"""
    rows = quality_subject_ranking(db, student_ids, subject)
    if not rows:
        return []
    top_rank = rows[0][2]
    return [r for r in rows if r[2] == top_rank]


# ---------------------------------------------------------------- 活动

def activity_summary(db, student_ids):
    """每人活动时长/次数按类型：{student_id: {type: {"hours": x, "count": n}}}。"""
    data = load_activities(db, student_ids)
    result = {}
    for sid, rows in data.items():
        acc = defaultdict(lambda: {"hours": 0.0, "count": 0})
        for r in rows:
            acc[r.type]["count"] += 1
            if r.hours:
                acc[r.type]["hours"] += r.hours
        result[sid] = dict(acc)
    return result


def activity_top(db, student_ids, activity_type=None, limit=5):
    """活动量最大（按小时）的学生；activity_type 为空则统计总时长。"""
    from backend.ai_modules.common import load_students
    students = load_students(db, student_ids)
    data = activity_summary(db, student_ids)
    totals = []
    for sid, types in data.items():
        if activity_type:
            info = types.get(activity_type)
            hours = info["hours"] if info else 0.0
            count = info["count"] if info else 0
        else:
            hours = sum(t["hours"] for t in types.values())
            count = sum(t["count"] for t in types.values())
        totals.append((students.get(sid), hours, count))
    totals.sort(key=lambda x: (-x[1], x[0].id if x[0] else 0))
    return totals[:limit]


# ---------------------------------------------------------------- 获奖

def award_summary(db, student_ids):
    """每人获奖：{student_id: {"count": n, "levels": {level: n}, "titles": [...]}}。"""
    data = load_awards(db, student_ids)
    result = {}
    for sid, rows in data.items():
        levels = defaultdict(int)
        titles = []
        for r in rows:
            levels[r.level] += 1
            titles.append(r.title)
        result[sid] = {"count": len(rows), "levels": dict(levels), "titles": titles}
    return result


def award_students(db, student_ids, limit=8):
    """获奖学生名单，按获奖数降序。返回 [(student, count, top_level)]。"""
    from backend.ai_modules.common import load_students
    from backend.constants import AWARD_LEVELS
    level_rank = {lvl: i for i, lvl in enumerate(AWARD_LEVELS)}
    students = load_students(db, student_ids)
    rows = []
    for sid, info in award_summary(db, student_ids).items():
        if info["count"]:
            best_level = min(info["levels"], key=lambda l: level_rank.get(l, 9))
            rows.append((students.get(sid), info["count"], best_level))
    rows.sort(key=lambda x: (-x[1], x[0].id if x[0] else 0))
    return rows[:limit]


# ---------------------------------------------------------------- 考试规划

def exam_plans(db, grade=None, class_name=None):
    """考试规划列表（可按年级/班级过滤）。返回 [{...}]。"""
    from backend.models import ExamPlan, Student
    q = db.query(ExamPlan)
    if grade:
        q = q.filter(ExamPlan.grade == grade)
    elif class_name:
        # 班级 → 需先确认该班年级
        stu = db.query(Student).filter(Student.class_name == class_name).first()
        if stu:
            q = q.filter(ExamPlan.grade == stu.grade)
        else:
            return []
    rows = q.order_by(ExamPlan.exam_date.desc()).all()
    return [{
        "id": p.id, "exam_type": p.exam_type, "subject": p.subject,
        "grade": p.grade, "exam_date": str(p.exam_date),
        "semester": p.semester, "status": p.status,
    } for p in rows]


# ---------------------------------------------------------------- 成长指数

def growth_summary(db, student_ids):
    """每人成长指数（light 模式）。{student_id: {"growth_index": x, "aspects": {...}}}。"""
    return batch_growth_profiles(student_ids, db, light=True)


def growth_ranking(db, student_ids, limit=8):
    """成长指数排行。返回 [(student, growth_index)]。"""
    from backend.ai_modules.common import load_students
    students = load_students(db, student_ids)
    profiles = growth_summary(db, student_ids)
    rows = []
    for sid, p in profiles.items():
        rows.append((students.get(sid), p["growth_index"]))
    rows.sort(key=lambda x: (-x[1], x[0].id if x[0] else 0))
    return rows[:limit]


# ---------------------------------------------------------------- 成绩趋势

def class_subject_trend(db, student_ids, subject):
    """某班某科平均掌握率的时间序列（按考试日期聚合）。返回 [(date, avg_pct)]。"""
    scores = load_scores(db, student_ids)
    buckets = defaultdict(list)
    for rows in scores.values():
        for s in rows:
            if s.subject != subject or s.score is None or not s.max_score:
                continue
            buckets[s.date].append(s.score / s.max_score * 100)
    ordered = sorted(buckets.items())
    return [(str(d), round(sum(v) / len(v), 1)) for d, v in ordered]


def subject_trend_label(db, student_ids, subject):
    """某科平均掌握率趋势标签 up/down/stable。"""
    from backend.ai_modules.common import trend_label
    series = [v for _, v in class_subject_trend(db, student_ids, subject)]
    if len(series) < 2:
        return "stable"
    return trend_label(series)
