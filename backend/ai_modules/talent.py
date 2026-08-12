"""AI 综合素质·特长发现：综合音体美信素质、课外活动与获奖记录，
识别学生的优势特长方向并给出竞赛/社团等发展建议。"""

from collections import defaultdict

from backend.models import Student
from backend.ai_modules.common import load_all, _avg

_QUALITY_NAMES = {"音乐": "音乐", "体育": "体育", "美术": "美术", "信息技术": "信息技术"}

_LEVEL_WEIGHT = {"校级": 1, "区级": 2, "市级": 3, "省级": 4}


def _quality_avg(data):
    acc = defaultdict(list)
    for q in data.get("quality") or []:
        acc[q.subject].append(q.score)
    return {subj: _avg(vals) for subj, vals in acc.items()}


def _activity_hours(data):
    acc = defaultdict(float)
    for a in data.get("activities") or []:
        if a.type and a.hours:
            acc[a.type] += a.hours
    return acc


def _award_info(data):
    awards = sorted(data.get("awards") or [], key=lambda a: (_LEVEL_WEIGHT.get(a.level, 0), a.date), reverse=True)
    return awards


def talent_analysis(db, student_id):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    data = load_all(db, [student_id]).get(student_id) or {}
    quality = _quality_avg(data)
    hours = _activity_hours(data)
    awards = _award_info(data)

    talents = []
    score_lines = []

    # 体育特长
    sports_score = quality.get("体育")
    sports_hours = hours.get("体育", 0)
    sports_award = any("体育" in (a.title or "") or a.level for a in awards if "体育" in (a.title or ""))
    if (sports_score is not None and sports_score >= 75) or sports_hours >= 14:
        talents.append({
            "direction": "体育",
            "level": "明显" if sports_hours >= 21 or (sports_score or 0) >= 80 else "初步",
            "basis": f"体育素质{sports_score if sports_score is not None else '—'}分、体育类活动累计{sports_hours:.0f}小时"
                     + ("，且已有体育类获奖" if sports_award else ""),
            "suggestions": ["参加校运动会/区级田径类比赛", "加入校级体育队或田径社团", "保持每周3次以上专项训练"],
        })

    # 艺术特长（音乐/美术）
    art_score = max(quality.get("音乐") or 0, quality.get("美术") or 0)
    art_awards = [a for a in awards if any(k in (a.title or "") for k in ("绘画", "美术", "书法", "音乐", "合唱", "艺术", "器乐", "钢琴", "舞蹈"))]
    if art_score >= 75 or art_awards:
        talents.append({
            "direction": "艺术",
            "level": "明显" if (art_score or 0) >= 80 or any(_LEVEL_WEIGHT.get(a.level, 0) >= 3 for a in art_awards) else "初步",
            "basis": f"艺术类素质最高{art_score}分" + (f"，{art_awards[0].level}·{art_awards[0].title}" if art_awards else ""),
            "suggestions": ["参加校内艺术节或书画展", "报名区市级艺术类展演", "可选择艺术社团担任主创角色"],
        })

    # 信息科技特长
    it_score = quality.get("信息技术")
    tech_hours = hours.get("社团", 0) * 0.5 + hours.get("实践", 0) * 0.5
    tech_awards = [a for a in awards if any(k in (a.title or "") for k in ("编程", "科技", "信息", "机器人", "创新"))]
    if (it_score is not None and it_score >= 75) or tech_awards:
        talents.append({
            "direction": "信息科技",
            "level": "明显" if (it_score or 0) >= 80 or tech_awards else "初步",
            "basis": f"信息技术素质{it_score if it_score is not None else '—'}分"
                     + (f"，{tech_awards[0].level}·{tech_awards[0].title}" if tech_awards else ""),
            "suggestions": ["参加信息学奥赛或机器人竞赛", "加入科创社团并担任项目角色", "学习一门编程语言并完成小项目"],
        })

    # 实践创新
    practice_hours = hours.get("实践", 0)
    if practice_hours >= 11 or (quality.get("信息技术") or 0) >= 75:
        talents.append({
            "direction": "实践创新",
            "level": "明显" if practice_hours >= 15 else "初步",
            "basis": f"实践活动累计{practice_hours:.0f}小时",
            "suggestions": ["参与研究性学习课题", "参加科技创新大赛", "承担小组项目中的动手环节"],
        })

    # 人文阅读
    reading_hours = hours.get("阅读", 0)
    read_awards = [a for a in awards if any(k in (a.title or "") for k in ("作文", "征文", "阅读", "演讲"))]
    if reading_hours >= 5 or read_awards:
        talents.append({
            "direction": "人文表达",
            "level": "明显" if reading_hours >= 10 or read_awards else "初步",
            "basis": f"阅读类活动累计{reading_hours:.0f}小时" + (f"，{read_awards[0].level}·{read_awards[0].title}" if read_awards else ""),
            "suggestions": ["参加作文/征文比赛", "担任校刊或广播站编辑", "参加演讲与辩论类社团"],
        })

    for subj in ("音乐", "体育", "美术", "信息技术"):
        v = quality.get(subj)
        if v is not None:
            score_lines.append(f"{_QUALITY_NAMES[subj]}素质{v}分")

    summary = (
        f"{student.name}的综合素质画像：{('；'.join(score_lines) + '。') if score_lines else ''}"
        + (f"已识别{'、'.join(t['direction'] for t in talents)}等{'个' if len(talents)>1 else ''}特长方向。"
           if talents else "暂未识别出明显特长方向，建议多尝试社团与课外活动。")
    )

    summary_polished = None
    try:
        from backend.ai_modules.llm_polish import polish
        if talents:
            summary_polished = polish(summary, tone="鼓励发掘、有针对性", max_tokens=250)
    except Exception:  # noqa: BLE001
        summary_polished = None

    return {
        "student_id": student_id,
        "name": student.name,
        "class_name": student.class_name,
        "quality": quality,
        "activity_hours": {k: round(v, 1) for k, v in hours.items()},
        "awards": [{"level": a.level, "title": a.title, "date": str(a.date)} for a in awards[:5]],
        "talents": talents,
        "summary": summary,
        "summary_polished": summary_polished,
    }
