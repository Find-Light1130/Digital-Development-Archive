"""AI 教师问数（Copilot）：LLM 语义理解 + 精确数据事实块 + LLM 自然语言组织。

流程：
1. 意图/槽位理解：llm_understanding.understand_ask（LLM 输出 JSON）；模型不可用时降级 TF-IDF。
2. 权限收敛：llm_understanding.enforce_scope —— 模型提取/上下文继承的范围
   必须落在 user_scope 内，越权一律回落用户默认范围（修复越权漏洞）。
3. 数据事实块：fact_blocks 按意图从精确数据层聚合（掌握率/下滑/预警/考勤…）。
4. 回复生成：LLM 基于事实块生成自然语言答案（不再模板拼接）；不可用时回退事实文本。
"""

import json
import re

from backend.models import Student
from backend.ai_modules import llm, fact_blocks, llm_understanding
from backend.ai_modules.thinking import StageTracker

_CLASS_RE = re.compile(r"[初高][一二三]\d+班")
_GRADE_RE = re.compile(r"初[一二三]年级")


def _sanitize_query(query, class_name=None, grade=None):
    """把用户问题里出现的班级/年级词替换为实际生效范围，防止 LLM 复述越权范围。"""
    if not class_name and not grade:
        return query
    q = query
    q = _CLASS_RE.sub(class_name or "", q)
    q = _GRADE_RE.sub(grade or "", q)
    return q

_ANSWER_SYSTEM = (
    "你是校园学情数据问答助手。请根据下方提供的『事实数据』用自然、清晰的中文回答用户问题。"
    "只能引用事实数据里的内容，不要编造或推断任何数字与名单，回答控制在3句话以内，简洁友好。"
    "如果用户问题里提到的班级/年级与事实数据中的范围不一致，一律以事实数据中的范围为准，不要提及问题中的错误范围。"
)

_CHAT_SYSTEM = (
    "你是校园学情数据问答助手，只回答与班级/年级成绩、考勤、素质、获奖、考试安排等校内数据相关的问题；"
    "课内知识或无关话题，礼貌告知无法回答并引导到数据类问题，回答简洁。"
)

_HANDLERS = {
    "mastery": lambda db, st, subject=None: fact_blocks.mastery_facts(db, st, subject),
    "declining": lambda db, st, subject=None: fact_blocks.declining_facts(db, st, subject),
    "warnings": lambda db, st, subject=None: fact_blocks.warnings_facts(db, st),
    "extremes": lambda db, st, subject=None: fact_blocks.extremes_facts(db, st, subject),
    "count": lambda db, st, subject=None: fact_blocks.count_facts(db, st),
    "attendance": lambda db, st, subject=None: fact_blocks.attendance_facts(db, st),
    "emotion": lambda db, st, subject=None: fact_blocks.emotion_facts(db, st),
    "quality": lambda db, st, subject=None: fact_blocks.quality_facts(db, st, subject),
    "activity": lambda db, st, subject=None: fact_blocks.activity_facts(db, st),
    "award": lambda db, st, subject=None: fact_blocks.award_facts(db, st),
    "exam_plan": lambda db, st, subject=None: fact_blocks.exam_facts(db, st),
    "growth_index": lambda db, st, subject=None: fact_blocks.growth_facts(db, st),
    "trend": lambda db, st, subject=None: fact_blocks.trend_facts(db, st, subject),
    "list": lambda db, st, subject=None: fact_blocks.list_facts(db, st),
}

# 闲聊意图：LLM 直接生成（不再使用模板列表）
_CHAT_INTENTS = {"greet", "thanks", "bye", "help", "chat"}


def _students_for(db, class_name, grade):
    q = db.query(Student).order_by(Student.id)
    if class_name:
        return q.filter(Student.class_name == class_name).all()
    if grade:
        return q.filter(Student.grade == grade).all()
    return q.all()


def _classify_students(students):
    if not students:
        return {"class_name": None, "grade": None}
    return {"class_name": students[0].class_name, "grade": students[0].grade}


def _build_llm_answer(query, facts_text, intent, parsed, data, class_name=None, grade=None):
    """LLM 基于事实块生成自然语言答案；模型不可用时直接返回事实文本。"""
    if not llm.is_available():
        return facts_text
    actual_scope = class_name or grade or (data or {}).get("scope") or "当前范围"
    safe_query = _sanitize_query(query, class_name, grade)
    user = (
        f"用户问题：{safe_query}\n\n"
        f"实际统计范围：{actual_scope}\n"
        f"事实数据：\n{facts_text}\n\n"
        "请用自然中文回答用户的问题（以实际统计范围与事实数据为准）。"
    )
    return llm.generate(user, system=_ANSWER_SYSTEM, max_tokens=200, temperature=0.4)


