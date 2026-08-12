"""AI 心理树洞：LLM 共情对话 + 精确数据语境 + 危机红线。

安全设计（不可让步）：
- 危机检测（自伤/轻生/伤人/绝望）永远走关键词红线，绝不放给模型判断；
  命中即紧急升级并保留原 risk_flag/escalate 契约。
- 正常情绪由 LLM 生成共情回复，但注入真实数据语境（近期情绪打卡/弱科）作为事实，
  让回复个性化而非千篇一律。
- 模型不可用时降级到原规则话术池，保证系统可用。

兼容旧契约：返回 dict 含 reply/intent/risk_flag/risk/escalate/prescriptions。
"""

import random

from backend.ai_modules import llm, llm_understanding
from backend.ai_modules.common import load_emotions, subject_mastery
from backend.ai_modules.emotion_companion import (
    detect_intent, emotion_risk, _CRISIS, _CRISIS_KEYWORDS, _PRESCRIPTIONS, regulation_prescription,
)


def _keyword_crisis(message):
    """关键词危机检测。返回 (crisis_type, keyword) 或 (None, None)。"""
    text = (message or "").lower()
    for group, keywords in _CRISIS_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return group, kw
    return None, None


def _context_facts(db, student_id, intent):
    """生成个性化语境事实（供 LLM 引用，数字/名单必须真实）。"""
    extras = []
    emotions = load_emotions(db, [student_id]).get(student_id, [])
    recent = [e for e in emotions if e.emotion_level is not None][-3:]
    if recent:
        avg = round(sum(e.emotion_level for e in recent) / len(recent), 1)
        if avg <= 1.3:
            extras.append("学生最近的情绪打卡普遍偏低（近3次均值%.1f/5）。" % avg)
        elif avg <= 2.5:
            extras.append("学生近期情绪打卡均值%.1f/5，略偏低。" % avg)
    if intent == "study":
        from backend.models import Score
        scores = db.query(Score).filter(Score.student_id == student_id).all()
        mastery = subject_mastery(scores)
        weak = sorted(mastery.items(), key=lambda kv: kv[1])[:2]
        if weak:
            subs = "、".join(s for s, _ in weak)
            extras.append(f"学生最近的弱科：{subs}。")
    return extras


def _llm_reply(message, intent, context_facts):
    """LLM 生成共情回复；不可用时返回 None（调用方回落规则话术）。"""
    if not llm.is_available():
        return None
    system = (
        "你是一位温柔、耐心、有分寸的中学生心理树洞陪伴者。学生向你倾诉心情。"
        "请用自然、温暖、简洁的中文回应（2-3句话），先共情，再试着引导对方多说一点，"
        "不要用说教口吻，不要评价对错，不要重复提问。"
    )
    user = f"学生说：{message}"
    if context_facts:
        user += "\n\n（可参考的真实背景信息：\n" + "\n".join(context_facts) + "）"
    try:
        return llm.generate(user, system=system, max_tokens=180, temperature=0.7)
    except Exception:  # noqa: BLE001
        return None


def companion_reply(db, student_id, message, use_llm=True):
    """生成树洞回复。返回与原 companion_reply 兼容的 dict。"""
    risk = emotion_risk(db, student_id)

    # 1. 危机红线（关键词优先，永不让模型裁决）
    crisis_type, kw = _keyword_crisis(message)
    if crisis_type:
        return {
            "reply": random.choice(_CRISIS),
            "intent": "crisis",
            "risk_flag": True,
            "crisis_type": crisis_type,
            "keyword": kw,
            "risk": risk,
            "emergency": True,
            "escalate": True,
            "prescriptions": regulation_prescription("help"),
        }

    # 2. 模型语义情绪理解（辅助选择话术池；不作为安全依据）
    intent, crisis_type_llm, confidence = None, None, None
    if use_llm:
        parsed = llm_understanding.understand_companion(message)
        intent = parsed["intent"]
        confidence = parsed.get("confidence")
        if parsed.get("crisis"):
            # 模型认为有危机 → 仍走关键词层二次确认；未命中关键词则保守升级
            ct, kw2 = _keyword_crisis(message)
            if ct:
                return {
                    "reply": random.choice(_CRISIS),
                    "intent": "crisis",
                    "risk_flag": True,
                    "crisis_type": ct,
                    "keyword": kw2,
                    "risk": risk,
                    "emergency": True,
                    "escalate": True,
                    "prescriptions": regulation_prescription("help"),
                }
            # 模型单方面认为危机但无关键词命中 → 不以模型为据，回落规则意图
            intent, _kw, crisis_type_llm = detect_intent(message)
    if not intent:
        intent, _kw, crisis_type_llm = detect_intent(message)
    intent = "crisis" if intent == "crisis" and not crisis_type else intent

    # 3. LLM 生成共情回复（带真实语境）
    context_facts = _context_facts(db, student_id, intent)
    reply = _llm_reply(message, intent, context_facts) if use_llm else None

    # 4. 降级：规则话术池 + 语境补充（保持原有质感）
    if reply is None:
        from backend.ai_modules.emotion_companion import (
            _GREET, _SAD, _ANXIOUS, _ANGRY, _TIRED, _STUDY, _FRIEND,
            _FAMILY, _HELP, _THANKS, _BYE, _CHAT_FALLBACK,
        )
        pools = {
            "greet": _GREET, "sad": _SAD, "anxious": _ANXIOUS, "angry": _ANGRY,
            "tired": _TIRED, "study": _STUDY, "friend": _FRIEND, "family": _FAMILY,
            "help": _HELP, "thanks": _THANKS, "bye": _BYE, "chat": _CHAT_FALLBACK,
        }
        reply = random.choice(pools.get(intent, _CHAT_FALLBACK))
        extras = []
        if intent in ("sad", "anxious") and context_facts:
            extras.append("我注意到你最近几天的情绪打卡都不太高，如果你愿意，可以把心事说给我听。")
        if intent == "study" and context_facts:
            extras.append(f"另外我看了看你最近的数据，{context_facts[0]}")
        tail = " 我先陪着你，你可以随时再说。"
        if risk.get("level") in ("medium", "high") and risk.get("reasons"):
            extras.append(f"不过我更希望你能同时和心理老师聊聊：我注意到{risk['reasons'][0]}。")
        reply = reply + ((" " + " ".join(extras)) if extras else "") + tail

    return {
        "reply": reply,
        "intent": intent if intent != "crisis" else ("crisis" if crisis_type else intent),
        "risk_flag": False,
        "risk": risk,
        "escalate": risk.get("level") in ("medium", "high"),
        "prescriptions": regulation_prescription(intent if intent != "crisis" else "help"),
        "confidence": confidence,
    }


