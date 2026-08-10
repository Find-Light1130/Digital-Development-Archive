"""AI 学情诊断报告：基于统计归因 + 规则引擎，为学生/班级/年级自动生成中文诊断报告。

与成长画像不同，本模块聚焦"学习"维度：科目掌握度、趋势归因、班级定位、
预测与行动建议，以自然语言段落 + 结构化数据双重输出，替代分散的统计图表。
"""

from collections import defaultdict

from backend.models import Student
from backend.ai_modules.common import (
    load_all, load_students, load_scores, subject_mastery, subject_trends,
    TREND_ZH, _avg,
)
from backend.ai_modules.analysis import batch_growth_profiles, compute_growth_profile


def _class_subject_stats(db, class_name):
    """班级各科掌握度均值 + 每生各科排名。"""
    students = db.query(Student).filter(Student.class_name == class_name).all()
    ids = [s.id for s in students]
    scores = load_scores(db, ids)
    per_subject_student = defaultdict(dict)
    for sid, rows in scores.items():
        m = subject_mastery(rows)
        for subj, val in m.items():
            per_subject_student[subj][sid] = val
    stats = {}
    for subj, mapping in per_subject_student.items():
        ranked = sorted(mapping.items(), key=lambda kv: (-kv[1], kv[0]))
        avg = _avg([v for _, v in mapping.items()])
        stats[subj] = {"avg": avg, "count": len(mapping), "ranked": ranked}
    return stats


def _growth_rank(profiles, class_ids, student_id):
    if not class_ids:
        return None
    ranked = sorted((sid for sid in class_ids if sid in profiles),
                    key=lambda sid: -profiles[sid]["growth_index"])
    for i, sid in enumerate(ranked):
        if sid == student_id:
            return {"rank": i + 1, "total": len(ranked),
                    "growth_index": round(profiles[sid]["growth_index"], 1)}
    return None


def _verdict(mastery, trend, decline_sem):
    if mastery < 65 and (trend == "down" or decline_sem):
        return "薄弱且下滑", "重点科目，建议优先介入"
    if mastery < 65:
        return "基础偏弱", "建议从基础概念入手逐级巩固"
    if mastery < 75 and (trend == "down" or decline_sem):
        return "中等偏弱", "存在下滑风险，建议及时复盘"
    if mastery >= 85:
        return "优势科目", "表现优秀，可适当拓展难度"
    if trend == "down":
        return "小幅下滑", "整体尚可但需关注下滑苗头"
    return "表现平稳", "保持当前节奏即可"


def _subject_block(subj, mastery, trend, decline_sem, class_avg, class_rank, class_total):
    verdict, note = _verdict(mastery, trend, decline_sem)
    deviation = round(mastery - class_avg, 1) if class_avg is not None else None
    para_parts = [f"{subj}掌握率 {mastery}%"]
    if class_avg is not None:
        para_parts.append(f"低于班级平均 {class_avg}%" if deviation < 0 else f"高于班级平均 {class_avg}%")
    if class_rank is not None:
        para_parts.append(f"班级第 {class_rank}/{class_total}")
    if trend != "stable":
        para_parts.append(f"整体呈{TREND_ZH[trend]}趋势")
    if decline_sem:
        para_parts.append(f"{decline_sem}以来连续下滑")
    return {
        "subject": subj,
        "mastery": mastery,
        "trend": trend,
        "trend_label": TREND_ZH[trend],
        "decline_semester": decline_sem,
        "class_avg": class_avg,
        "deviation": deviation,
        "class_rank": class_rank,
        "class_total": class_total,
        "verdict": verdict,
        "note": note,
        "paragraph": "，".join(para_parts) + "。",
    }


def _predict(subj_trend):
    pcts = subj_trend.get("pcts") or []
    if len(pcts) < 2:
        return None
    step = pcts[-1] - pcts[-2]
    nxt = round(min(100, max(0, pcts[-1] + step)), 1)
    if step > 1:
        return f"按当前节奏，预计下次考试在{pcts[-1]}%基础上继续走高至约{nxt}%"
    if step < -1:
        return f"按当前下滑节奏，预计下次考试将从{pcts[-1]}%回落至约{nxt}%，需提前干预"
    return f"成绩走势平稳，预计下次考试维持在{nxt}%左右"


# ---------------------------------------------------------------- 学生报告