def _chat_answer_llm(query):
    if not llm.is_available():
        return _chat_fallback(query)
    return llm.generate(query, system=_CHAT_SYSTEM, max_tokens=120, temperature=0.7)


def _chat_fallback(q):
    """模型不可用时的闲聊兜底（保留原有文案）。"""
    from random import choice
    if "你好" in q or "hi" in q.lower() or "hello" in q.lower():
        return ("你好，我是智能AI助手，可以帮你查班级/年级的成绩、考勤、素质、获奖、考试安排等。"
                "试试：初一1班数学掌握率")
    if "谢谢" in q or "感谢" in q:
        return choice(["不客气，随时问我。", "能帮到你就好，还有想问的尽管说。"])
    if "再见" in q or "拜拜" in q or "晚安" in q:
        return choice(["再见，有需要再问我。", "好的，随时欢迎回来。"])
    if "帮助" in q or "help" in q.lower() or "能做什么" in q:
        return ("我是学情数据 AI 助手，可以帮你查：成绩掌握率/下滑/预警/最高最低/人数、考勤出勤率、"
                "情绪风险、音体美信素质、活动时长、获奖情况、考试规划、成长指数、成绩趋势。"
                "例如「初一1班数学掌握率」「本班谁在掉队」。")
    return ("我是学情数据智能AI助手，专注回答班级/年级的成绩、考勤、素质、获奖、考试安排等校内数据问题；"
            "课内知识或无关话题，请与老师或同学交流吧～")


def answer_query(db, user, query, context=None):
    """处理问数。context: 上一轮会话摘要（class_name/grade/subject/intent）或 None。"""
    q = (query or "").strip()
    if not q:
        return {"query": q, "intent": "unknown", "answer": "请输入问题。", "data": None}

    tracker = StageTracker()

    # 1. LLM 语义理解（意图 + 槽位）
    tracker.begin("searching")
    parsed = llm_understanding.understand_ask(q)
    intent = parsed["intent"]

    # 2. 权限收敛（越权回落用户默认范围）
    class_name, grade = llm_understanding.enforce_scope(user, parsed, context)
    subject = parsed.get("subject")
    if not subject and context:
        subject = context.get("subject")
    tracker.end("searching")

    # 闲聊意图
    if intent in _CHAT_INTENTS:
        return {
            "query": q, "intent": intent, "subject": subject,
            "class_name": class_name, "grade": grade,
            "answer": _chat_answer_llm(q), "data": {"intent": intent},
            "confidence": parsed.get("confidence"),
            "stages": None,
        }

    # 3. 精确数据聚合
    tracker.begin("aggregating")
    students = _students_for(db, class_name, grade)
    if not students and (class_name or grade):
        label = class_name or grade
        return {
            "query": q, "intent": intent, "subject": subject,
            "class_name": class_name, "grade": grade,
            "answer": f"未找到{label}的学生。", "data": None,
            "confidence": parsed.get("confidence"), "stages": None,
        }
    if not students:
        return {
            "query": q, "intent": intent, "subject": subject,
            "class_name": class_name, "grade": grade,
            "answer": "我没有权限访问这个范围，或请明确说明班级/年级。", "data": None,
            "confidence": parsed.get("confidence"), "stages": None,
        }
    handler = _HANDLERS.get(intent)
    if not handler:
        answer = ("该功能暂未开放，试试成绩、考勤、素质、获奖或考试安排相关的问题。")
        return {"query": q, "intent": intent, "subject": subject,
                "class_name": class_name, "grade": grade,
                "answer": answer, "data": None, "confidence": parsed.get("confidence"),
                "stages": None}
    try:
        block = handler(db, students, subject)
    except Exception as e:  # noqa: BLE001
        return {"query": q, "intent": intent, "subject": subject,
                "class_name": class_name, "grade": grade,
                "answer": "查询失败，请稍后再试。", "data": None,
                "confidence": parsed.get("confidence"), "stages": None}
    facts_text, data = block["facts"], block["data"]
    tracker.end("aggregating")

    # 4. LLM 组织自然语言
    tracker.begin("generating")
    answer = _build_llm_answer(q, facts_text, intent, parsed, data,
                               class_name=class_name, grade=grade)
    tracker.end("generating")

    return {
        "query": q, "intent": intent, "subject": subject,
        "class_name": class_name, "grade": grade,
        "answer": answer, "data": data,
        "confidence": parsed.get("confidence"),
        "stages": {
            "searching": tracker._times.get("searching", {}).get("ms"),  # noqa: SLF001
            "aggregating": tracker._times.get("aggregating", {}).get("ms"),  # noqa: SLF001
            "generating": tracker._times.get("generating", {}).get("ms"),  # noqa: SLF001
        },
    }


