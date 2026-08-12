"""LLM 文案润色：把精确数据模板段落改写为更自然、更有温度的中文表达。

原则：数字/名单/结论一律来自精确计算层（template 内），LLM 只负责润色文字，
prompt 里明确禁止改动任何数字、百分比、人名与结论。

模型不可用时原样返回模板文本（保证系统不降级）。
"""

from backend.ai_modules import llm


def polish(template, tone=None, max_tokens=250):
    """把模板段落润色为自然语言。template 为包含真实数据的文本。

    tone: 可选风格提示，如"温暖鼓励"/"专业客观"/"简洁直接"。
    """
    if not template or not llm.is_available():
        return template
    system = (
        "你是一位资深中学教师兼文案编辑。请把下方给定的『原文内容』润色为自然、通顺、"
        "有人情味的中文表达。要求：必须保留原文中所有数字、百分比、人名、班级、学科与结论，"
        "不得增删或篡改任何事实；可以调整句式、补充恰当的过渡词与语气；整体比原文更自然好读。"
    )
    if tone:
        system += f" 风格倾向：{tone}。"
    user = f"原文内容：\n{template}\n\n请润色，只输出润色后的完整内容。"
    try:
        result = llm.generate(user, system=system, max_tokens=max_tokens, temperature=0.5)
        result = (result or "").strip()
        return result if result else template
    except Exception:  # noqa: BLE001
        return template


def polish_stream(template, tone=None, max_tokens=250):
    """流式润色：yield token。失败时 yield 原文。"""
    if not template or not llm.is_available():
        yield template
        return
    system = (
        "你是一位资深中学教师兼文案编辑。请把下方给定的『原文内容』润色为自然、通顺、"
        "有人情味的中文表达。要求：必须保留原文中所有数字、百分比、人名、班级、学科与结论，"
        "不得增删或篡改任何事实；可以调整句式、补充恰当的过渡词与语气；整体比原文更自然好读。"
    )
    if tone:
        system += f" 风格倾向：{tone}。"
    user = f"原文内容：\n{template}\n\n请润色，只输出润色后的完整内容。"
    try:
        for tok in llm.generate_stream(user, system=system, max_tokens=max_tokens, temperature=0.5):
            yield tok
    except Exception:  # noqa: BLE001
        yield template