def student_report(db, student_id):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    data = load_all(db, [student_id]).get(student_id)
    if not data:
        return None
    scores = data["scores"]
    mastery = subject_mastery(scores)
    trends = subject_trends(scores)
    profile = compute_growth_profile(student_id, db) or {}

    classmates = db.query(Student).filter(Student.class_name == student.class_name).all()
    class_ids = [s.id for s in classmates]
    class_stats = _class_subject_stats(db, student.class_name)
    profiles = batch_growth_profiles(class_ids, db, light=True)
    growth_rank = _growth_rank(profiles, class_ids, student_id)

    subjects = []
    for subj, m in sorted(mastery.items(), key=lambda kv: -kv[1]):
        st = trends.get(subj, {})
        st_subj = class_stats.get(subj, {})
        ranked = st_subj.get("ranked") or []
        rank = None
        if ranked:
            for i, (sid, _v) in enumerate(ranked):
                if sid == student_id:
                    rank = i + 1
                    break
        subjects.append(_subject_block(
            subj, m, st.get("trend", "stable"),
            st.get("recent_sem_monotonic_decline"),
            st_subj.get("avg"), rank, len(ranked) or None,
        ))

    weak = sorted([s for s in subjects if s["mastery"] < 75], key=lambda x: x["mastery"])[:3]
    strong = sorted([s for s in subjects if s["mastery"] >= 75], key=lambda x: -x["mastery"])[:3]
    mastery_avg = _avg(list(mastery.values())) if mastery else 0
    trend_counts = defaultdict(int)
    for s in subjects:
        trend_counts[s["trend"]] += 1
    overall_trend = "up" if trend_counts.get("up", 0) > trend_counts.get("down", 0) else (
        "down" if trend_counts.get("down", 0) else "stable")

    suggestions = []
    for sb in weak[:2]:
        if sb["trend"] == "down" or sb["decline_semester"]:
            suggestions.append(
                f"{sb['subject']}掌握率仅{sb['mastery']}%且持续下滑，建议每周整理错题本、找任课老师定位失分点后系统复习")
        else:
            suggestions.append(
                f"{sb['subject']}基础偏弱（掌握率{sb['mastery']}%），建议每天固定15分钟从课本例题和基础概念入手")
    if strong:
        suggestions.append(f"优势科目{strong[0]['subject']}表现突出，可挑战更高难度题目并总结方法迁移到薄弱科")
    if profile.get("warnings"):
        for w in profile["warnings"][:1]:
            suggestions.append(f"预警提醒：{w}")
    if len(suggestions) < 2:
        suggestions.append("各科表现均衡，建议保持规律作息并每周设定一个小目标稳步提升")

    prediction = _predict(trends.get(weak[0]["subject"])) if weak else None
    pred_subject = weak[0]["subject"] if weak else None

    summary = (
        f"{student.name}的综合成长指数为{round(profile.get('growth_index', 0), 1)}分"
        + (f"，居班级第{growth_rank['rank']}名（共{growth_rank['total']}人）" if growth_rank else "")
        + f"，各科平均掌握率{mastery_avg}%。学习整体呈{TREND_ZH[overall_trend]}态势。"
        + ("优势学科包括" + "、".join(s["subject"] for s in strong) if strong else "暂无明显优势学科")
        + "，" + ("薄弱学科为" + "、".join(s["subject"] for s in weak) if weak else "无薄弱学科")
        + "。"
    )

    return {
        "student_id": student_id,
        "name": student.name,
        "grade": student.grade,
        "class_name": student.class_name,
        "generated_at": None,
        "overview": {
            "growth_index": round(profile.get("growth_index", 0), 1),
            "mastery_avg": mastery_avg,
            "trend": overall_trend,
            "trend_label": TREND_ZH[overall_trend],
            "growth_rank": growth_rank,
            "warnings": profile.get("warnings", []),
        },
        "summary": summary,
        "subjects": subjects,
        "strengths": [s["subject"] for s in strong],
        "weaknesses": [s["subject"] for s in weak],
        "suggestions": suggestions[:5],
        "prediction": prediction,
        "prediction_subject": pred_subject,
    }


# ---------------------------------------------------------------- 班级报告