# ---------------------------------------------------------------- SSE 流式

def answer_query_stream(db, user, query, context=None):
    """SSE 流式问数：逐阶段 yield (event_type, payload) 并流式输出答案 token。

    yield 顺序：stage(searching) -> stage(aggregating) -> stage(generating)
               -> token(...) ... -> done({...完整结果...})
    """
    q = (query or "").strip()
    tracker = StageTracker()
    if not q:
        yield tracker.error_event("请输入问题。")
        return

    tracker.begin("searching")
    yield "stage", tracker.stage_event("searching")
    parsed = llm_understanding.understand_ask(q)
    intent = parsed["intent"]
    class_name, grade = llm_understanding.enforce_scope(user, parsed, context)
    subject = parsed.get("subject")
    if not subject and context:
        subject = context.get("subject")
    tracker.end("searching")

    if intent in _CHAT_INTENTS:
        tracker.begin("generating")
        yield "stage", tracker.stage_event("generating")
        answer = _chat_answer_llm(q)
        tracker.end("generating")
        yield "done", tracker.result_event(
            query=q, intent=intent, subject=subject, class_name=class_name, grade=grade,
            answer=answer, data={"intent": intent}, confidence=parsed.get("confidence"),
        )
        return

    tracker.begin("aggregating")
    yield "stage", tracker.stage_event("aggregating")
    students = _students_for(db, class_name, grade)
    if not students:
        answer = (f"未找到{class_name or grade}的学生。"
                  if (class_name or grade) else "我没有权限访问这个范围，或请明确说明班级/年级。")
        tracker.end("aggregating")
        yield "done", tracker.result_event(
            query=q, intent=intent, subject=subject, class_name=class_name, grade=grade,
            answer=answer, data=None, confidence=parsed.get("confidence"))
        return
    handler = _HANDLERS.get(intent)
    if not handler:
        tracker.end("aggregating")
        yield "done", tracker.result_event(
            query=q, intent=intent, subject=subject, class_name=class_name, grade=grade,
            answer="该功能暂未开放，试试成绩、考勤、素质、获奖或考试安排相关的问题。",
            data=None, confidence=parsed.get("confidence"))
        return
    try:
        block = handler(db, students, subject)
    except Exception:  # noqa: BLE001
        tracker.end("aggregating")
        yield "done", tracker.result_event(
            query=q, intent=intent, subject=subject, class_name=class_name, grade=grade,
            answer="查询失败，请稍后再试。", data=None, confidence=parsed.get("confidence"))
        return
    facts_text, data = block["facts"], block["data"]
    tracker.end("aggregating")

    # 4. LLM 生成自然语言（流式）
    tracker.begin("generating")
    yield "stage", tracker.stage_event("generating")
    if llm.is_available():
        actual_scope = class_name or grade or "当前范围"
        safe_query = _sanitize_query(q, class_name, grade)
        user_prompt = (
            f"用户问题：{safe_query}\n\n实际统计范围：{actual_scope}\n事实数据：\n{facts_text}\n\n"
            "请用自然中文回答用户的问题（以实际统计范围与事实数据为准）。"
        )
        parts = []
        for tok in llm.generate_stream(user_prompt, system=_ANSWER_SYSTEM,
                                       max_tokens=200, temperature=0.4):
            parts.append(tok)
            yield "token", {"type": "token", "text": tok}
        answer = "".join(parts)
    else:
        answer = facts_text
        yield "token", {"type": "token", "text": answer}
    tracker.end("generating")

    yield "done", tracker.result_event(
        query=q, intent=intent, subject=subject, class_name=class_name, grade=grade,
        answer=answer, data=data, confidence=parsed.get("confidence"))
