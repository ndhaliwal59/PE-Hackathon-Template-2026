"""Load seed CSV files from app/data/."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from peewee import chunked

from app.database import db
from app.models import Event, Url, User

DATA_DIR = Path(__file__).resolve().parent / "data"
BATCH_SIZE = 100
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FORMAT)


def _normalize_boolean(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


def _normalize_user_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "email": row["email"],
        "created_at": _parse_datetime(row["created_at"]),
    }


def _normalize_url_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "short_code": row["short_code"],
        "original_url": row["original_url"],
        "title": row["title"] or None,
        "is_active": _normalize_boolean(row["is_active"]),
        "created_at": _parse_datetime(row["created_at"]),
        "updated_at": _parse_datetime(row["updated_at"]),
    }


def _normalize_event_details(raw_details: str | None) -> str | None:
    if not raw_details:
        return None
    return json.dumps(json.loads(raw_details), separators=(",", ":"))


def _normalize_event_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "id": int(row["id"]),
        "url_id": int(row["url_id"]),
        "user_id": int(row["user_id"]),
        "event_type": row["event_type"],
        "occurred_at": _parse_datetime(row["timestamp"]),
        "details": _normalize_event_details(row.get("details")),
    }


def _read_rows(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_users() -> None:
    rows = _read_rows("users.csv")
    rows = [_normalize_user_row(row) for row in rows]
    with db.atomic():
        for batch in chunked(rows, BATCH_SIZE):
            User.insert_many(batch).execute()


def load_urls() -> None:
    rows = _read_rows("urls.csv")
    rows = [_normalize_url_row(row) for row in rows]
    with db.atomic():
        for batch in chunked(rows, BATCH_SIZE):
            Url.insert_many(batch).execute()


def load_events() -> None:
    rows = _read_rows("events.csv")
    normalized = [_normalize_event_row(row) for row in rows]
    with db.atomic():
        for batch in chunked(normalized, BATCH_SIZE):
            Event.insert_many(batch).execute()


def load_csv_seed(*, skip_if_populated: bool = True) -> None:
    """Create rows from CSVs in dependency order (users → urls → events)."""
    if skip_if_populated and User.select().count() > 0:
        return
    load_users()
    load_urls()
    load_events()
