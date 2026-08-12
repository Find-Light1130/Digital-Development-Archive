"""轻量意图分类模型：字符 n-gram TF-IDF + 质心余弦相似度（纯 numpy）。

设计说明：
- 中文无需分词：直接按字符 n-gram（2-gram/3-gram）构造特征，避免外部分词依赖。
- 训练：由 train_model.py 读取 corpus.py 语料，构造 TF-IDF 矩阵后求每类意图质心。
- 分类：对输入文本做同样特征化，与各意图质心求余弦相似度，取最高分；
  低于 CONFIDENCE_THRESHOLD 判为 unknown（调用方用澄清话术兜底，杜绝文不对题）。
- 工件存储于 backend/ai_modules/model/（.npz 参数 + meta.json 元数据）。
"""

import json
import os
import re

import numpy as np

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
_PARAMS_PATH = os.path.join(_MODEL_DIR, "intent_model.npz")
_META_PATH = os.path.join(_MODEL_DIR, "meta.json")

CONFIDENCE_THRESHOLD = 0.21
_MIN_GRAMS = 2
_MAX_GRAMS = 3

# 问数（教师/管理智能AI助手）可用意图集合
ASK_INTENTS = {
    "mastery", "declining", "warnings", "extremes", "count",
    "attendance", "emotion", "quality", "activity", "award", "exam_plan",
    "growth_index", "trend", "list", "help", "chat", "greet", "thanks", "bye",
}

# 心理树洞可用意图集合
COMPANION_INTENTS = {
    "crisis", "greet", "sad", "anxious", "angry", "tired", "study",
    "friend", "family", "advice", "thanks", "bye", "chat",
}

_punct = re.compile(r"[\s，。！？、；：""''（）《》·\-,.()!?;:…—]")
_alnum = re.compile(r"[a-z0-9]")


def normalize(text: str) -> str:
    """小写、去标点与空白，保留中英文与数字。"""
    t = (text or "").lower()
    t = _punct.sub("", t)
    t = _alnum.sub(lambda m: m.group(0), t)
    return t


def ngrams(text: str):
    """生成字符 n-gram 序列（含首尾边界标记，增强短文本区分度）。"""
    t = normalize(text)
    if not t:
        return []
    # 加入边界标记以捕捉"谁/多少/第一"等词首信息
    padded = "^" + t + "$"
    result = []
    for n in range(_MIN_GRAMS, _MAX_GRAMS + 1):
        for i in range(len(padded) - n + 1):
            result.append(padded[i:i + n])
    return result


def _token_idf(vocab, df, total):
    """TF-IDF：tf = 1（出现计数由向量元素承载），idf = ln((N+1)/(df+1)) + 1。"""
    n = max(total, 1)
    return {
        tok: np.log((n + 1) / (df.get(tok, 0) + 1)) + 1.0
        for tok in vocab
    }


class IntentModel:
    """加载后的意图模型：vocab + idf + 各类质心向量。"""

    def __init__(self, vocab, idf, labels, centroids, threshold=CONFIDENCE_THRESHOLD):
        self.vocab = vocab  # {token: index}
        self.idf = idf  # {token: idf_value}
        self.labels = list(labels)
        self.centroids = np.asarray(centroids, dtype=float)  # (n_labels, n_feats)
        self.threshold = threshold

    # ------------------------------------------------------------------ 向量化

    def _vector(self, text):
        vec = np.zeros(len(self.vocab), dtype=float)
        for tok in ngrams(text):
            idx = self.vocab.get(tok)
            if idx is not None:
                vec[idx] += self.idf[tok]
        return vec

    # ------------------------------------------------------------------ 分类

    def scores(self, text):
        vec = self._vector(text)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return {}
        vec = vec / norm
        cents = self.centroids / (np.linalg.norm(self.centroids, axis=1, keepdims=True) + 1e-9)
        sims = cents @ vec
        return {self.labels[i]: float(sims[i]) for i in range(len(self.labels))}

    def classify(self, text, top_k=3, restrict=None):
        """返回 [(intent, score), ...]（已按得分降序，含 unknown 兜底）。

        restrict: 允许的意图集合（如问数只考虑问数意图、树洞只考虑树洞意图），
        可避免跨域语义冲突（如"成绩退步了"在 study/declining 之间混淆）。
        """
        scores = self.scores(text)
        if restrict:
            scores = {k: v for k, v in scores.items() if k in restrict}
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        if not ranked or ranked[0][1] < self.threshold:
            return [("unknown", ranked[0][1] if ranked else 0.0)]
        return ranked[:top_k]

    def top(self, text, restrict=None):
        """返回最高分意图；低于阈值返回 unknown。"""
        return self.classify(text, top_k=1, restrict=restrict)[0]


# ------------------------------------------------------------------ 加载

def load_model(path=_PARAMS_PATH, meta_path=_META_PATH):
    """加载训练工件；不存在时抛出 FileNotFoundError。"""
    if not os.path.exists(path) or not os.path.exists(meta_path):
        raise FileNotFoundError(
            "意图模型工件不存在，请先运行 python backend/ai_modules/train_model.py")
    data = np.load(path, allow_pickle=False)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    vocab = meta["vocab"]
    idf = meta["idf"]
    return IntentModel(vocab, idf, meta["labels"], data["centroids"])


_model_cache = None


def get_model():
    """懒加载单例。"""
    global _model_cache
    if _model_cache is None:
        _model_cache = load_model()
    return _model_cache
