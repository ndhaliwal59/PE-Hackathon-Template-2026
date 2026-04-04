from datetime import datetime

import app.seed as seed_module


def test_normalize_user_row_parses_types():
    row = {
        "id": "1",
        "username": "alpha",
        "email": "alpha@example.com",
        "created_at": "2026-01-01 00:00:00",
    }

    assert seed_module._normalize_user_row(row) == {
        "id": 1,
        "username": "alpha",
        "email": "alpha@example.com",
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
    }


def test_normalize_url_row_parses_boolean_and_datetimes():
    row = {
        "id": "9",
        "user_id": "3",
        "short_code": "abc123",
        "original_url": "https://example.com",
        "title": "Example",
        "is_active": "True",
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-02 00:00:00",
    }

    assert seed_module._normalize_url_row(row) == {
        "id": 9,
        "user_id": 3,
        "short_code": "abc123",
        "original_url": "https://example.com",
        "title": "Example",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 2, 0, 0, 0),
    }


def test_normalize_event_row_parses_nested_json_and_datetime():
    row = {
        "id": "4",
        "url_id": "2",
        "user_id": "1",
        "event_type": "created",
        "timestamp": "2026-01-03 01:02:03",
        "details": '{"short_code": "abc123", "original_url": "https://example.com"}',
    }

    assert seed_module._normalize_event_row(row) == {
        "id": 4,
        "url_id": 2,
        "user_id": 1,
        "event_type": "created",
        "occurred_at": datetime(2026, 1, 3, 1, 2, 3),
        "details": '{"short_code":"abc123","original_url":"https://example.com"}',
    }