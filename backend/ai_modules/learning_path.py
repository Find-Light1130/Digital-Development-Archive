"""AI 个性化学习路径：基于薄弱科目与趋势，为每个学生自动生成每周学习计划，
支持按新数据动态调整（重新生成），并跟踪完成进度。

计划包含：每周目标、分日学习任务（数据归因）、以及情绪风险时的心理调节任务。
"""

from datetime import date, timedelta

from backend.models import Student, Score
from backend.ai_modules.common import subject_mastery, subject_trends
from backend.ai_modules.emotion_companion import emotion_risk, regulation_prescription


def _task_pool(subject, trend_info):
    """按科目归因生成任务池。"""
    tasks = []
    if trend_info.get("recent_sem_monotonic_decline"):
        tasks.append((f"{subject}整理近期错题本，标出失分类型", 15))
        tasks.append((f"{subject}每周五复盘一次错题，重做错题2道", 20))
    elif trend_info.get("trend") == "down":
        tasks.append((f"{subject}回归课本，梳理一章核心概念", 20))
        tasks.append((f"{subject}做2道基础题，订正错题并写明原因", 15))
    else:
        tasks.append((f"{subject}完成课本例题1-2道并订正", 20))
        tasks.append((f"{subject}自测一个小知识点，标记薄弱处", 10))
    tasks.append((f"{subject}向老师或同学请教一个没弄懂的问题", 10))
    return tasks


def generate_plan(db, student_id, semester=None):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    scores = db.query(Score).filter(Score.student_id == student_id).order_by(Score.date).all()
    mastery = subject_mastery(scores)
    if not mastery:
        return None
    trends = subject_trends(scores)

    week_start = date.today() - timedelta(days=date.today().weekday())
    week_label = f"{week_start.month}月第{(week_start.day - 1) // 7 + 1}周"

    weak = sorted(mastery.items(), key=lambda kv: kv[1])[:3]
    goals = [f"{subj}掌握率 {v}%→{min(100, v + 5)}%" for subj, v in weak]
    items = []
    for idx, (subj, _v) in enumerate(weak):
        pool = _task_pool(subj, trends.get(subj, {}))
        for day, (task, minutes) in enumerate(pool):
            items.append({
                "key": f"{subj}-{day}",
                "subject": subj,
                "task": task,
                "minutes": minutes,
                "day": day + 1,
                "done": False,
            })

    mental_item = None
    risk = emotion_risk(db, student_id)
    if risk["level"] in ("medium", "high"):
        mental_item = {
            "key": "mental",
            "subject": "心理调节",
            "task": "完成一次情绪调节练习：" + regulation_prescription("anxious")[0],
            "minutes": 10,
            "day": 7,
            "done": False,
        }
        items.append(mental_item)

    return {
        "student_id": student_id,
        "name": student.name,
        "semester": semester or (scores[-1].semester if scores else "当前"),
        "week_start": str(week_start),
        "week_label": week_label,
        "title": "·".join(s for s, _ in weak) + " 提升计划",
        "goals": goals,
        "items": items,
        "mental_risk": risk["level"] in ("medium", "high"),
    }


def plan_progress(items):
    total = len(items)
    done = sum(1 for it in items if it.get("done"))
    return {
        "total": total,
        "done": done,
        "percent": round(done / total * 100, 1) if total else 0,
    }