def companion_reply_stream(db, student_id, message):
    """SSE 流式树洞回复：yield (event_type, payload)。

    stage(searching)->stage(generating)->token(...) ... -> done(...)
    危机红线命中时直接 done（不再让模型生成，保证最快响应）。
    """
    from backend.ai_modules.thinking import StageTracker
    tracker = StageTracker(labels={"searching": "正在理解你的心情", "generating": "正在为你回复"})
    risk = emotion_risk(db, student_id)

    crisis_type, kw = _keyword_crisis(message)
    if crisis_type:
        result = {
            "reply": random.choice(_CRISIS), "intent": "crisis", "risk_flag": True,
            "crisis_type": crisis_type, "keyword": kw, "risk": risk,
            "emergency": True, "escalate": True,
            "prescriptions": regulation_prescription("help"),
        }
        yield "done", tracker.result_event(**result)
        return

    tracker.begin("searching")
    yield "stage", tracker.stage_event("searching")
    parsed = llm_understanding.understand_companion(message)
    intent = parsed["intent"]
    if parsed.get("crisis"):
        ct, kw2 = _keyword_crisis(message)
        if ct:
            result = {
                "reply": random.choice(_CRISIS), "intent": "crisis", "risk_flag": True,
                "crisis_type": ct, "keyword": kw2, "risk": risk,
                "emergency": True, "escalate": True,
                "prescriptions": regulation_prescription("help"),
            }
            yield "done", tracker.result_event(**result)
            return
        # 模型单方面认为危机但无关键词命中 → 不以模型为据，回落规则意图
        intent, _kw, _ct = detect_intent(message)
    tracker.end("searching")

    context_facts = _context_facts(db, student_id, intent)
    tracker.begin("generating")
    yield "stage", tracker.stage_event("generating")

    if llm.is_available():
        system = (
            "你是一位温柔、耐心、有分寸的中学生心理树洞陪伴者。学生向你倾诉心情。"
            "请用自然、温暖、简洁的中文回应（2-3句话），先共情，再试着引导对方多说一点，"
            "不要用说教口吻，不要评价对错，不要重复提问。"
        )
        user = f"学生说：{message}"
        if context_facts:
            user += "\n\n（可参考的真实背景信息：\n" + "\n".join(context_facts) + "）"
        parts = []
        try:
            for tok in llm.generate_stream(user, system=system, max_tokens=180, temperature=0.7):
                parts.append(tok)
                yield "token", {"type": "token", "text": tok}
            reply = "".join(parts).strip()
        except Exception:  # noqa: BLE001
            reply = None
    else:
        reply = None

    if not reply:
        from backend.ai_modules.emotion_companion import companion_reply as _rule_reply
        rule = _rule_reply(db, student_id, message)
        reply = rule["reply"]
        yield "token", {"type": "token", "text": reply}

    tracker.end("generating")
    result = {
        "reply": reply, "intent": intent if intent != "crisis" else "crisis",
        "risk_flag": False, "risk": risk,
        "escalate": risk.get("level") in ("medium", "high"),
        "prescriptions": regulation_prescription(intent if intent != "crisis" else "help"),
        "confidence": parsed.get("confidence"),
    }
    yield "done", tracker.result_event(**result)
