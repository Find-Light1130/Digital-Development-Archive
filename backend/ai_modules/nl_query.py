"""AI 教师问数（Copilot）：本地规则引擎的自然语言问数。

通过关键词槽位解析（范围：班级/年级；指标：平均分/掌握率/排名/预警/掉队/人数/最高最低；
学科）自动查库并生成一句话结论。纯本地实现，能力限定为结构化问答。
"""

import re

from backend.constants import MAX_SCORES, SEMESTER_ORDER
from backend.models import Student
from backend.ai_modules.common import (
    load_students, load_scores, subject_mastery, subject_trends, _avg,
)
from backend.routes.auth import user_scope

_SUBJECTS = list(MAX_SCORES.keys())
_CLASS_RE = re.compile(r'[初高][一二三]\d+班')
_GRADES = ("初一", "初二", "初三")

_INTENTS = [
    ("declining", ["掉队", "下滑", "退步", "下降", "滑坡", "滑落"]),
    ("warnings", ["预警", "风险", "关注", "需要帮助", "问题学生", "需关注"]),
    ("ranking", ["排名", "第几名", "第一名", "谁第一", "谁最", "最好的", "最差的"]),
    ("extremes", ["最高", "最低", "满分", "不及格", "及格"]),
    ("count", ["多少人", "几个学生", "人数", "多少学生", "有几", "多少个"]),
    ("mastery", ["平均分", "平均", "掌握率", "均分", "掌握", "情况", "怎么样", "如何", "整体"]),
]


def _detect_intent(q):
    for intent, kws in _INTENTS:
        for kw in kws:
            if kw in q:
                return intent
    return "mastery"


def _resolve_scope(db, user, q):
    """返回 (class_name, grade)；q 中的显式范围优先，否则取用户默认范围。"""
    class_name, grade = None, None
    m = _CLASS_RE.search(q)
    if m:
        class_name = m.group(0)
        grade = class_name[:2]
    else:
        for g in _GRADES:
            if g in q:
                grade = g
                break
    if not class_name and not grade:
        scope = user_scope(user)
        if scope.get("class_names"):
            class_name = scope["class_names"][0]
        elif scope.get("grades"):
            grade = scope["grades"][0]
    return class_name, grade


def _resolve_subject(q):
    for s in _SUBJECTS:
        if s in q:
            return s
    return None


def _class_students(db, class_name):
    return db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()


def _grade_students(db, grade):
    return db.query(Student).filter(Student.grade == grade).order_by(Student.id).all()


def _mastery_answer(db, students, subject):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    if subject:
        vals = [subject_mastery(rows).get(subject) for rows in scores.values() if subject_mastery(rows).get(subject)]
        vals = [v for v in vals if v is not None]
        avg = _avg(vals)
        cls = students[0].class_name if students else ""
        return (f"{cls or '范围内'}的{subject}平均掌握率为{avg}%"
                + (f"（{len(vals)}人）" if vals else ""), {"subject": subject, "avg": avg, "count": len(vals)})
    all_vals = []
    for rows in scores.values():
        all_vals.extend(subject_mastery(rows).values())
    avg = _avg(all_vals)
    top = sorted(_aggregate_subjects(scores).items(), key=lambda kv: -kv[1])[:3]
    return (f"整体平均掌握率约{avg}%，表现最好的学科为{('、'.join(s for s, _ in top))}",
            {"avg": avg, "top_subjects": [s for s, _ in top]})


def _aggregate_subjects(scores):
    acc = {}
    for rows in scores.values():
        for subj, val in subject_mastery(rows).items():
            acc.setdefault(subj, []).append(val)
    return {k: _avg(v) for k, v in acc.items()}


def _declining_answer(db, students, subject):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    result = []
    for sid, rows in scores.items():
        trends = subject_trends(rows)
        for subj, t in trends.items():
            if subject and subj != subject:
                continue
            if t.get("recent_sem_monotonic_decline") or t.get("trend") == "down":
                result.append({"student_id": sid, "subject": subj,
                               "text": f"{subj}持续下滑" if t.get("recent_sem_monotonic_decline") else f"{subj}整体下滑"})
    students_map = load_students(db, ids)
    result = [{"student_id": r["student_id"], "name": students_map[r["student_id"]].name,
               "class_name": students_map[r["student_id"]].class_name, "subject": r["subject"], "text": r["text"]}
              for r in result]
    if not result:
        return "暂未发现明显成绩下滑的学生。", []
    answer = "成绩下滑学生：" + "、".join(f"{r['name']}（{r['text']}）" for r in result[:8])
    if len(result) > 8:
        answer += f" 等{len(result)}人次"
    return answer, result


