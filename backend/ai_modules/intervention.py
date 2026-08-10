"""AI 预警·干预闭环：多信号加权分级预警 → 自动生成干预方案 → 效果对比追踪。

预警不再是"一张列表"，而是带严重程度分级、可生成干预方案、可追踪效果的完整闭环。
"""

from collections import defaultdict

from backend.ai_modules.common import load_all, subject_mastery, subject_trends
from backend.ai_modules.analysis import compute_growth_profile

# 各预警信号权重（满分合计可超 100，最终封顶 100）
_W = {
    "score_drop": 30,
    "overall_down": 25,
    "emotion_low": 30,
    "emotion_volatile": 15,
    "attendance": 25,
    "low_mastery": 20,
}


def _detect_warnings(student, scores, emotions, attendance):
    warnings = []
    mastery = subject_mastery(scores)
    trends = subject_trends(scores)

    for subj, t in sorted(trends.items()):
        if t.get("recent_sem_monotonic_decline"):
            warnings.append({
                "type": "score_drop", "subject": subj,
                "semester": t["recent_sem_monotonic_decline"],
                "text": f"{subj}本学期成绩持续下滑，需关注",
                "score": _W["score_drop"],
            })
        elif t.get("trend") == "down":
            warnings.append({
                "type": "overall_down", "subject": subj,
                "text": f"{subj}成绩整体呈下滑趋势，建议关注",
                "score": _W["overall_down"],
            })

    weak = sorted(mastery.items(), key=lambda kv: kv[1])[:2]
    for subj, v in weak:
        if v < 65:
            warnings.append({
                "type": "low_mastery", "subject": subj, "value": v,
                "text": f"{subj}基础偏弱（掌握率{v}%）",
                "score": _W["low_mastery"],
            })

    emo = sorted(emotions, key=lambda x: x.date, reverse=True)
    if len(emo) >= 3:
        recent = [e.emotion_level for e in emo[:3] if e.emotion_level is not None]
        if len(recent) >= 3 and all(v <= 1 for v in recent):
            warnings.append({
                "type": "emotion_low", "text": "近期情绪持续低落，建议心理辅导",
                "score": _W["emotion_low"],
            })
    if len(emo) >= 7:
        recent7 = [e.emotion_level for e in emo[:7] if e.emotion_level is not None]
        if len(recent7) >= 3 and max(recent7) - min(recent7) >= 2 and len(set(recent7)) >= 3:
            warnings.append({
                "type": "emotion_volatile", "text": "近期情绪波动较大，建议关注",
                "score": _W["emotion_volatile"],
            })

    if attendance:
        present = sum(1 for a in attendance if a.present)
        rate = present / len(attendance)
        if rate < 0.90:
            warnings.append({
                "type": "attendance", "rate": round(rate * 100, 1),
                "text": f"出勤率仅{rate:.0%}，低于正常水平",
                "score": _W["attendance"],
            })
    return warnings


def _compute_score(warnings):
    """按信号类别分组计分，避免同类信号（如多科下滑）简单堆叠。

    类别取最强信号分，跨类别叠加并给出小幅"多信号"加成，防止风险分虚高。
    """
    decl_scores = [w["score"] for w in warnings if w["type"] in ("score_drop", "overall_down")]
    decl_max = max(decl_scores) if decl_scores else 0
    decl_subjects = {w.get("subject") for w in warnings if w.get("subject")}

    mastery = [w for w in warnings if w["type"] == "low_mastery"]
    emotion_low = any(w["type"] == "emotion_low" for w in warnings)
    emotion_vol = any(w["type"] == "emotion_volatile" for w in warnings)
    attendance = any(w["type"] == "attendance" for w in warnings)

    score = 0
    if decl_max:
        score += decl_max
        if len(decl_subjects) >= 3:
            score += 10
    if mastery:
        score += 20
    if emotion_low:
        score += 30
    elif emotion_vol:
        score += 15
    if emotion_low and emotion_vol:
        score += 5
    if attendance:
        score += 25
    return min(100, score)


