"""AI 成长档案叙事：把成长指数、五维画像、获奖与活动等数据转成可读的成长故事。

面向学生/家长/教师阅读，强调"可解释、可读、有温度"，与学习报告互补。
"""

from backend.models import Student
from backend.ai_modules.common import load_all, load_awards, load_quality, load_activities, _avg
from backend.ai_modules.analysis import compute_growth_profile

_ASPECT_NAMES = {
    "学习能力": ("学业功底扎实，听课与练习转化率高", "学业上仍有提升空间，建议夯实基础后再求突破"),
    "心理健康": ("心态阳光稳定，面对测评能保持冷静", "近期情绪状态需要更多关照，学会给压力留出口"),
    "体育健康": ("体能状态出色，坚持锻炼让学习更有后劲", "运动量略有不足，身体是高效学习的本钱"),
    "实践能力": ("动手能力强，能把知识用到真实场景中", "实践参与偏少，建议多争取动手与观察的机会"),
    "兴趣发展": ("课余兴趣丰富，综合素养在持续生长", "课余兴趣较单一，试着发展一两个真正热爱的方向"),
}


def growth_narrative(db, student_id):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    profile = compute_growth_profile(student_id, db) or {}
    data = load_all(db, [student_id]).get(student_id) or {}
    aspects = profile.get("aspects", {})
    gi = round(profile.get("growth_index", 0), 1)

    paragraphs = []
    if gi >= 85:
        opening = f"{student.name}正处在一个稳健向上的成长通道里"
    elif gi >= 70:
        opening = f"{student.name}的整体发展较为均衡，正处于稳步积累的黄金阶段"
    elif gi >= 55:
        opening = f"{student.name}的成长道路上还有不少可以打磨的空间，潜力远未兑现"
    else:
        opening = f"{student.name}目前正面临一段需要更多帮助的时期，但只要方向对了，进步会来得很快"
    paragraphs.append(
        f"{opening}：综合成长指数 {gi} 分。过去一段时间，学习、心理、体育、实践与兴趣五条线交织，"
        f"构成了他/她独特的成长轨迹。"
    )

    for name, (good, warn) in _ASPECT_NAMES.items():
        val = aspects.get(name)
        if val is None:
            continue
        if val >= 80:
            paragraphs.append(f"在「{name}」上，{good}（指数 {val} 分）。")
        elif val < 60:
            paragraphs.append(f"在「{name}」上，{warn}（指数 {val} 分）。")
        else:
            paragraphs.append(f"在「{name}」上表现中规中矩（指数 {val} 分），上升空间依然充足。")

    awards = data.get("awards") or []
    activities = data.get("activities") or []
    if awards:
        levels = "、".join(f"{a.level}·{a.title}" for a in awards[:3])
        paragraphs.append(f"他/她已获得{levels}等荣誉，这些点滴积累都是成长路上清晰的注脚。")
    else:
        paragraphs.append("虽然尚未留下获奖记录，但每一次尝试本身都值得被记录。")

    sem_hours = {}
    for a in activities:
        if a.type and a.hours:
            sem_hours[a.type] = sem_hours.get(a.type, 0) + a.hours
    if sem_hours:
        top_type = max(sem_hours, key=sem_hours.get)
        paragraphs.append(f"在课外活动上，{top_type}类投入最多（累计 {sem_hours[top_type]:.0f} 小时），看得出他/她的精力所向。")

    strengths = profile.get("strengths") or []
    if strengths:
        paragraphs.append(f"他/她的优势学科集中在{'、'.join(strengths)}，这是可以持续放大并发光的支点。")
    if profile.get("weakness"):
        weakness_text = "、".join(profile["weakness"]).replace("%", "％")
        paragraphs.append(f"相对而言，{weakness_text}值得在下个阶段投入更多耐心。")

    stage = "下个阶段"
    if gi >= 80:
        stage_sentence = "建议保持势头，向更高目标发起挑战，同时把成功的经验沉淀成可复制的方法。"
    elif gi >= 60:
        stage_sentence = "建议稳住优势科目，集中力量优先补齐最薄弱的1-2门，让短板不再拖后腿。"
    else:
        stage_sentence = "建议先从作息、运动和情绪入手稳住状态，再逐步恢复学习节奏，不必急于求成。"
    paragraphs.append(f"{stage}的小目标很简单：{stage_sentence}")

    return {
        "student_id": student_id,
        "name": student.name,
        "class_name": student.class_name,
        "growth_index": gi,
        "paragraphs": paragraphs,
        "aspects": aspects,
        "strengths": strengths,
        "weakness": profile.get("weakness", []),
        "suggestion": stage_sentence,
    }