def class_report(db, class_name):
    students = db.query(Student).filter(Student.class_name == class_name).order_by(Student.id).all()
    if not students:
        return None
    ids = [s.id for s in students]
    profiles = batch_growth_profiles(ids, db)
    class_stats = _class_subject_stats(db, class_name)

    total_index = _avg([p["growth_index"] for p in profiles.values() if "growth_index" in p])
    needs_attention = [{
        "student_id": s.id, "name": s.name, "reason": (profiles.get(s.id) or {}).get("warnings", [""])[0],
    } for s in students if profiles.get(s.id) and profiles[s.id].get("warnings")]
    distribution = defaultdict(int)
    for p in profiles.values():
        gi = p["growth_index"]
        bucket = min(19, max(0, int(gi // 5)))
        distribution[f"{bucket*5}~{bucket*5+4}"] += 1

    subject_rows = []
    for subj, st in sorted(class_stats.items()):
        pcts = []
        for sid, val in st["ranked"]:
            pcts.append(val)
        subject_rows.append({
            "subject": subj,
            "avg": st["avg"],
            "count": st["count"],
        })
    subject_rows.sort(key=lambda x: -x["avg"])
    weak = [r["subject"] for r in subject_rows[:3] if r["avg"] < 75]
    strong = [r["subject"] for r in subject_rows if r["avg"] >= 80]

    teaching = []
    if weak:
        teaching.append(f"班级共性薄弱学科为{'、'.join(weak)}，建议在讲评中重点回归基础概念并布置分层练习")
    if needs_attention:
        teaching.append(f"有{len(needs_attention)}名学生需重点关注，建议制定一对一跟进计划并定期回看")
    if not teaching:
        teaching.append("班级整体掌握情况良好，可适当提高课堂拓展难度")

    paragraph = (
        f"{class_name}共{len(students)}人，班级平均成长指数{total_index}分，"
        f"需关注学生{len(needs_attention)}人。各科平均掌握率最高为"
        + (f"{strong[0]}（{_avg([s['avg'] for s in subject_rows if s['subject']==strong[0]])}%）" if strong else "—")
        + f"，最低为" + (f"{weak[0]}（{_avg([s['avg'] for s in subject_rows if s['subject']==weak[0]])}%）" if weak else "—")
        + "。"
    )

    return {
        "class_name": class_name,
        "grade": students[0].grade,
        "student_count": len(students),
        "avg_growth_index": total_index,
        "needs_attention": needs_attention[:10],
        "needs_attention_count": len(needs_attention),
        "distribution": [{"bucket": k, "count": v} for k, v in sorted(distribution.items())],
        "subjects": subject_rows,
        "weak_subjects": weak,
        "strong_subjects": strong,
        "paragraph": paragraph,
        "teaching_suggestions": teaching,
    }


# ---------------------------------------------------------------- 年级报告

def grade_report(db, grade):
    students = db.query(Student).filter(Student.grade == grade).order_by(Student.id).all()
    if not students:
        return None
    ids = [s.id for s in students]
    profiles = batch_growth_profiles(ids, db, light=True)
    classes = {}
    for s in students:
        p = profiles.get(s.id)
        if not p:
            continue
        c = classes.setdefault(s.class_name, {"total": 0, "idx_sum": 0.0})
        c["total"] += 1
        c["idx_sum"] += p["growth_index"]
    class_rows = sorted(
        [{"class_name": k, "avg_growth_index": round(v["idx_sum"] / v["total"], 1), "student_count": v["total"]}
         for k, v in classes.items()],
        key=lambda x: x["class_name"],
    )

    scores = load_scores(db, ids)
    subj_vals = defaultdict(list)
    for rows in scores.values():
        for subj, val in subject_mastery(rows).items():
            subj_vals[subj].append(val)
    subject_rows = [{"subject": s, "avg": _avg(v)} for s, v in subj_vals.items()]
    subject_rows.sort(key=lambda x: -x["avg"])

    avg_index = _avg([p["growth_index"] for p in profiles.values()])
    weak = [r["subject"] for r in subject_rows[:3] if r["avg"] < 75]
    paragraph = (
        f"{grade}年级共{len(students)}名学生，平均成长指数{avg_index}分，共{len(class_rows)}个班级。"
        + (f"整体薄弱学科为{'、'.join(weak)}。" if weak else "各科整体掌握较为均衡。")
    )
    teaching = []
    if weak:
        teaching.append(f"年级共性薄弱学科为{'、'.join(weak)}，建议年级统一开展专项复习与错题讲评")
    if class_rows:
        lowest = min(class_rows, key=lambda x: x["avg_growth_index"])
        teaching.append(f"{lowest['class_name']}平均成长指数（{lowest['avg_growth_index']}分）居年级末位，建议重点帮扶")
    if not teaching:
        teaching.append("年级整体状态良好，可组织学科拓展与分层教学")

    return {
        "grade": grade,
        "student_count": len(students),
        "class_count": len(class_rows),
        "avg_growth_index": avg_index,
        "classes": class_rows,
        "subjects": subject_rows,
        "weak_subjects": weak,
        "paragraph": paragraph,
        "teaching_suggestions": teaching,
    }