def assess_risks(db, student_ids):
    """批量评估预警风险，返回按风险分降序的学生列表（red/yellow/green 三级）。"""
    data = load_all(db, student_ids)
    result = []
    for sid in student_ids:
        d = data.get(sid)
        if not d or not d["student"]:
            continue
        student = d["student"]
        warnings = _detect_warnings(student, d["scores"], d["emotions"], d["attendance"])
        total = _compute_score(warnings)
        level = "red" if total >= 75 else ("yellow" if total >= 55 else "green")
        result.append({
            "student_id": sid,
            "name": student.name,
            "class_name": student.class_name,
            "grade": student.grade,
            "risk_level": level,
            "risk_score": total,
            "warnings": warnings,
        })
    result.sort(key=lambda r: -r["risk_score"])
    return result


def student_risk(db, student_id):
    result = assess_risks(db, [student_id])
    return result[0] if result else None


def build_intervention_plan(warnings):
    """根据预警信号自动生成干预方案（含目标与跟进节点）。"""
    if not warnings:
        return None
    primary = max(warnings, key=lambda w: w["score"])
    ptype = primary["type"]
    subj = primary.get("subject", "")

    templates = {
        "score_drop": (
            "成绩下滑干预",
            f"针对{subj}本学期成绩持续下滑：由任课老师与学生一对一面谈，定位失分点；"
            "整理近三次考试错题建立错题本，每周五复盘一次；两周后安排一次随堂小测检验效果。",
            ["第1周：完成错题整理并面谈", "第2周：每周复盘2次，观察回升", "第3周：随堂小测，对比干预前后"],
        ),
        "overall_down": (
            "学习下滑干预",
            f"针对{subj}成绩整体下滑趋势：调整学习节奏，回归课本基础概念，每天安排10分钟专项复习；"
            "与家长沟通作息，保证睡眠；一个月后评估趋势是否反转。",
            ["第1周：制定并执行每日复习计划", "第2周：与任课老师沟通一次", "第4周：评估整体趋势"],
        ),
        "emotion_low": (
            "心理疏导干预",
            "针对近期情绪持续低落：安排心理老师一对一谈话，了解压力来源；"
            "建议每日进行正念呼吸或运动20分钟；连续两周跟踪情绪打卡情况。",
            ["第1周：心理老师面谈并制定疏导计划", "第2周：跟踪情绪打卡与睡眠情况", "第3周：复评情绪状态"],
        ),
        "emotion_volatile": (
            "情绪稳定干预",
            "针对近期情绪波动较大：建立稳定作息，减少熬夜；引导使用情绪日记记录触发事件；"
            "必要时由心理老师介入，持续观察两周。",
            ["第1周：记录情绪日记与作息", "第2周：评估波动是否缓解", "第3周：如未缓解升级心理干预"],
        ),
        "attendance": (
            "出勤改善干预",
            f"针对出勤率仅{primary.get('rate', 0)}%：与家长沟通原因，制定固定作息表；"
            "班主任每周跟进出勤情况，连续两周达标后结束干预。",
            ["第1周：家校沟通并约定作息", "第2周：跟踪出勤是否达标", "第4周：评估出勤率改善"],
        ),
        "low_mastery": (
            "基础补强干预",
            f"针对{subj}基础偏弱（掌握率{primary.get('value', 0)}%）：从课本例题和核心概念入手，"
            "每天固定15分钟专项训练，每周做一次自测，目标两周内掌握率提升5个百分点。",
            ["第1周：回归基础，完成核心概念梳理", "第2周：每日专项训练+自测", "第3周：复测掌握率"],
        ),
    }
    title, plan_text, milestones = templates[ptype]
    # 次要信号并入方案说明
    extra = [w for w in warnings if w is not primary]
    if extra:
        plan_text += " 同时关注：" + "；".join(w["text"] for w in extra[:2]) + "。"

    return {
        "category": {"score_drop": "成绩", "overall_down": "成绩", "low_mastery": "学业",
                     "emotion_low": "心理", "emotion_volatile": "心理", "attendance": "考勤"}[ptype],
        "type": ptype,
        "title": title,
        "plan_text": plan_text,
        "milestones": milestones,
        "target": primary["text"],
    }


def compute_effect(db, student_id, baseline_growth_index):
    """干预效果对比：干预创建时的成长指数 vs 当前成长指数。"""
    profile = compute_growth_profile(student_id, db)
    current = round(profile["growth_index"], 1) if profile else None
    delta = round(current - baseline_growth_index, 1) if current is not None and baseline_growth_index is not None else None
    return {
        "baseline": baseline_growth_index,
        "current": current,
        "delta": delta,
    }
