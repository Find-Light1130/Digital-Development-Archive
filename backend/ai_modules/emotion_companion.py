"""AI 心理树洞：规则对话引擎 + 情绪风险分级 + 心理调节处方。

纯本地实现：通过关键词意图识别 + 读取学生真实数据（近期情绪/弱科）生成共情回应。
严格遵循安全边界：AI 只做陪伴与疏导，明确提示可求助的真实资源；
检测到高风险（危机）措辞时立即升级并建议联系心理老师/紧急渠道。
"""

import random
from collections import defaultdict

from backend.ai_modules.common import load_emotions, subject_mastery

# ---------------------------------------------------------------- 意图识别

# 危机信号按类型分组：self_harm（自伤/轻生）、harm_others（伤人/毁灭）、hopeless（绝望感）
_CRISIS_KEYWORDS = {
    "self_harm": [
        "自杀", "想死", "轻生", "不想活", "不想活", "活不下去", "活够了", "不想存在",
        "伤害自己", "自残", "割腕", "结束生命", "了结自己", "一了百了", "想消失",
        "结束自己", "不想再见", "去死", "跳楼", "了结",
    ],
    "harm_others": [
        "毁灭世界", "杀人", "杀了", "杀光", "报复社会", "同归于尽", "伤害别人",
        "我要弄死", "拉人垫背", "炸了学校", "报复他们",
    ],
    "hopeless": [
        "没有意义", "活着没意思", "活着没劲", "活着没意思", "撑不下去", "熬不下去了",
        "不知道活着为了什么", "活着好累", "活着真没意思", "人生没意思", "活得好没意思",
        "活着没盼头",
    ],
}

