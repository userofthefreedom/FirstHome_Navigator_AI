from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

from django.core.cache import cache


T = TypeVar("T")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def get_or_set_locked(key: str, builder: Callable[[], T], *, timeout: int) -> T:
    cached = cache.get(key)
    if cached is not None:
        return cached

    lock = _lock_for_key(key)
    with lock:
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = builder()
        cache.set(key, value, timeout=timeout)
        return value


def clear_firsthome_cache() -> None:
    cache.clear()


def _lock_for_key(key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock
