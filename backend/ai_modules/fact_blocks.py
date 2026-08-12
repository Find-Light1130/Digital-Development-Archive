"""事实块构建：把精确数据层结果组织为结构化事实，供 LLM 生成自然语言。

核心原则：LLM 只负责「理解与表达」，所有数字/名单/结论一律来自精确计算层，
避免小模型幻觉。各函数返回 {"facts": str, "data": obj}。
"""

from collections import defaultdict

from backend.constants import MAX_SCORES, QUALITY_SUBJECTS
from backend.models import Student
from backend.ai_modules.common import load_scores, subject_mastery, _avg, load_students
from backend.ai_modules import data_service


def _scope_label(class_name=None, grade=None):
    if class_name:
        return class_name
    if grade:
        return grade
    return "范围内"


def _with_scope(data, students, class_name=None, grade=None):
    """给 data 附加实际统计范围，供 LLM 答案生成防止幻觉错范围。"""
    if isinstance(data, dict):
        data = dict(data)
        data["scope"] = _scope_label(
            class_name or (students[0].class_name if students else None),
            grade)
    return data


def _students(db, class_name=None, grade=None, user=None):
    q = db.query(Student).order_by(Student.id)
    if class_name:
        return q.filter(Student.class_name == class_name).all()
    if grade:
        return q.filter(Student.grade == grade).all()
    return q.all()


# ---------------------------------------------------------------- 问数事实块

def mastery_facts(db, students, subject=None):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    label = _scope_label(students[0].class_name if students else None)
    if subject:
        vals = []
        for rows in scores.values():
            v = subject_mastery(rows).get(subject)
            if v is not None:
                vals.append(v)
        avg = _avg(vals)
        return {
            "facts": f"{label}的{subject}平均掌握率为{avg}%（{len(vals)}人参加统计）。",
            "data": {"subject": subject, "avg": avg, "count": len(vals)},
        }
    acc = defaultdict(list)
    for rows in scores.values():
        for subj, val in subject_mastery(rows).items():
            acc[subj].append(val)
    avg = _avg([v for vs in acc.values() for v in vs])
    top = sorted(acc.items(), key=lambda kv: -_avg(kv[1]))[:3]
    top_text = "、".join(f"{s}（{_avg(v)}%）" for s, v in top)
    return {
        "facts": f"{label}整体平均掌握率约{avg}%，表现最好的学科：{top_text}。",
        "data": {"avg": avg, "top_subjects": [s for s, _ in top]},
    }


def ranking_facts(db, students, subject=None):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    subject = subject or list(MAX_SCORES)[0]
    vals = []
    for sid, rows in scores.items():
        m = subject_mastery(rows).get(subject)
        if m is not None:
            vals.append((sid, m))
    label = _scope_label(students[0].class_name if students else None)
    if not vals:
        return {"facts": f"{label}暂无{subject}成绩数据。", "data": []}
    vals.sort(key=lambda kv: (-kv[1], kv[0]))
    smap = load_students(db, ids)
    top = vals[0]
    names = "、".join(f"{smap[sid].name}（{v}%）" for sid, v in vals[:3])
    return {
        "facts": f"{label}的{subject}掌握率排名：第一{top[0] and smap[top[0]].name}（{top[1]}%），前三：{names}。",
        "data": [{"student_id": sid, "name": smap[sid].name, "value": v} for sid, v in vals[:10]],
    }


def declining_facts(db, students, subject=None):
    from backend.ai_modules.common import subject_trends
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    label = _scope_label(students[0].class_name if students else None)
    result = []
    for sid, rows in scores.items():
        for subj, t in subject_trends(rows).items():
            if subject and subj != subject:
                continue
            if t.get("recent_sem_monotonic_decline") or t.get("trend") == "down":
                result.append({"student_id": sid, "subject": subj,
                               "text": "持续下滑" if t.get("recent_sem_monotonic_decline") else "整体下滑"})
    if not result:
        return {"facts": f"{label}暂未发现明显成绩下滑的学生。", "data": []}
    smap = load_students(db, ids)
    result = [{"student_id": r["student_id"], "name": smap[r["student_id"]].name,
               "class_name": smap[r["student_id"]].class_name, "subject": r["subject"],
               "text": r["text"]} for r in result]
    names = "、".join(f"{r['name']}（{r['subject']}{r['text']}）" for r in result[:8])
    return {"facts": f"{label}成绩下滑学生：{names}{' 等' + str(len(result)) + '人次' if len(result) > 8 else ''}。",
            "data": result}