_INTENT_KEYWORDS = {
    "crisis": [kw for group in _CRISIS_KEYWORDS.values() for kw in group],
    "greet": ["你好", "您好", "hi", "嗨", "hello", "哈喽", "在吗", "在么", "你好呀"],
    "sad": ["难过", "伤心", "不开心", "沮丧", "郁闷", "想哭", "哭", "低落", "emo", "委屈", "失落", "消沉", "心情不好"],
    "anxious": ["焦虑", "紧张", "压力", "害怕", "担心", "烦躁", "慌", "不安", "失眠", "睡不着", "心慌", "恐慌"],
    "angry": ["生气", "愤怒", "气死", "火大", "烦死了", "烦"],
    "tired": ["累", "疲惫", "没精神", "困", "乏力", "不想动", "太累了", "身心俱疲"],
    "study": ["考试", "成绩", "考砸", "考差", "考不好", "学不会", "听不懂", "作业", "复习", "月考", "期中", "期末",
              "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "道法", "道德", "学习", "背不下来"],
    "friend": ["朋友", "同学", "室友", "同桌", "孤立", "吵架", "背叛", "闹翻", "不和", "被排挤", "没人理"],
    "family": ["爸妈", "父母", "家长", "妈妈", "爸爸", "家里", "家人", "家庭", "唠叨", "控制"],
    "help": ["怎么办", "帮助", "帮帮我", "建议", "办法", "怎么调整", "怎么缓解", "怎么走出来", "怎么放松"],
    "thanks": ["谢谢", "感谢", "谢了", "辛苦"],
    "bye": ["再见", "拜拜", "晚安", "先聊到这", "不聊了", "下了"],
}

_INTENTS_ORDER = ["crisis", "greet", "sad", "anxious", "angry", "tired",
                  "study", "friend", "family", "help", "thanks", "bye"]


def detect_intent(message: str):
    """返回 (intent, keyword)。危机命中时 keyword 为命中的信号词，并附带危机类型。

    设计：危机关键词按类型分组（_CRISIS_KEYWORDS），命中后据分组判定
    crisis_type（self_harm/harm_others/hopeless），供通报与安抚话术区分。
    """
    text = (message or "").lower()
    if any(kw in text for kw in _CRISIS_KEYWORDS["self_harm"]):
        kw = next(k for k in _CRISIS_KEYWORDS["self_harm"] if k in text)
        return "crisis", kw, "self_harm"
    if any(kw in text for kw in _CRISIS_KEYWORDS["harm_others"]):
        kw = next(k for k in _CRISIS_KEYWORDS["harm_others"] if k in text)
        return "crisis", kw, "harm_others"
    if any(kw in text for kw in _CRISIS_KEYWORDS["hopeless"]):
        kw = next(k for k in _CRISIS_KEYWORDS["hopeless"] if k in text)
        return "crisis", kw, "hopeless"
    for intent in _INTENTS_ORDER:
        if intent == "crisis":
            continue
        for kw in _INTENT_KEYWORDS[intent]:
            if kw in text:
                return intent, kw, None
    return "chat", None, None


# ---------------------------------------------------------------- 情绪风险分级

def emotion_risk(db, student_id):
    """基于情绪打卡记录输出风险分级与原因（供树洞与心理老师工作台共用）。"""
    emotions = sorted(load_emotions(db, [student_id]).get(student_id, []), key=lambda e: e.date)
    recent7 = [e for e in emotions if e.emotion_level is not None][-7:]
    recent14 = [e for e in emotions if e.emotion_level is not None][-14:]

    score = 0
    reasons = []
    if len(recent7) >= 3:
        avg = sum(e.emotion_level for e in recent7) / len(recent7)
        if avg <= 1.3:
            score += 40
            reasons.append("近一周情绪普遍低落")
        levels7 = [e.emotion_level for e in recent7]
        trailing_low = 0
        for v in reversed(levels7):
            if v <= 1:
                trailing_low += 1
            else:
                break
        if trailing_low >= 3:
            score += 30
            reasons.append("已连续多天情绪低落")
        if len(levels7) >= 3 and max(levels7) - min(levels7) >= 2 and len(set(levels7)) >= 3:
            score += 15
            reasons.append("近期情绪波动较大")
    if recent14:
        low_ratio = sum(1 for e in recent14 if e.emotion_level <= 1) / len(recent14)
        if low_ratio >= 0.5:
            score += 20
            reasons.append("近两周低落天数占比较高")
        tags = [t for e in recent14 for t in (e.tags.split(",") if e.tags else [])]
        if sum(1 for t in tags if t in ("焦虑", "疲惫")) >= 2:
            score += 10
            reasons.append("焦虑/疲惫标签出现频繁")

    level = "high" if score >= 55 else ("medium" if score >= 25 else "low")
    return {
        "level": level,
        "score": min(100, score),
        "reasons": reasons,
        "recent": [{"date": str(e.date), "level": e.emotion_level, "tags": (e.tags.split(",") if e.tags else [])}
                   for e in recent7],
    }


# ---------------------------------------------------------------- 回应生成

_GREET = [
    "你好呀，我一直在。今天有什么想跟我说的吗？",
    "嗨，很高兴你愿意来找我聊。发生了什么事，都可以慢慢说。",
    "你好呀～放松一下，我就在这里听着，想说什么都可以。",
]

_SAD = [
    "抱抱你。听起来你今天心情很低落，愿意多说一点发生了什么吗？",
    "难过的时候不需要强撑，你在自己眼里也许普通，但在我这里每一次低落都被认真对待。如果愿意，可以讲讲让你难过的那件事。",
    "这种感觉一定很不好受。允许自己难过一会儿，慢慢说出来，我们一起看看能做点什么。",
]

_ANXIOUS = [
    "能感觉到你心里压着不少东西。焦虑其实是一种提醒，说明你对自己有期待。可以先做个深呼吸，再把让你紧张的具体事情一件件说出来。",
    "紧张和担心都是很正常的反应。试着把「最坏会怎样」具体写下来，很多时候写下来就会发现没那么可怕。你具体在担心什么呢？",
    "压力大的时候，试着把注意力从「结果」放到「下一步」，一次只做眼前这一件小事。愿意跟我聊聊让你最焦虑的是哪件事吗？",
]

_ANGRY = [
    "生气说明这件事碰到了你的底线，你的感受是合理且重要的。可以先用「我很生气，因为……」把话说清楚，而不是憋着。",
    "先别急着压住这团火，你的愤怒值得被看见。发生了什么让你这么生气？",
]

_TIRED = [
    "累成这样，说明你真的辛苦了。身体是最诚实的，它需要被照顾。今天有没有可能早点休息，哪怕只是多睡半小时？",
    "疲惫的时候效率反而更低，磨刀不误砍柴工。建议今晚给自己一点空白时间，先恢复电量再继续。",
]

_STUDY = [
    "考试和成绩确实会带来压力，但一次结果从来定义不了你的全部。你的努力一点都不会白费，问题是可以被拆解解决的。",
    "学不会不等于你不行，只是还没找到对的路。咱们可以把它拆小，比如只盯住一个知识点，先啃下来一个再说。",
    "听起来学习上的事让你挺困扰的。别急着和难题硬碰硬，有时候放一放、换个方法，思路就通了。",
]

_FRIEND = [
    "和同学之间出现别扭真的很影响心情。关系是需要经营的，你愿意的话，可以试着先冷静一天，再坦诚地把感受说出来。",
    "被朋友冷落或孤立的感觉很难受。先别急着怀疑自己，一段健康的关系不会让你一直委屈。需要聊聊具体发生了什么吗？",
]

_FAMILY = [
    "和家人沟通不畅是很常见也特别耗神的事。他们的出发点可能是关心，但表达方式让你难受也是真实的。可以试着用「我感到……因为……」去表达，而不是对抗。",
    "家里的事往往最容易牵动情绪。你不需要一夜之间解决所有问题，先从照顾好自己的感受开始。",
]

_HELP = [
    "我给你几个今天就能用的小方法：① 4-7-8 呼吸法（吸气4秒、屏住7秒、呼气8秒），重复3轮；② 把烦恼写在纸上然后划掉一件能马上做的小事；③ 出去走走或跑几分钟。",
    "可以试试：先给自己倒杯温水，做三次深呼吸；然后从「最不影响心情、但能立刻完成」的那件事开始做起。情绪会一点点松开的。",
]

_THANKS = [
    "不客气，能帮到你我很开心。情绪有起伏很正常，随时回来找我。",
    "不用谢～记得照顾好自己，我随时都在。",
]

_BYE = [
    "好的，今天聊到这。记得给自己一点温柔，晚安。",
    "去吧，去好好休息。需要的时候，我都在。",
]

_CHAT_FALLBACK = [
    "我在认真听。你说的这件事，能再具体一点吗？比如当时发生了什么、你现在的感受是什么样的？",
    "嗯，我感受到你的情绪了。继续说说看，没关系，慢慢来。",
    "你愿意把这些说出来，已经很勇敢了。我们可以换个角度看看这件事，你介意吗？",
]

_CRISIS = [
    "看到你说这样的话，我真的很担心你。你现在的感受非常痛苦，但请你先不要一个人扛着。请立刻联系你信任的人：班主任、心理老师，或者直接拨打 12355（青少年心理热线）/ 110 寻求帮助。你的生命很珍贵，眼前的黑暗真的会过去。",
]

# 各意图的调节小处方（供学习路径/心理调节页共用）
_PRESCRIPTIONS = {
    "sad": ["给信任的人发条消息聊聊", "听一首喜欢的歌或看一段治愈视频", "写情绪日记，把难受写下来", "做一次深呼吸练习（4-7-8呼吸法）"],
    "anxious": ["4-7-8 呼吸法重复3轮", "把担心的具体事情写在纸上", "散散步或做几分钟拉伸", "一次只专注眼前一件小事"],
    "angry": ["先离开现场冷静10分钟", "把生气的事写下来撕掉", "用说话代替发泄：说清楚感受而非指责", "去跑几圈把情绪释放掉"],
    "tired": ["今晚提前30分钟上床", "课间站起来走动5分钟", "减少刷手机，让大脑真正休息", "午休眯15分钟"],
    "study": ["拆小目标：只攻克一个知识点", "整理错题本并周末复盘", "向任课老师请教一次", "与学习伙伴互相讲题"],
    "friend": ["冷静一天后再坦诚沟通", "用「我感到……」表达而不是指责", "参加一次集体活动缓一缓", "给自己留点独处空间"],
    "family": ["用「我感到……因为……」表达", "约定一个家庭沟通时间", "先照顾好自己的感受", "必要时请班主任帮忙沟通"],
    "help": ["做三次4-7-8深呼吸", "把烦恼写在纸上再划掉能马上做的一件小事", "出去走走或跑几分钟", "给信任的人发条消息"],
}


def regulation_prescription(intent):
    return _PRESCRIPTIONS.get(intent, _PRESCRIPTIONS["help"])


def _context_note(db, student_id, intent):
    """根据真实情绪数据生成个性化语境补充，让回应不那么"模板"。"""
    if intent not in ("sad", "anxious"):
        return None
    emotions = load_emotions(db, [student_id]).get(student_id, [])
    recent = [e for e in emotions if e.emotion_level is not None][-3:]
    if recent and all(e.emotion_level <= 1 for e in recent):
        return "我注意到你最近几天的情绪打卡都不太高，如果你愿意，可以把心事说给我听。"
    return None


def companion_reply(db, student_id, message):
    intent, kw, crisis_type = detect_intent(message)
    risk_flag = intent == "crisis"
    risk = emotion_risk(db, student_id)

    if intent == "crisis":
        reply = random.choice(_CRISIS)
        return {"reply": reply, "intent": intent, "risk_flag": True,
                "crisis_type": crisis_type, "keyword": kw,
                "risk": risk, "emergency": True, "escalate": True}

    pools = {
        "greet": _GREET, "sad": _SAD, "anxious": _ANXIOUS, "angry": _ANGRY,
        "tired": _TIRED, "study": _STUDY, "friend": _FRIEND, "family": _FAMILY,
        "help": _HELP, "thanks": _THANKS, "bye": _BYE, "chat": _CHAT_FALLBACK,
    }
    base = random.choice(pools.get(intent, _CHAT_FALLBACK))

    # 语境补充
    extras = []
    if intent in ("sad", "anxious"):
        note = _context_note(db, student_id, intent)
        if note:
            extras.append(note)
    if intent == "study":
        from backend.models import Score
        scores = db.query(Score).filter(Score.student_id == student_id).all()
        mastery = subject_mastery(scores)
        weak = sorted(mastery.items(), key=lambda kv: kv[1])[:2]
        if weak:
            subs = "、".join(s for s, _ in weak)
            extras.append(f"另外我看了看你最近的数据，{subs}或许可以成为接下来一起攻克的小目标。")
    if intent in ("help",):
        extras.append("如果需要，我可以把适合你的调节小方法列出来。")

    tail = " 我先陪着你，你可以随时再说。"
    if risk.get("level") in ("medium", "high") and risk.get("reasons"):
        extras.append(f"不过我更希望你能同时和心理老师聊聊：我注意到{risk['reasons'][0]}。")

    return {
        "reply": base + ((" " + " ".join(extras)) if extras else "") + tail,
        "intent": intent,
        "risk_flag": False,
        "risk": risk,
        "escalate": risk.get("level") in ("medium", "high"),
        "prescriptions": regulation_prescription(intent),
    }
