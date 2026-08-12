"""AI 考后试卷分析：从单场考试成绩自动计算难度、区分度、分数段，
并生成"本次考试暴露的教学问题"结论与教学建议。

难度系数 P = 均分 / 满分；区分度 D = (高分组27%均分 - 低分组27%均分) / 满分。
"""

from backend.models import Student, Score
from backend.constants import MAX_SCORES
from sqlalchemy import and_


def _difficulty_label(p):
    if p is None:
        return "数据不足"
    if p >= 0.75:
        return "偏易"
    if p >= 0.45:
        return "适中"
    return "偏难"


def _discrimination_label(d):
    if d is None:
        return "数据不足"
    if d >= 0.40:
        return "区分度优秀"
    if d >= 0.30:
        return "区分度良好"
    if d >= 0.20:
        return "区分度合格"
    return "区分度待改进"


def paper_analysis(db, plan, class_name):
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        return None
    ids = [s.id for s in students]
    rows = db.query(Score).filter(
        Score.student_id.in_(ids), Score.subject == plan.subject,
        Score.exam_type == plan.exam_type, Score.date == plan.exam_date,
    ).all()
    scored = [(r.student_id, r.score) for r in rows if r.score is not None]
    if not scored:
        return None

    max_s = MAX_SCORES.get(plan.subject, 100)
    n = len(scored)
    avg = round(sum(s for _, s in scored) / n, 1)
    highest = max(s for _, s in scored)
    lowest = min(s for _, s in scored)
    passed = sum(1 for _, s in scored if s >= max_s * 0.6)
    pass_rate = round(passed / n * 100, 1)

    difficulty = round(avg / max_s, 2) if max_s else None
    ranked = sorted(s for _, s in scored)
    group = max(1, int(n * 0.27))
    top_mean = sum(ranked[n - group:]) / group
    bottom_mean = sum(ranked[:group]) / group
    discrimination = round((top_mean - bottom_mean) / max_s, 2) if max_s else None

    buckets = {"优秀": 0, "良好": 0, "及格": 0, "待提高": 0}
    for _, s in scored:
        ratio = s / max_s
        if ratio >= 0.85:
            buckets["优秀"] += 1
        elif ratio >= 0.70:
            buckets["良好"] += 1
        elif ratio >= 0.60:
            buckets["及格"] += 1
        else:
            buckets["待提高"] += 1

    # 历史对比：本班该科历史均分（排除本次考试，避免自我污染）
    hist = db.query(Score).filter(
        Score.student_id.in_(ids), Score.subject == plan.subject, Score.score != None,
        ~and_(Score.exam_type == plan.exam_type, Score.date == plan.exam_date),
    ).all()
    hist_avg = round(sum(s.score for s in hist) / len(hist), 1) if hist else None
    vs_history = None
    if hist_avg is not None:
        vs_history = {
            "avg": hist_avg,
            "delta": round(avg - hist_avg, 1),
        }

    diff_label = _difficulty_label(difficulty)
    disc_label = _discrimination_label(discrimination)

    findings = []
    if difficulty is not None:
        if difficulty < 0.45:
            findings.append("本次试卷难度偏大，多数学生得分率低于平时，建议适当降低综合题比重并加强基础巩固")
        elif difficulty > 0.75:
            findings.append("本次试卷难度偏易，优秀率可能虚高，建议补充区分性题目以暴露真实差距")
        else:
            findings.append("本次试卷难度适中，能够较好地区分不同水平的学生")
    if discrimination is not None and discrimination < 0.2:
        findings.append("区分度不足，题目要么过难要么过易，建议调整题目梯度")
    if pass_rate < 70:
        findings.append(f"及格率仅{pass_rate}%，低分段学生较多，建议对这部分学生集中补基础、降低起点要求")

    teaching_suggestions = findings[:3] if findings else [
        "本次考试各项指标正常，继续保持当前教学节奏"
    ]

    summary = (
        f"本班共{n}人参加{plan.subject}{plan.exam_type}（满分{max_s}），均分{avg}、最高{highest}、最低{lowest}，"
        f"及格率{pass_rate}%。难度系数{difficulty if difficulty is not None else '-'}（{diff_label}），"
        f"区分度{discrimination if discrimination is not None else '-'}（{disc_label}）。"
        + (f"相较该科历史均分{hist_avg}，本次{'提高' if avg > hist_avg else '下降'}{abs(vs_history['delta'])}分。"
           if vs_history and avg != hist_avg else "")
    )

    return {
        "plan_id": plan.id,
        "subject": plan.subject,
        "exam_type": plan.exam_type,
        "exam_date": str(plan.exam_date),
        "semester": plan.semester,
        "class_name": class_name,
        "max_score": max_s,
        "count": n,
        "avg": avg,
        "highest": highest,
        "lowest": lowest,
        "pass_rate": pass_rate,
        "difficulty": difficulty,
        "difficulty_label": diff_label,
        "discrimination": discrimination,
        "discrimination_label": disc_label,
        "buckets": buckets,
        "vs_history": vs_history,
        "summary": summary,
        "teaching_suggestions": teaching_suggestions,
    }
