"""LLM 语义理解层：用本地小模型理解自然语言（意图 + 槽位提取），替代 TF-IDF 分类器。

与「判断系统」的关键区别：
- 不依赖关键词/字符 n-gram 匹配，而是由语言模型理解问句语义；
- 模型输出结构化 JSON（intent/class_name/grade/subject/time/confidence），
  供问数/树洞统一消费；
- 权限边界在此层强制校验：模型提取到的范围必须落在 user_scope 之内，
  越权一律回落用户默认范围（教师→本班、组长→本年级），从源头杜绝越权。

降级路径：模型不可用时回落到 intent_model（TF-IDF）原有实现，保证系统可用。
"""

import json

from backend.ai_modules import llm
from backend.ai_modules.intent_model import get_model, ASK_INTENTS, COMPANION_INTENTS
from backend.routes.auth import user_scope

# 问数意图（与 corpus 保持一致）
ASK_LABELS = [
    "mastery", "declining", "warnings", "extremes", "count",
    "attendance", "emotion", "quality", "activity", "award", "exam_plan",
    "growth_index", "trend", "list", "help", "chat", "greet", "thanks", "bye",
]

# 树洞意图
COMPANION_LABELS = [
    "crisis", "greet", "sad", "anxious", "angry", "tired", "study",
    "friend", "family", "advice", "thanks", "bye", "chat",
]

_ASK_PROMPT = """你是校园学情数据问答助手。用户会提问关于班级/年级学生的成绩、考勤、情绪、素质、活动、获奖、考试安排等数据问题。

请理解用户意图并提取关键信息，只输出一个 JSON 对象（不要任何其他文字），JSON 必须包含全部字段，intent 字段必须填写：

{{"intent": "这里填意图", "class_name": "这里填班级或null", "grade": "这里填年级或null", "subject": "这里填学科或null", "time": "这里填时间或null", "confidence": 0.0}}

可选意图(intent)之一（只能选一个）：
{labels}

字段说明：
- "intent": 上述意图之一。问"平均分/掌握率/整体成绩"→mastery；问"谁下滑/退步"→declining；问"预警/风险"→warnings；问"最高最低"→extremes；问"多少人"→count；问"考勤/出勤/缺勤"→attendance；问"情绪"→emotion；问"素质/音体美信"→quality；问"活动"→activity；问"获奖"→award；问"考试安排"→exam_plan；问"成长指数"→growth_index；问"趋势"→trend；问"名单/有哪些人"→list；打招呼→greet；道谢→thanks；告别→bye；问能做什么→help；其他闲聊→chat。
- "class_name": 班级名（格式如"初一1班"，没提到班级则为 null）
- "grade": 年级（初一/初二/初三，没提到则为 null）
- "subject": 学科（语文/数学/英语/物理/化学/生物/历史/地理/道德与法治/音乐/体育/美术/信息技术，没提到则为 null）
- "time": 时间范围（如"近7天"/"上周"/"本学期"，没提到则为 null）
- "confidence": 0到1的浮点数，表示你对意图判断的确信程度

示例：
用户问题：初一1班数学平均分多少
{{"intent": "mastery", "class_name": "初一1班", "grade": "初一", "subject": "数学", "time": null, "confidence": 0.98}}

用户问题：我们班谁成绩退步了
{{"intent": "declining", "class_name": "初一1班", "grade": "初一", "subject": null, "time": null, "confidence": 0.9}}

用户问题：{query}
"""

_COMPANION_PROMPT = """你是一个理解中学生心情的树洞助手。学生会对你说心里话。

请理解学生的情绪并输出一个 JSON 对象（不要任何其他文字），JSON 必须包含全部字段：

{{"intent": "这里填情绪意图", "crisis": false, "confidence": 0.0}}

可选情绪意图(intent)之一（只能选一个）：
{labels}

字段：
- "intent": 最匹配的情绪意图。难过想哭→sad；焦虑紧张压力大→anxious；生气愤怒→angry；疲惫没劲→tired；学习考试困扰→study；朋友矛盾→friend；家庭烦恼→family；求助要建议→advice；道谢→thanks；告别→bye；打招呼→greet；其他→chat。
- "crisis": 布尔值，仅当学生表达强烈的自我伤害/轻生/伤人倾向时为 true，否则 false。
- "confidence": 0到1的浮点数。

示例：
学生的话：最近压力好大，睡不着
{{"intent": "anxious", "crisis": false, "confidence": 0.95}}

学生的话：我好难过，想哭
{{"intent": "sad", "crisis": false, "confidence": 0.95}}

学生的话：{query}
"""


def _parse_json(text):
    """鲁棒解析模型输出的 JSON（容忍围栏/前后缀）。"""
    t = llm._extract_json(text)  # noqa: SLF001  # 复用工具函数
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return None


def _clamp(value, lo, hi):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def _allowed_intents(domain):
    return ASK_LABELS if domain == "ask" else COMPANION_LABELS


