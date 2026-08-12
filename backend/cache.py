"""进程内 TTL 缓存（线程安全）。写操作（POST）需调用 invalidate 主动失效。"""

import threading
import time

_cache = {}
_cache_ttl = {}
_cache_lock = threading.Lock()
_indices_gen = 0


def get(key):
    with _cache_lock:
        now = time.monotonic()
        if key in _cache and now - _cache_ttl.get(key, 0) < 300:
            return _cache[key]
    return None


def put(key, value):
    with _cache_lock:
        _cache[key] = value
        _cache_ttl[key] = time.monotonic()


def invalidate(key):
    global _indices_gen
    with _cache_lock:
        _cache.pop(key, None)
        _cache_ttl.pop(key, None)
        prefix = f"{key}:"
        for k in [k for k in _cache if k.startswith(prefix)]:
            _cache.pop(k, None)
            _cache_ttl.pop(k, None)
        if key == "indices":
            _indices_gen += 1


def generation(key):
    """返回某前缀缓存内容的代数，写操作 invalidate 时递增，用于防陈旧回填。"""
    with _cache_lock:
        return _indices_gen if key == "indices" else 0