def warnings_facts(db, students):
    from backend.ai_modules.intervention import assess_risks
    risks = assess_risks(db, [s.id for s in students])
    flagged = [r for r in risks if r["risk_level"] in ("red", "yellow")]
    label = _scope_label(students[0].class_name if students else None)
    if not flagged:
        return {"facts": f"{label}当前没有需要特别关注的学生。", "data": []}
    names = "、".join(
        f"{r['name']}（{'红' if r['risk_level']=='red' else '黄'}）" for r in flagged[:8])
    return {"facts": f"{label}需关注学生：{names}（共{len(flagged)}人）。", "data": flagged}


def extremes_facts(db, students, subject=None):
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    subject = subject or list(MAX_SCORES)[0]
    label = _scope_label(students[0].class_name if students else None)
    vals = []
    for sid, rows in scores.items():
        m = subject_mastery(rows).get(subject)
        if m is not None:
            vals.append((sid, m))
    if not vals:
        return {"facts": f"{label}暂无{subject}成绩数据。", "data": None}
    vals.sort(key=lambda kv: (-kv[1], kv[0]))
    smap = load_students(db, ids)
    hi, lo = vals[0], vals[-1]
    return {
        "facts": f"{label}的{subject}最高为{smap[hi[0]].name}（{hi[1]}%），最低为{smap[lo[0]].name}（{lo[1]}%）。",
        "data": {"highest": {"name": smap[hi[0]].name, "value": hi[1]},
                 "lowest": {"name": smap[lo[0]].name, "value": lo[1]}},
    }


def count_facts(db, students):
    label = _scope_label(students[0].class_name if students else None)
    return {"facts": f"{label}共有{len(students)}名学生。", "data": {"count": len(students)}}


def attendance_facts(db, students):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    rows = data_service.low_attendance_students(db, ids)
    summary = data_service.attendance_summary(db, ids)
    rates = [info["rate"] for info in summary.values()]
    if not rates:
        return {"facts": f"{label}暂无考勤记录。", "data": []}
    avg_rate = round(sum(rates) / len(rates), 1)
    if not rows:
        return {"facts": f"{label}平均出勤率{avg_rate}%，暂无出勤率低于90%的学生。",
                "data": {"avg_rate": avg_rate}}
    names = "、".join(f"{st.name}（{rate}%）" if st else str(rate) for st, rate, _ in rows[:8])
    return {"facts": f"{label}平均出勤率{avg_rate}%，出勤率偏低：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "rate": rate, "absent": absent}
                     for st, rate, absent in rows]}


def emotion_facts(db, students):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    rows = data_service.low_emotion_students(db, ids)
    if not rows:
        return {"facts": f"{label}暂无明显的情绪风险学生。", "data": []}
    names = "、".join(f"{st.name}（{'高风险' if lvl=='high' else '中风险'}）" if st else str(lvl)
                      for st, lvl, _ in rows[:8])
    return {"facts": f"{label}需要关注情绪的学生：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "level": lvl, "reason": reason}
                     for st, lvl, reason in rows]}


def quality_facts(db, students, subject=None):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    if not subject or subject not in QUALITY_SUBJECTS:
        summary = data_service.quality_summary(db, ids)
        counts = defaultdict(int)
        for subs in summary.values():
            for g in subs.values():
                counts[g] += 1
        if not counts:
            return {"facts": f"{label}暂无素质（音体美信）数据。", "data": []}
        total = sum(counts.values())
        top = max(counts.items(), key=lambda kv: kv[1])
        return {"facts": f"{label}素质评价共{total}条，最常见等级为{top[0]}（{top[1]}条）。",
                "data": {"levels": dict(counts)}}
    rows = data_service.quality_best(db, ids, subject)
    if not rows:
        return {"facts": f"{label}暂无{subject}素质数据。", "data": []}
    names = "、".join(f"{st.name}（{g}）" if st else str(g) for st, g, _ in rows[:8])
    return {"facts": f"{label}的{subject}等级最高学生：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "grade": g} for st, g, _ in rows]}


def activity_facts(db, students, activity_type=None):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    rows = data_service.activity_top(db, ids, activity_type)
    if not rows:
        return {"facts": f"{label}暂无活动记录。", "data": []}
    kind = {"体育": "体育", "实践": "实践", "社团": "社团", "阅读": "阅读"}.get(activity_type, "活动")
    names = "、".join(f"{st.name}（{hours}小时）" if st else f"{hours}小时" for st, hours, _ in rows[:5])
    return {"facts": f"{label}{kind}时长最多：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "hours": hours, "count": count}
                     for st, hours, count in rows]}


def award_facts(db, students):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    rows = data_service.award_students(db, ids)
    if not rows:
        return {"facts": f"{label}暂无获奖记录。", "data": []}
    names = "、".join(f"{st.name}（{count}项）" if st else str(count) for st, count, _ in rows[:8])
    return {"facts": f"{label}获奖学生：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "count": count, "top_level": lvl}
                     for st, count, lvl in rows]}


