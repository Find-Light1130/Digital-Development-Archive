"""AI 模块共享数据层与统计工具。

统一负责批量加载学生多维数据（成绩/情绪/活动/考勤/获奖/素质）以及
成绩掌握度、趋势等基础统计口径，供各 AI 模块复用，避免各自重复查询。
"""

from collections import defaultdict

from sqlalchemy import select

from backend.models import Student, Score, EmotionLog, Activity, Attendance, Award, QualityScore


# ---------------------------------------------------------------- 批量加载

def load_students(db, student_ids):
    if not student_ids:
        return {}
    return {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}


def load_scores(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(Score.student_id, Score.subject, Score.score, Score.max_score,
               Score.date, Score.semester, Score.exam_type)
        .where(Score.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_emotions(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(EmotionLog.student_id, EmotionLog.date, EmotionLog.emotion_level, EmotionLog.tags)
        .where(EmotionLog.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_activities(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(Activity.student_id, Activity.type, Activity.hours, Activity.date)
        .where(Activity.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_attendance(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(Attendance.student_id, Attendance.date, Attendance.present)
        .where(Attendance.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_awards(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(Award.student_id, Award.title, Award.level, Award.date)
        .where(Award.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_quality(db, student_ids):
    if not student_ids:
        return defaultdict(list)
    acc = defaultdict(list)
    for r in db.execute(
        select(QualityScore.id, QualityScore.student_id, QualityScore.subject, QualityScore.semester,
               QualityScore.dimension, QualityScore.score, QualityScore.grade)
        .where(QualityScore.student_id.in_(student_ids))
    ):
        acc[r.student_id].append(r)
    return acc


def load_all(db, student_ids):
    """一次加载全部维度，返回 {student_id: {...}}。"""
    students = load_students(db, student_ids)
    scores, emotions, activities, attendance = (
        load_scores(db, student_ids), load_emotions(db, student_ids),
        load_activities(db, student_ids), load_attendance(db, student_ids),
    )
    awards, quality = load_awards(db, student_ids), load_quality(db, student_ids)
    return {
        sid: {
            "student": students.get(sid),
            "scores": scores.get(sid, []),
            "emotions": emotions.get(sid, []),
            "activities": activities.get(sid, []),
            "attendance": attendance.get(sid, []),
            "awards": awards.get(sid, []),
            "quality": quality.get(sid, []),
        }
        for sid in student_ids if students.get(sid)
    }


# ---------------------------------------------------------------- 统计口径

def to_pct(score, max_score):
    if score is None or not max_score:
        return 50.0
    return round(score / max_score * 100, 1)


def subject_mastery(scores, recent_n=3):
    """各科掌握度：取最近 recent_n 次考试的平均百分制（与成长画像口径一致）。"""
    by_subject = defaultdict(list)
    for s in scores:
        by_subject[s.subject].append(s)
    mastery = {}
    for subj, vals in by_subject.items():
        ordered = sorted(vals, key=lambda x: x.date)
        recent = ordered[-recent_n:] if len(ordered) >= recent_n else ordered
        if not recent:
            continue
        mastery[subj] = round(sum(to_pct(s.score, s.max_score) for s in recent) / len(recent), 1)
    return mastery


def trend_label(pcts):
    """对一段百分制序列做线性回归，返回 up/down/stable（与成长画像口径一致）。"""
    n = len(pcts)
    if n < 4:
        return "stable"
    x_mean = (n - 1) / 2
    y_mean = sum(pcts) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(pcts))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    if slope > 1.0:
        return "up"
    if slope < -1.0:
        return "down"
    return "stable"


def is_monotonic_decreasing(pcts):
    for i in range(1, len(pcts)):
        if pcts[i] > pcts[i - 1]:
            return False
    return True


def subject_trends(scores):
    """各科趋势：按时间排序的百分制序列 + 趋势标签 + 最近一学期是否连续下滑。"""
    by_subject = defaultdict(list)
    for s in scores:
        if s.score is None or not s.max_score:
            continue
        by_subject[s.subject].append((s.date, to_pct(s.score, s.max_score), s.semester))
    result = {}
    for subj, items in by_subject.items():
        items.sort(key=lambda x: x[0])
        pcts = [p for _, p, _ in items]
        result[subj] = {
            "pcts": pcts,
            "trend": trend_label(pcts),
            "recent_sem_monotonic_decline": _recent_sem_decline(items),
            "latest": pcts[-1] if pcts else None,
        }
    return result


def _recent_sem_decline(items):
    """最近一个学期若所有考试百分制单调递减，返回该学期名，否则 None。"""
    sem_map = defaultdict(list)
    for _date, pct, sem in items:
        if sem:
            sem_map[sem].append(pct)
    if not sem_map:
        return None
    from backend.constants import SEMESTER_ORDER
    recent_sem = max(sem_map, key=lambda s: SEMESTER_ORDER.get(s, 0))
    vals = sem_map[recent_sem]
    if len(vals) >= 3 and is_monotonic_decreasing(vals):
        return recent_sem
    return None


TREND_ZH = {"up": "上升", "down": "下滑", "stable": "平稳"}


def avg_score(scores):
    if not scores:
        return None
    vals = [s.score for s in scores if s.score is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _avg(vals):
    if not vals:
        return 0
    return round(sum(vals) / len(vals), 1)
