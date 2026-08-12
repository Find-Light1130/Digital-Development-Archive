"""AI 思考阶段状态机：为 SSE 推流提供分阶段事件。

阶段顺序：
    searching  -> 正在搜索资料（检索数据层事实块）
    aggregating -> 正在整合数据（整理/聚合结果）
    generating  -> 正在生成回答（LLM 推理生成）
    done        -> 完成（携带最终结构化结果）

每阶段真实触发时记录耗时，由路由层包装为 SSE event: stage。
"""

import time


class StageTracker:
    """记录各阶段开始/结束耗时，并生成阶段事件文本。"""

    def __init__(self, labels=None):
        # labels: {"searching": "正在搜索资料", "aggregating": "正在整合数据", "generating": "正在生成回答"}
        self.labels = labels or {
            "searching": "正在搜索资料",
            "aggregating": "正在整合数据",
            "generating": "正在生成回答",
        }
        self._times = {}
        self._started = None

    def begin(self, stage):
        self._times[stage] = {"start": time.time(), "end": None, "ms": None}

    def end(self, stage):
        if stage in self._times and self._times[stage]["end"] is None:
            self._times[stage]["end"] = time.time()
            self._times[stage]["ms"] = round((self._times[stage]["end"] - self._times[stage]["start"]) * 1000)

    def __enter__(self):
        self._started = time.time()
        return self

    def __exit__(self, *exc):
        return False

    def stage_event(self, stage):
        """返回 SSE 阶段事件 dict。"""
        return {"type": "stage", "stage": stage, "label": self.labels.get(stage, stage)}

    def result_event(self, **payload):
        """返回 SSE done 事件 dict（携带最终结果）。"""
        elapsed = round((time.time() - self._started) * 1000) if self._started else None
        return {"type": "done", "elapsed_ms": elapsed, **payload}

    def error_event(self, message):
        return {"type": "error", "message": message}
