"""JSON-friendly representations for API responses (hackathon-compatible field names)."""

from __future__ import annotations

import json
from typing import Any

from app.models.event import Event
from app.models.url import Url
from app.models.user import User

_DT_FMT = "%Y-%m-%dT%H:%M:%S"


def _dt(value: Any) -> str:
    if value is None:
        return ""
    return value.strftime(_DT_FMT)


def user_to_json(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": _dt(user.created_at),
    }


def url_to_json(url: Url) -> dict[str, Any]:
    return {
        "id": url.id,
        "user_id": url.user_id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "created_at": _dt(url.created_at),
        "updated_at": _dt(url.updated_at),
    }


def event_to_json(event: Event) -> dict[str, Any]:
    raw = event.details or ""
    try:
        details: Any = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        details = {}
    return {
        "id": event.id,
        "url_id": event.url_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": _dt(event.occurred_at),
        "details": details,
    }
