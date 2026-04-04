"""Redis cache for short-code resolution. No-op when REDIS_URL is unset."""

from __future__ import annotations

import json
import os
from typing import Any

import redis

TTL_SHORT_OK = 600
TTL_SHORT_404 = 60

_client: redis.Redis | None = None
_client_initialized: bool = False


def _redis_client() -> redis.Redis | None:
    global _client, _client_initialized
    if _client_initialized:
        return _client
    _client_initialized = True
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return None
    _client = redis.Redis.from_url(
        url,
        decode_responses=True,
        max_connections=50,
    )
    return _client


def get_short_entry(short_code: str) -> tuple[str, dict[str, Any] | None]:
    """Return (X-Cache value, payload). Payload: {missing: True} or {original_url, is_active}."""
    r = _redis_client()
    if r is None:
        return "BYPASS", None
    try:
        raw = r.get(f"url:short:{short_code}")
        if raw is None:
            return "MISS", None
        obj = json.loads(raw)
        if obj.get("missing"):
            return "HIT", {"missing": True}
        return "HIT", {
            "original_url": obj["original_url"],
            "is_active": bool(obj.get("is_active", True)),
        }
    except (redis.RedisError, TypeError, ValueError, KeyError):
        return "BYPASS", None


def set_short_entry(
    short_code: str,
    *,
    missing: bool = False,
    original_url: str | None = None,
    is_active: bool = True,
) -> None:
    r = _redis_client()
    if r is None:
        return
    key = f"url:short:{short_code}"
    try:
        if missing:
            r.setex(key, TTL_SHORT_404, json.dumps({"missing": True}))
        else:
            if original_url is None:
                return
            r.setex(
                key,
                TTL_SHORT_OK,
                json.dumps({"original_url": original_url, "is_active": is_active}),
            )
    except (redis.RedisError, TypeError):
        pass
