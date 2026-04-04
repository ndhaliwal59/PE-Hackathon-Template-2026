from contextlib import nullcontext
from types import SimpleNamespace

import app.seed as seed_module


def test_load_users_transforms_ids_and_batches(tmp_path, monkeypatch):
    seed_dir = tmp_path / "data"
    seed_dir.mkdir()
    (seed_dir / "users.csv").write_text(
        "id,username,email,created_at\n1,alpha,alpha@example.com,2026-01-01 00:00:00\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(seed_module, "DATA_DIR", seed_dir)
    monkeypatch.setattr(seed_module, "db", SimpleNamespace(atomic=lambda: nullcontext()))

    captured_rows = []

    class InsertResult:
        def execute(self):
            return None

    monkeypatch.setattr(
        seed_module.User,
        "insert_many",
        lambda rows: captured_rows.extend(rows) or InsertResult(),
    )

    seed_module.load_users()

    assert captured_rows == [
        {
            "id": 1,
            "username": "alpha",
            "email": "alpha@example.com",
            "created_at": "2026-01-01 00:00:00",
        }
    ]


def test_load_csv_seed_skips_when_population_exists(monkeypatch):
    monkeypatch.setattr(seed_module.User, "select", lambda: type("Q", (), {"count": lambda self=None: 1})())

    called = {"users": False, "urls": False, "events": False}
    monkeypatch.setattr(seed_module, "load_users", lambda: called.__setitem__("users", True))
    monkeypatch.setattr(seed_module, "load_urls", lambda: called.__setitem__("urls", True))
    monkeypatch.setattr(seed_module, "load_events", lambda: called.__setitem__("events", True))

    seed_module.load_csv_seed(skip_if_populated=True)

    assert called == {"users": False, "urls": False, "events": False}