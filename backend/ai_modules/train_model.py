"""意图模型训练脚本：读取 corpus.py 语料，构建 TF-IDF 质心模型并保存工件。

用法：
    python backend/ai_modules/train_model.py

输出：
    backend/ai_modules/model/intent_model.npz  （centroids 参数）
    backend/ai_modules/model/meta.json          （vocab/idf/labels 元数据）

模型训练完即可离线使用，无需联网。
"""

import json
import os
from collections import defaultdict

import numpy as np

from backend.ai_modules.corpus import INTENT_EXAMPLES
from backend.ai_modules.intent_model import ngrams, _token_idf

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
_PARAMS_PATH = os.path.join(_MODEL_DIR, "intent_model.npz")
_META_PATH = os.path.join(_MODEL_DIR, "meta.json")


def build():
    """返回 (vocab, idf, labels, centroid_matrix)。"""
    texts = [ngrams(t) for _, t in INTENT_EXAMPLES]
    intents = [i for i, _ in INTENT_EXAMPLES]

    vocab = {}
    df = defaultdict(int)
    for grams in texts:
        seen = set()
        for g in grams:
            if g not in vocab:
                vocab[g] = len(vocab)
            if g not in seen:
                seen.add(g)
                df[g] += 1

    idf = _token_idf(vocab, df, len(texts))
    n_feats = len(vocab)

    # 每类意图的文档-词频矩阵行号
    by_intent = defaultdict(list)
    for i, intent in enumerate(intents):
        by_intent[intent].append(i)

    # 每类质心 = 该意图所有文档 tf-idf 向量的平均
    labels = sorted(by_intent.keys())
    centroids = np.zeros((len(labels), n_feats), dtype=float)
    for row, intent in enumerate(labels):
        matrix = np.zeros((len(by_intent[intent]), n_feats), dtype=float)
        for k, doc_idx in enumerate(by_intent[intent]):
            for tok in texts[doc_idx]:
                matrix[k, vocab[tok]] += idf[tok]
        centroids[row] = matrix.mean(axis=0)

    return vocab, idf, labels, centroids


def main():
    vocab, idf, labels, centroids = build()
    os.makedirs(_MODEL_DIR, exist_ok=True)
    np.savez(_PARAMS_PATH, centroids=centroids)
    with open(_META_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "vocab": vocab,
            "idf": idf,
            "labels": labels,
            "n_examples": len(INTENT_EXAMPLES),
            "n_features": len(vocab),
        }, f, ensure_ascii=False, indent=1)
    print(f"[train] 语料 {len(INTENT_EXAMPLES)} 条，意图 {len(labels)} 类，特征 {len(vocab)} 个")
    print(f"[train] 已保存 -> {_PARAMS_PATH}")
    print(f"[train] 已保存 -> {_META_PATH}")

    # 自检：对每类首个样例分类，验证意图识别正确
    from backend.ai_modules.intent_model import IntentModel, CONFIDENCE_THRESHOLD
    model = IntentModel(vocab, idf, labels, centroids)
    checked, bad = 0, 0
    for intent, text in INTENT_EXAMPLES:
        if checked >= 30:
            break
        top, score = model.top(text)
        checked += 1
        if top != intent:
            bad += 1
            print(f"[check] MISMATCH 期望={intent} 实际={top} ({score:.3f}) 问: {text}")
    print(f"[check] 自检 {checked} 条，错误 {bad} 条")


if __name__ == "__main__":
    main()