def exam_facts(db, students):
    label = _scope_label(students[0].class_name if students else None)
    stu = students[0] if students else None
    if not stu:
        return {"facts": "范围内暂无学生。", "data": []}
    plans = data_service.exam_plans(db, grade=stu.grade)
    if not plans:
        return {"facts": f"{stu.grade}暂无考试规划。", "data": []}
    upcoming = [p for p in plans if p["status"] == "planned"]
    recent = [p for p in plans if p["status"] != "planned"][:3]
    parts = []
    if upcoming:
        parts.append("待进行：" + "、".join(f"{p['subject']}·{p['exam_date']}" for p in upcoming[:5]))
    if recent:
        parts.append("最近已举行：" + "、".join(f"{p['subject']}·{p['exam_date']}" for p in recent[:3]))
    return {"facts": f"{stu.grade}考试安排——" + "；".join(parts), "data": {"plans": plans}}


def growth_facts(db, students):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    rows = data_service.growth_ranking(db, ids)
    if not rows:
        return {"facts": f"{label}暂无成长指数数据。", "data": []}
    vals = [g for _, g in rows]
    avg = round(sum(vals) / len(vals), 1)
    top = rows[0]
    names = "、".join(f"{st.name}（{g}）" if st else str(g) for st, g in rows[:3])
    return {"facts": f"{label}平均成长指数{avg}，最高为{top[0].name}（{top[1]}），前三：{names}。",
            "data": [{"student_id": st.id, "name": st.name, "growth_index": g} for st, g in rows]}


def trend_facts(db, students, subject=None):
    ids = [s.id for s in students]
    label = _scope_label(students[0].class_name if students else None)
    if not subject:
        return {"facts": "请说明要查看哪个学科的趋势。", "data": None}
    series = data_service.class_subject_trend(db, ids, subject)
    if len(series) < 2:
        return {"facts": f"{label}的{subject}数据不足，暂无法判断趋势。", "data": None}
    trend = data_service.subject_trend_label(db, ids, subject)
    latest, first = series[-1][1], series[0][1]
    delta = round(latest - first, 1)
    zh = {"up": "上升", "down": "下滑", "stable": "平稳"}
    return {"facts": f"{label}的{subject}平均掌握率呈{zh[trend]}趋势（{first}%→{latest}%，变化{delta:+g}个百分点）。",
            "data": {"subject": subject, "trend": trend, "series": series}}


def list_facts(db, students):
    label = _scope_label(students[0].class_name if students else None)
    names = "、".join(s.name for s in students[:15])
    if not names:
        return {"facts": "范围内暂无学生。", "data": []}
    suffix = f" 等{len(students)}名学生" if len(students) > 15 else ""
    return {"facts": f"{label}共有{len(students)}名学生：{names}{suffix}。",
            "data": {"count": len(students),
                     "students": [{"student_id": s.id, "name": s.name} for s in students[:50]]}}


FACT_BUILDERS = {
    "mastery": lambda db, st, subject=None: _wrap_scope(mastery_facts(db, st, subject), st),
    "ranking": lambda db, st, subject=None: _wrap_scope(ranking_facts(db, st, subject), st),
    "declining": lambda db, st, subject=None: _wrap_scope(declining_facts(db, st, subject), st),
    "warnings": lambda db, st, subject=None: _wrap_scope(warnings_facts(db, st), st),
    "extremes": lambda db, st, subject=None: _wrap_scope(extremes_facts(db, st, subject), st),
    "count": lambda db, st, subject=None: _wrap_scope(count_facts(db, st), st),
    "attendance": lambda db, st, subject=None: _wrap_scope(attendance_facts(db, st), st),
    "emotion": lambda db, st, subject=None: _wrap_scope(emotion_facts(db, st), st),
    "quality": lambda db, st, subject=None: _wrap_scope(quality_facts(db, st, subject), st),
    "activity": lambda db, st, subject=None: _wrap_scope(activity_facts(db, st), st),
    "award": lambda db, st, subject=None: _wrap_scope(award_facts(db, st), st),
    "exam_plan": lambda db, st, subject=None: _wrap_scope(exam_facts(db, st), st),
    "growth_index": lambda db, st, subject=None: _wrap_scope(growth_facts(db, st), st),
    "trend": lambda db, st, subject=None: _wrap_scope(trend_facts(db, st, subject), st),
    "list": lambda db, st, subject=None: _wrap_scope(list_facts(db, st), st),
}


def _wrap_scope(block, students):
    block["data"] = _with_scope(block["data"], students)
    return block
