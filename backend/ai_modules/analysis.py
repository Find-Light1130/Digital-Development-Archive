"""
AI 分析模块
计算成长指数、知识掌握度、预警检测、个性化建议
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from collections import defaultdict
import random
from backend.models import Student, Score, EmotionLog, Activity, Attendance

GROWTH_WEIGHTS = {
    "体育健康": 0.30,
    "心理健康": 0.25,
    "学习能力": 0.25,
    "实践能力": 0.10,
    "兴趣发展": 0.10,
}


def _batch_load(student_ids, db: Session):
    key = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}
    scores = defaultdict(list)
    for r in db.execute(
        select(Score.student_id, Score.subject, Score.score, Score.max_score,
               Score.date, Score.semester, Score.exam_type)
        .where(Score.student_id.in_(student_ids))
    ):
        scores[r.student_id].append(r)
    emotions = defaultdict(list)
    for r in db.execute(
        select(EmotionLog.student_id, EmotionLog.date, EmotionLog.emotion_level)
        .where(EmotionLog.student_id.in_(student_ids))
    ):
        emotions[r.student_id].append(r)
    activities = defaultdict(list)
    for r in db.execute(
        select(Activity.student_id, Activity.type, Activity.hours)
        .where(Activity.student_id.in_(student_ids))
    ):
        activities[r.student_id].append(r)
    attendance = defaultdict(list)
    for r in db.execute(
        select(Attendance.student_id, Attendance.present)
        .where(Attendance.student_id.in_(student_ids))
    ):
        attendance[r.student_id].append(r)
    return key, scores, emotions, activities, attendance


def _pct(scores):
    return [s.score / s.max_score * 100 if (s.score is not None and s.max_score) else 50 for s in scores]


def _recent_mastery(student_scores):
    subject_scores = {}
    for s in student_scores:
        subject_scores.setdefault(s.subject, []).append(s)
    mastery = {}
    for subj, vals in subject_scores.items():
        ordered = sorted(vals, key=lambda x: x.date)
        recent = ordered[-3:] if len(ordered) >= 3 else ordered
        pcts = _pct(recent)
        mastery[subj] = round(sum(pcts) / len(pcts), 1)
    return mastery


def _overall_trend(vals):
    """对整段成绩序列做线性回归，得到每次考试的平均百分比变化量（整体趋势而非局部）。"""
    n = len(vals)
    if n < 4:
        return "stable"
    x_mean = (n - 1) / 2
    y_mean = sum(vals) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    if slope > 1.0:
        return "up"
    if slope < -1.0:
        return "down"
    return "stable"


def _is_monotonic_decreasing(pcts):
    for i in range(1, len(pcts)):
        if pcts[i] > pcts[i - 1]:
            return False
    return True


def _recent_semester_monotonic_decline(subject_semester_pcts, subj):
    """最近一个学期所有考试单调递减时返回该学期名，否则返回 None。"""
    sem_dict = subject_semester_pcts.get(subj, {})
    if not sem_dict:
        return None
    recent_sem = list(sem_dict.keys())[-1]
    pcts = sem_dict[recent_sem]
    if len(pcts) >= 3 and _is_monotonic_decreasing(pcts):
        return recent_sem
    return None


def _build_aspects(student, student_scores, student_emotions, student_activities):
    """计算五维画像与成长指数（唯一公式来源）。"""
    mastery = _recent_mastery(student_scores)
    learning = round(sum(mastery.values()) / len(mastery), 1) if mastery else 60

    if student_emotions:
        recent_emo = sorted(student_emotions, key=lambda x: x.date, reverse=True)[:30]
        levels = [e.emotion_level for e in recent_emo if e.emotion_level is not None]
        avg_e = sum(levels) / len(levels) if levels else 3
        mental = round(max(0, min(100, (avg_e - 1) / 2 * 70 + 30)), 1)
    else:
        mental = 75

    sports_hours = sum(a.hours for a in student_activities if a.type == "体育" and a.hours is not None)
    physical = round(min(100, sports_hours / 14 * 100), 1)

    practice_hours = sum(a.hours for a in student_activities if a.type == "实践" and a.hours is not None)
    practice = round(min(100, practice_hours / 11 * 100), 1)

    clubs = [a for a in student_activities if a.type == "社团"]
    reading = [a for a in student_activities if a.type == "阅读"]
    interest = round(min(100, len(clubs) * 10 + len(reading) * 5 + sum(a.hours for a in clubs if a.hours is not None) * 5), 1)

    aspects = {"学习能力": learning, "心理健康": mental, "体育健康": physical, "实践能力": practice, "兴趣发展": interest}

    growth_index = round(
        learning * GROWTH_WEIGHTS["学习能力"] + mental * GROWTH_WEIGHTS["心理健康"]
        + physical * GROWTH_WEIGHTS["体育健康"] + practice * GROWTH_WEIGHTS["实践能力"]
        + interest * GROWTH_WEIGHTS["兴趣发展"], 1,
    )
    return aspects, growth_index


def build_profile(student, student_scores, student_emotions, student_activities, student_attendance):
    aspects, growth_index = _build_aspects(student, student_scores, student_emotions, student_activities)

    mastery = _recent_mastery(student_scores)
    sorted_subjects = sorted(mastery.items(), key=lambda x: x[1], reverse=True)
    strengths = [s[0] for s in sorted_subjects[:2]] if sorted_subjects else []
    weakness = [f"{s[0]}-{round(s[1], 1)}%" for s in sorted_subjects[-2:]] if len(sorted_subjects) >= 2 else []

    warnings = _detect_warnings(student_scores, student_emotions, student_attendance)
    suggestions = _dynamic_suggestions(mastery, aspects, student_scores, student_emotions, student_activities, student_attendance, warnings)

    date_sorted = sorted(student_scores, key=lambda x: x.date) if student_scores else []
    trend = []
    if len(date_sorted) >= 3:
        chunk = max(1, len(date_sorted) // 5)
        for i in range(0, len(date_sorted), chunk):
            batch = date_sorted[i:i + chunk]
            trend.append(round(sum((s.score / s.max_score * 100) if (s.score is not None and s.max_score) else 50 for s in batch) / len(batch), 1))
        if len(trend) > 6:
            trend = trend[-6:]

    return {
        "growth_index": growth_index, "aspects": aspects,
        "strengths": strengths, "weakness": weakness,
        "suggestions": suggestions, "warnings": warnings, "trend": trend,
    }


def _detect_warnings(student_scores, student_emotions, student_attendance):
    warnings = []

    student_scores = sorted(student_scores, key=lambda x: x.date)
    subject_sem_scores = defaultdict(lambda: defaultdict(list))
    subject_all_pcts = defaultdict(list)
    for s in student_scores:
        if s.score is not None and s.max_score:
            pct = s.score / s.max_score * 100
            subject_sem_scores[s.subject][s.semester].append((s.date, pct))
            subject_all_pcts[s.subject].append((s.date, pct))

    for subj, sem_dict in subject_sem_scores.items():
        recent_sem = list(sem_dict.keys())[-1] if sem_dict else None
        if recent_sem:
            recent_pcts = [pct for _, pct in sem_dict[recent_sem]]
            if len(recent_pcts) >= 3 and _is_monotonic_decreasing(recent_pcts):
                warnings.append(f"{subj}本学期成绩持续下滑，需关注")
                continue
        all_sorted = [pct for _, pct in sorted(subject_all_pcts[subj], key=lambda x: x[0])]
        if _overall_trend(all_sorted) == "down":
            warnings.append(f"{subj}成绩整体呈下滑趋势，建议关注")

    emo_list = sorted(student_emotions, key=lambda x: x.date, reverse=True)
    if len(emo_list) >= 3:
        recent_lev = [e.emotion_level for e in emo_list[:3] if e.emotion_level is not None]
        if len(recent_lev) >= 3 and all(v <= 1 for v in recent_lev):
            warnings.append("近期情绪持续低落，建议心理辅导")

    if student_attendance:
        total = len(student_attendance)
        present = sum(1 for a in student_attendance if a.present)
        if present / total < 0.90:
            warnings.append(f"出勤率仅{present / total:.0%}，低于正常水平")

    if len(emo_list) >= 7:
        recent = [e.emotion_level for e in emo_list[:7] if e.emotion_level is not None]
        if len(recent) >= 3 and max(recent) - min(recent) >= 2 and len(set(recent)) >= 3:
            warnings.append("近期情绪波动较大，建议关注")
    return warnings


def _pick(templates):
    return random.choice(templates)

def _dynamic_suggestions(mastery, aspects, student_scores, student_emotions, student_activities, student_attendance, warnings):
    suggestions = []

    sorted_scores = sorted(student_scores, key=lambda x: x.date) if student_scores else []
    subject_pcts = defaultdict(list)
    subject_semester_pcts = defaultdict(lambda: defaultdict(list))
    for s in sorted_scores:
        if s.score is not None and s.max_score:
            pct = s.score / s.max_score * 100
        else:
            pct = 50
        subject_pcts[s.subject].append(pct)
        subject_semester_pcts[s.subject][s.semester].append(pct)

    for subj, vals in sorted(subject_pcts.items()):
        decline_sem = _recent_semester_monotonic_decline(subject_semester_pcts, subj)
        t = _overall_trend(vals)
        if decline_sem:
            suggestions.append(_pick([
                f"{subj}本学期成绩持续下滑，建议整理近期错题本，每周回顾一次薄弱题型",
                f"{subj}本学期成绩持续下滑，建议及时与任课老师沟通，分析失分点后系统复习",
            ]))
        elif t == "down":
            suggestions.append(_pick([
                f"{subj}成绩整体呈下滑趋势，尝试调整学习方法，多向老师请教解题思路",
                f"{subj}近期表现不佳，建议拆解知识点逐个攻破，每天多花10分钟复习",
                f"{subj}整体有下滑，建议先回归课本基础概念，再逐步过渡到中等难度练习",
                f"{subj}需要加把劲，可以找一位学习伙伴互相督促、共同进步",
                f"{subj}整体下滑，建议每学完一章就做一次自测，及时查漏补缺",
                f"{subj}最近有些滑坡，别灰心，先把容易丢分的基础题稳稳拿住",
                f"{subj}成绩在往下走，建议把近两次测评的失分点列出来逐条攻克",
            ]))
        elif t == "up":
            suggestions.append(_pick([
                f"{subj}稳步提升，继续保持当前节奏，适当挑战更高难度题目",
                f"{subj}进步势头很好，建议总结有效方法并应用到其他科目",
                f"{subj}成绩上升明显，自信心是学习最好的加速器，再接再厉",
                f"{subj}提升显著，说明这段时间的努力没有白费，请继续保持这种状态",
                f"{subj}持续向好，建议把成功的经验整理成学习笔记，形成自己的方法论",
                f"{subj}表现越来越棒，可以尝试帮助同学解答问题，巩固自身理解",
                f"{subj}一路上扬的曲线很亮眼，试着为下一阶段定一个更高的目标",
                f"{subj}进步的每一步都算数，继续保持这种稳扎稳打的复习节奏",
            ]))

    if aspects["体育健康"] < 60:
        suggestions.append(_pick([
            "体育锻炼偏少，建议每周安排3次以上户外运动，哪怕从课间散步开始",
            "运动量不足会影响注意力和情绪，建议每天抽20分钟进行跳绳或跑步",
            "身体是学习的本钱，建议加入一项感兴趣的体育活动并坚持下去",
            "建议利用课间操和体育课的机会充分活动身体，不要总是待在教室里",
            "久坐不动容易疲劳，每隔45分钟站起来活动五分钟，效率反而更高",
            "周末可以约同学打打球或骑骑车，既锻炼身体又放松心情",
        ]))
    elif aspects["体育健康"] >= 80:
        suggestions.append(_pick([
            "体能状态优秀，规律的体育锻炼是高效学习的有力支撑",
            "体育表现突出，建议尝试一项团队运动，既锻炼身体也培养合作能力",
            "运动习惯保持得很好，可以挑战更高的运动目标或参加校级比赛",
            "身体素质和运动能力都很好，建议兼顾力量和有氧训练全面发展",
            "热爱运动是好习惯，注意运动前热身和运动后拉伸，避免受伤",
            "体能优势明显，可以考虑在运动会或体育节中一展身手",
        ]))

    if aspects["心理健康"] < 60:
        suggestions.append(_pick([
            "心理状态需要关注，建议主动与心理老师或信任的师长聊聊近况",
            "情绪低落时不要一个人扛着，写日记、听音乐或和朋友倾诉都是好办法",
            "近期心理压力偏大，尝试每天给自己10分钟的放松时间，做些喜欢的事",
            "深呼吸和正念冥想能有效缓解焦虑，每天花5分钟练习会有帮助",
            "如果感觉压力太大，不妨暂时放下书本出门走走，换换心情再继续",
            '可以和好朋友约定一个"吐槽时间"，定期交流释放心理压力',
        ]))
    elif aspects["心理健康"] >= 80:
        suggestions.append(_pick([
            "心理状态阳光积极，这种心态是战胜学习困难的重要武器",
            "情绪管理能力出色，建议多用自己的正能量影响身边的同学",
            "心理健康状况很好，保持乐观心态会让学习效率事半功倍",
            "乐观开朗是你宝贵的财富，这种积极心态会感染身边的人",
            "心理素质过硬，面对测评和挑战时能保持冷静，这是很大的优势",
            "你的情绪调节能力很强，可以试着在班级中担任心理委员等角色",
        ]))

    if aspects["实践能力"] < 30:
        suggestions.append(_pick([
            "实践活动参与较少，建议抓住学校实验课和社会实践的机会多动手",
            "动手能力同样重要，尝试参加一次科技创新或社区服务活动",
            "纸上得来终觉浅，建议争取动手实验或实地考察的机会来加深理解",
            "可以尝试在家做一些简单的科学小实验，培养动手兴趣",
            "参加一次志愿者活动或社区服务，既能实践又能增长见识",
            '建议多参与小组合作项目中的实操环节，不要只做"旁观者"',
        ]))
    elif aspects["实践能力"] >= 70:
        suggestions.append(_pick([
            "实践能力突出，建议参加科技创新比赛或研究性学习项目",
            "动手能力强是你的优势，可以在小组项目中主动承担动手环节",
            "实践能力优秀，可以尝试将理论知识与实际应用结合起来",
            "你有很强的动手能力，可以考虑参加机器人、编程等实践类竞赛",
            "理论和实践结合得很好，这种能力在未来的学习中会越来越重要",
            "动手实验能力强，建议在理科学习中多通过实验来验证和深化理解",
        ]))

    if aspects["兴趣发展"] < 30:
        suggestions.append(_pick([
            "课余兴趣较单一，建议尝试一项社团活动或培养阅读习惯",
            "兴趣是最好的老师，试着在课外发展1-2项真正热爱的爱好",
            "除了课本知识，探索一项兴趣爱好能让学习生活更加充实",
            "可以从学校现有的社团中选择一个感兴趣的方向尝试参与",
            "建议每周安排固定的课外阅读时间，先从感兴趣的书籍开始",
            "多尝试不同领域的活动，找到真正热爱的事情会让学习更有动力",
        ]))
    elif aspects["兴趣发展"] >= 70:
        suggestions.append(_pick([
            "兴趣广泛且深入，这是综合素养的重要体现，建议选择一个方向深耕",
            "多才多艺是难得优势，可以考虑参加相关比赛或展示活动",
            "兴趣爱好丰富，尝试将兴趣与学科学习结合起来，会更有动力",
            "你在课余兴趣方面表现活跃，可以尝试社团负责人或组织者的角色",
            "广泛的兴趣爱好有助于培养跨学科思维，建议继续保持并适当取舍",
            "如果能将一两项兴趣发展为特长，对未来的升学和成长都有帮助",
        ]))

    if mastery:
        low = sorted(mastery.items(), key=lambda x: x[1])[:2]
        for sub, v in low:
            if v < 65:
                suggestions.append(_pick([
                    f"{sub}基础偏弱（掌握率{v:.0f}%），建议每天分配15分钟巩固该科基础概念",
                    f"{sub}掌握率仅{v:.0f}%，可以从课本例题入手，逐步建立知识框架",
                    f"{sub}是薄弱科目，建议整理该科思维导图，理清知识点之间的关联",
                    f"{sub}掌握率偏低（{v:.0f}%），建议先抓核心概念再做针对性练习",
                    f"{sub}需要重点突破（{v:.0f}%），建议利用周末集中攻克该科目的薄弱章节",
                    f"{sub}水平有待提升（{v:.0f}%），可参考网课或教辅资料辅助理解",
                ]))

    for w in warnings:
        if "波动" in w:
            suggestions.append(_pick([
                "情绪波动时尝试通过运动、绘画或写日记来释放压力",
                "建议学习简单的正念呼吸练习，在情绪起伏时帮助自己平静下来",
                "情绪起伏时不妨暂时停下来，做几次深呼吸再继续学习",
                "建立稳定的作息有助于情绪稳定，尽量保持每天作息规律",
            ]))
        elif "出勤" in w:
            suggestions.append(_pick([
                "建议制定固定的作息时间表，保证充足的睡眠和按时到校",
                "连续缺勤会影响学习节奏，建议与班主任沟通制定补课计划",
                "按时到校是学习的第一步，建议设置固定的起床和就寝闹钟",
                "缺勤落下的课程一定要及时补上，可以找同学借笔记抄写",
            ]))
        elif "下滑" in w:
            suggestions.append(_pick([
                "成绩下滑不必焦虑，找出薄弱环节后逐个击破，进步空间往往更大",
                "遇到瓶颈期是正常的，建议与任课老师沟通，调整复习策略",
                "成绩波动时先别着急，仔细分析试卷上的失分点更有意义",
                "成绩下滑可能是学习方法需要调整了，试试换一种复习方式",
            ]))

    if aspects["学习能力"] >= 80 and not any("下滑" in s for s in suggestions):
        suggestions.append(_pick([
            "学习能力出色，建议挑战学科竞赛或提前预习更高年级内容",
            "学有余力的情况下，可以尝试阅读学科拓展书籍，拓宽知识面",
            "学习能力强是最大的优势，建议设定一个更高的目标来挑战自己",
            "你的学习效率很高，可以尝试担任学科课代表或帮助同学答疑",
            "学习能力突出，建议制定更有挑战性的学习计划，不要满足于现状",
            "可以开始培养自主学习的习惯，尝试自己制定学习计划和目标",
        ]))

    if not suggestions:
        suggestions.append(_pick([
            "综合表现均衡稳定，建议保持规律的作息和良好的学习习惯",
            "各方面发展良好，继续脚踏实地，稳中求进",
            "整体状态不错，建议每周设定一个小目标，让进步看得见",
            "各科发展比较均衡，可以尝试在自己感兴趣的科目上深入拓展",
            "当前状态平稳，是时候给自己定一个阶段性目标来激发潜力了",
            "保持良好的学习节奏，注意劳逸结合，效率往往比时间更重要",
        ]))

    return suggestions[:6]


def compute_growth_profile(student_id: int, db: Session):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    student_scores = db.query(Score).filter(Score.student_id == student_id).all()
    student_emotions = db.query(EmotionLog).filter(EmotionLog.student_id == student_id).all()
    student_activities = db.query(Activity).filter(Activity.student_id == student_id).all()
    student_attendance = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    return build_profile(student, student_scores, student_emotions, student_activities, student_attendance)


def batch_growth_profiles(student_ids: list, db: Session, light: bool = False):
    key, scores, emotions, activities, attendance = _batch_load(student_ids, db)
    result = {}
    for sid in student_ids:
        student = key.get(sid)
        if not student:
            continue
        if light:
            aspects, growth_index = _build_aspects(
                student, scores.get(sid, []), emotions.get(sid, []), activities.get(sid, []),
            )
            result[sid] = {"growth_index": growth_index, "aspects": aspects}
        else:
            result[sid] = build_profile(
                student, scores.get(sid, []), emotions.get(sid, []),
                activities.get(sid, []), attendance.get(sid, []),
            )
    return result