def _warnings_answer(db, students):
    from backend.ai_modules.intervention import assess_risks
    risks = assess_risks(db, [s.id for s in students])
    flagged = [r for r in risks if r["risk_level"] in ("red", "yellow")]
    if not flagged:
        return "当前范围内没有需要特别关注的学生。", []
    answer = "需关注学生：" + "、".join(
        f"{r['name']}（{'红' if r['risk_level']=='red' else '黄'}·{r['warnings'][0]['text'] if r['warnings'] else ''}）"
        for r in flagged[:8])
    if len(flagged) > 8:
        answer += f" 共{len(flagged)}人"
    return answer, flagged


def _ranking_answer(db, students, subject):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    if not subject:
        subject = _SUBJECTS[0]
    vals = []
    for sid, rows in scores.items():
        m = subject_mastery(rows).get(subject)
        if m is not None:
            vals.append((sid, m))
    if not vals:
        return f"暂无{subject}成绩数据。", []
    vals.sort(key=lambda kv: (-kv[1], kv[0]))
    students_map = load_students(db, ids)
    top = vals[0]
    names = [f"{students_map[sid].name}" for sid, _ in vals[:3]]
    return (f"{subject}掌握率排名第一的是{students_map[top[0]].name}（{top[1]}%），前三名：{'、'.join(names)}。",
            [{"student_id": sid, "name": students_map[sid].name, "value": v} for sid, v in vals[:10]])


def _extremes_answer(db, students, subject):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    if not subject:
        subject = _SUBJECTS[0]
    vals = []
    for sid, rows in scores.items():
        m = subject_mastery(rows).get(subject)
        if m is not None:
            vals.append((sid, m))
    if not vals:
        return f"暂无{subject}成绩数据。", []
    vals.sort(key=lambda kv: (-kv[1], kv[0]))
    students_map = load_students(db, ids)
    hi = vals[0]
    lo = vals[-1]
    return (f"{subject}最高为{students_map[hi[0]].name}（{hi[1]}%），最低为{students_map[lo[0]].name}（{lo[1]}%）。",
            {"highest": {"name": students_map[hi[0]].name, "value": hi[1]},
             "lowest": {"name": students_map[lo[0]].name, "value": lo[1]}})


def _count_answer(db, students):
    cls = students[0].class_name if students else ""
    return f"{cls or '范围内'}共有{len(students)}名学生。", {"count": len(students)}


def answer_query(db, user, query):
    q = (query or "").strip()
    class_name, grade = _resolve_scope(db, user, q)
    subject = _resolve_subject(q)
    intent = _detect_intent(q)

    if class_name:
        students = _class_students(db, class_name)
        if not students:
            return {"query": q, "class_name": class_name, "intent": intent, "subject": subject,
                    "answer": "未找到该班级。", "data": None}
    elif grade:
        students = _grade_students(db, grade)
        if not students:
            return {"query": q, "grade": grade, "intent": intent, "subject": subject,
                    "answer": "未找到该年级学生。", "data": None}
    else:
        return {"query": q, "intent": intent, "subject": subject,
                "answer": "我没有权限访问这个范围，或请明确说明班级/年级。", "data": None}

    if not students:
        return {"query": q, "intent": intent, "subject": subject, "answer": "数据不足。", "data": None}

    if intent == "declining":
        answer, data = _declining_answer(db, students, subject)
    elif intent == "warnings":
        answer, data = _warnings_answer(db, students)
    elif intent == "ranking":
        answer, data = _ranking_answer(db, students, subject)
    elif intent == "extremes":
        answer, data = _extremes_answer(db, students, subject)
    elif intent == "count":
        answer, data = _count_answer(db, students)
    else:
        answer, data = _mastery_answer(db, students, subject)

    return {
        "query": q,
        "class_name": class_name,
        "grade": grade,
        "intent": intent,
        "subject": subject,
        "answer": answer,
        "data": data,
    }
