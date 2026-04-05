from peewee import PostgresqlDatabase

import app.database as database_module


class FakeApp:
    def __init__(self):
        self.before_request_handlers = []
        self.teardown_handlers = []

    def before_request(self, func):
        self.before_request_handlers.append(func)
        return func

    def teardown_appcontext(self, func):
        self.teardown_handlers.append(func)
        return func


class FakeDB:
    def __init__(self):
        self.initialize_calls = []
        self.connect_calls = []
        self.closed = False

    def initialize(self, database):
        self.initialize_calls.append(database)

    def connect(self, reuse_if_open=True):
        self.connect_calls.append(reuse_if_open)

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True


def test_init_db_uses_environment_defaults_and_registers_hooks(monkeypatch):
    captured = {}

    fake_db = FakeDB()
    fake_database = object()

    def fake_postgresql_database(name, **kwargs):
        captured["name"] = name
        captured["kwargs"] = kwargs
        return fake_database

    monkeypatch.setenv("DATABASE_NAME", "testdb")
    monkeypatch.setenv("DATABASE_HOST", "dbhost")
    monkeypatch.setenv("DATABASE_PORT", "15432")
    monkeypatch.setenv("DATABASE_USER", "dbuser")
    monkeypatch.setenv("DATABASE_PASSWORD", "dbpass")
    monkeypatch.setattr(database_module, "PostgresqlDatabase", fake_postgresql_database)
    monkeypatch.setattr(database_module, "db", fake_db)

    app = FakeApp()
    database_module.init_db(app)

    assert captured["name"] == "testdb"
    assert captured["kwargs"] == {
        "host": "dbhost",
        "port": 15432,
        "user": "dbuser",
        "password": "dbpass",
    }
    assert fake_db.initialize_calls
    assert fake_db.initialize_calls[0] is fake_database
    assert len(app.before_request_handlers) == 1
    assert len(app.teardown_handlers) == 1

    app.before_request_handlers[0]()
    assert fake_db.connect_calls == [True]

    app.teardown_handlers[0](None)
    assert fake_db.closed is True
