"""Rate limiting with Redis when available and an in-process fallback."""

from __future__ import annotations

import threading
import time

try:
    import redis  # type: ignore
except ImportError:  # tests/API may run without the redis client
    redis = None  # type: ignore

from backend.core.config import get_settings

_memory: dict[str, tuple[float, int]] = {}
_lock = threading.Lock()
_redis_client = None
_redis_checked = False


def _client():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if redis is None:
        _redis_client = None
        return None
    try:
        client = redis.Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


def reset_rate_limits() -> None:
    global _redis_checked, _redis_client
    with _lock:
        _memory.clear()
    _redis_checked = False
    _redis_client = None


def check_rate_limit(
    key: str, limit: int, window_seconds: int = 60
) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds)."""

    if limit <= 0:
        return True, 0

    client = _client()
    if client is not None:
        try:
            bucket = f"ratelimit:{key}:{int(time.time() // window_seconds)}"
            count = client.incr(bucket)
            if count == 1:
                client.expire(bucket, window_seconds)
            if count > limit:
                return False, window_seconds
            return True, 0
        except Exception:
            pass  # fall back to memory

    now = time.monotonic()
    with _lock:
        started, count = _memory.get(key, (now, 0))
        if now - started >= window_seconds:
            started, count = now, 0
        count += 1
        _memory[key] = (started, count)
        if count > limit:
            return False, max(1, int(window_seconds - (now - started)))
    return True, 0
