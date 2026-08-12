"""本地小体量 LLM 接入层（Qwen2.5-0.5B-Instruct GGUF via llama-cpp-python）。

设计要点：
- 懒加载单例：首次使用才加载模型，避免阻塞后端启动；加载失败不影响整体。
- 流式生成：generate_stream 逐 token yield，供 SSE 推流使用。
- 自动下载：模型缺失时尝试从 hf-mirror.com 下载（可被环境变量 LLM_MODEL_URL 覆盖）。
- 降级路径：模型不可用时 is_available()==False，调用方回落到原规则实现。
- 纯本地推理：不联网、不上传任何数据。
- 串行推理：generate/generate_stream 全程持有进程级 _gen_lock，保证同一 Llama 实例
  不会被并发调用。llama.cpp 单实例并发推理会触发 GGML_ASSERT 直接 abort 整个进程
  （曾导致后端整体崩溃、登录全部失败），串行化可彻底规避。

环境变量：
  LLM_MODEL_URL   覆盖模型下载地址（默认 hf-mirror 官方镜像）
  LLM_MODEL_FILE  覆盖本地模型文件名（默认 qwen2.5-0.5b-instruct-q4_k_m.gguf）
  LLM_N_THREADS   覆盖推理线程数（默认 8）
"""

import os
import threading
import urllib.request

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
_DEFAULT_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
_MODEL_PATH = os.path.join(_MODELS_DIR, os.environ.get("LLM_MODEL_FILE", _DEFAULT_FILE))
_DEFAULT_URL = (
    "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

_lock = threading.Lock()
_instance = None
_load_error = None
_gen_lock = threading.Lock()


def model_path():
    return _MODEL_PATH


def model_file_exists():
    return os.path.exists(_MODEL_PATH) and os.path.getsize(_MODEL_PATH) > 1_000_000


def download_model(force=False):
    """下载模型权重到 models/；已存在且非 force 时跳过。返回路径或抛异常。

    采用临时文件 + 完成后再改名：避免下载中断留下超大残缺文件，
    被 model_file_exists() 的 >1MB 大小检查误判为「模型已存在」。
    """
    os.makedirs(_MODELS_DIR, exist_ok=True)
    if model_file_exists() and not force:
        return _MODEL_PATH
    url = os.environ.get("LLM_MODEL_URL", _DEFAULT_URL)
    tmp = _MODEL_PATH + ".part"
    if os.path.exists(tmp):
        os.remove(tmp)  # 清理上次中断的残缺临时文件
    print(f"[llm] downloading model from {url} ...", flush=True)
    urllib.request.urlretrieve(url, tmp)  # noqa: S310  # 仅允许用户显式配置的地址
    os.replace(tmp, _MODEL_PATH)
    print("[llm] model downloaded.", flush=True)
    return _MODEL_PATH


def _build():
    from llama_cpp import Llama

    threads = int(os.environ.get("LLM_N_THREADS", "8"))
    return Llama(
        model_path=_MODEL_PATH,
        n_ctx=2048,
        n_threads=threads,
        n_batch=threads * 2,
        verbose=False,
    )


def get_llm():
    """懒加载单例。返回 Llama 实例；不可用时抛 RuntimeError。"""
    global _instance, _load_error
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is not None:
            return _instance
        if _load_error is not None:
            raise RuntimeError(_load_error)
        try:
            if not model_file_exists():
                try:
                    download_model()
                except Exception as e:  # noqa: BLE001
                    _load_error = f"模型下载失败：{e}"
                    raise RuntimeError(_load_error)
            _instance = _build()
        except RuntimeError:
            raise
        except Exception as e:  # noqa: BLE001
            _load_error = f"模型加载失败：{e}"
            raise RuntimeError(_load_error)
        return _instance


def is_available():
    """模型是否可用（尝试加载；不抛异常）。"""
    try:
        get_llm()
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- 生成接口

_SYSTEM_DEFAULT = (
    "你是一名友善的中学校园 AI 助手，回复简洁、真诚、符合中学生场景，"
    "使用简体中文，不要编造数据，只基于提供的事实作答。"
)


def _msgs(user, system=None, history=None):
    msgs = []
    if system or _SYSTEM_DEFAULT:
        msgs.append({"role": "system", "content": system or _SYSTEM_DEFAULT})
    for h in history or []:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
            msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": user})
    return msgs


def generate(user, system=None, history=None, max_tokens=300, temperature=0.5,
             stop=None, json_mode=False):
    """同步生成完整回复文本。"""
    llm = get_llm()
    kwargs = dict(messages=_msgs(user, system, history), max_tokens=max_tokens,
                  temperature=temperature, stream=False)
    if stop:
        kwargs["stop"] = stop
    with _gen_lock:
        resp = llm.create_chat_completion(**kwargs)
    text = resp["choices"][0]["message"]["content"] or ""
    if json_mode:
        text = _extract_json(text)
    return text


def generate_stream(user, system=None, history=None, max_tokens=300, temperature=0.5,
                    stop=None):
    """流式生成：yield 每个 token 文本。异常向上抛。"""
    llm = get_llm()
    kwargs = dict(messages=_msgs(user, system, history), max_tokens=max_tokens,
                  temperature=temperature, stream=True)
    if stop:
        kwargs["stop"] = stop
    with _gen_lock:
        stream = llm.create_chat_completion(**kwargs)
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            tok = delta.get("content")
            if tok:
                yield tok


def _extract_json(text):
    """从模型输出中提取 JSON 对象（容忍 markdown 围栏与前后缀噪音）。"""
    import re
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        return m.group(0)
    return t


# ---------------------------------------------------------------- 预热

def warmup():
    """后台线程预热模型，避免首个请求卡顿。失败静默。"""
    def _w():
        try:
            get_llm()
            print("[llm] warmup done", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[llm] warmup failed: {e}", flush=True)
    t = threading.Thread(target=_w, daemon=True)
    t.start()