def _fallback_ask(query):
    """模型不可用时回落到 TF-IDF 分类器（只作降级，不参与 LLM 语义理解）。"""
    try:
        model = get_model()
        intent, conf = model.top(query, restrict=ASK_INTENTS)
        return {
            "intent": intent, "class_name": None, "grade": None,
            "subject": None, "time": None, "confidence": _clamp(conf, 0.0, 1.0),
            "fallback": True,
        }
    except Exception:  # noqa: BLE001
        return {"intent": "chat", "class_name": None, "grade": None,
                "subject": None, "time": None, "confidence": 0.1, "fallback": True}


def understand_ask(query, history=None):
    """理解问数意图与槽位。返回 dict。模型不可用时降级。"""
    if not llm.is_available():
        return _fallback_ask(query)
    try:
        prompt = _ASK_PROMPT.format(labels=", ".join(ASK_LABELS), query=query)
        text = llm.generate(prompt, system="你是校园学情数据助手，只输出 JSON。",
                            max_tokens=120, temperature=0.1)
        data = _parse_json(text) or {}
        intent = str(data.get("intent", "chat")).strip()
        if intent not in ASK_LABELS:
            intent = "chat"
        return {
            "intent": intent,
            "class_name": data.get("class_name") or None,
            "grade": data.get("grade") or None,
            "subject": data.get("subject") or None,
            "time": data.get("time") or None,
            "confidence": _clamp(data.get("confidence", 0.5), 0.0, 1.0),
            "fallback": False,
        }
    except Exception:  # noqa: BLE001
        return _fallback_ask(query)


def understand_companion(message):
    """理解树洞消息的情绪意图。返回 dict（含 crisis 标记）。模型不可用时降级。"""
    if not llm.is_available():
        from backend.ai_modules.emotion_companion import detect_intent
        intent, _kw, crisis_type = detect_intent(message)
        return {"intent": intent, "crisis": intent == "crisis",
                "crisis_type": crisis_type, "confidence": 0.6, "fallback": True}
    try:
        prompt = _COMPANION_PROMPT.format(labels=", ".join(COMPANION_LABELS), query=message)
        text = llm.generate(prompt, system="你是校园心理树洞助手，只输出 JSON。",
                            max_tokens=100, temperature=0.1)
        data = _parse_json(text) or {}
        intent = str(data.get("intent", "chat")).strip()
        if intent not in COMPANION_LABELS:
            intent = "chat"
        return {
            "intent": intent,
            "crisis": bool(data.get("crisis", False)),
            "crisis_type": None,
            "confidence": _clamp(data.get("confidence", 0.5), 0.0, 1.0),
            "fallback": False,
        }
    except Exception:  # noqa: BLE001
        from backend.ai_modules.emotion_companion import detect_intent
        intent, _kw, crisis_type = detect_intent(message)
        return {"intent": intent, "crisis": intent == "crisis",
                "crisis_type": crisis_type, "confidence": 0.6, "fallback": True}


# ---------------------------------------------------------------- 权限收敛

_CLASS_RE = __import__("re").compile(r"[初高][一二三]\d+班")
_GRADES = ("初一", "初二", "初三")
_SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理",
             "道德与法治", "音乐", "体育", "美术", "信息技术"]


def enforce_scope(user, parsed, context=None):
    """权限边界：把模型提取/上下文继承的范围收敛到用户可见范围。

    返回 (class_name, grade)。越权的范围一律回落用户默认范围。
    context: 上一轮会话摘要 {"class_name":..,"grade":..}（仅在用户范围内才继承）。

    校验规则按角色：
      admin        不限
      teacher      仅可看本班（class_names 集合）；任何年级维度一律拒绝
      grade_leader 仅可看本年级（grades 集合）；班级必须属于本年级
    """
    role = user.role
    scope = user_scope(user)
    allowed_classes = set(scope["class_names"] or [])
    allowed_grades = set(scope["grades"] or [])

    def _class_allowed(cn):
        if role == "admin":
            return True
        if allowed_classes:
            return cn in allowed_classes
        if allowed_grades:
            return cn.startswith(sorted(allowed_grades)[0])
        return False

    def _grade_allowed(g):
        if role == "admin":
            return True
        if allowed_grades:
            return g in allowed_grades
        if allowed_classes:
            return False
        return False

    class_name, grade = None, None

    # 模型提取的范围先校验；越权则丢弃
    m = parsed.get("class_name")
    if m and _CLASS_RE.fullmatch(m) and _class_allowed(m):
        class_name = m
    else:
        g = parsed.get("grade")
        if g and g in _GRADES and _grade_allowed(g):
            grade = g

    if not class_name and not grade:
        # 上下文继承（同样校验边界）
        if context:
            ctx_cn = context.get("class_name")
            ctx_g = context.get("grade")
            if ctx_cn and _CLASS_RE.fullmatch(ctx_cn) and _class_allowed(ctx_cn):
                class_name = ctx_cn
            elif ctx_g and ctx_g in _GRADES and _grade_allowed(ctx_g):
                grade = ctx_g

    if not class_name and not grade:
        # 回落到用户默认范围
        if allowed_classes:
            class_name = sorted(allowed_classes)[0]
        elif allowed_grades:
            grade = sorted(allowed_grades)[0]

    return class_name, grade
