"""Load seed CSV files from app/data/."""

from __future__ import annotations

import csv
from pathlib import Path

from peewee import chunked

from app.database import db
from app.models import Event, Url, User

DATA_DIR = Path(__file__).resolve().parent / "data"
BATCH_SIZE = 100


def _read_rows(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_users() -> None:
    rows = _read_rows("users.csv")
    for row in rows:
        row["id"] = int(row["id"])
    with db.atomic():
        for batch in chunked(rows, BATCH_SIZE):
            User.insert_many(batch).execute()


def load_urls() -> None:
    rows = _read_rows("urls.csv")
    for row in rows:
        row["id"] = int(row["id"])
        row["user_id"] = int(row["user_id"])
        row["is_active"] = row["is_active"].strip().lower() in ("true", "1", "yes")
    with db.atomic():
        for batch in chunked(rows, BATCH_SIZE):
            Url.insert_many(batch).execute()


def load_events() -> None:
    rows = _read_rows("events.csv")
    normalized: list[dict] = []
    for row in rows:
        normalized.append(
            {
                "id": int(row["id"]),
                "url_id": int(row["url_id"]),
                "user_id": int(row["user_id"]),
                "event_type": row["event_type"],
                "occurred_at": row["timestamp"],
                "details": row["details"],
            }
        )
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
