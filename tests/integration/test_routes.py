import pytest
from datetime import datetime, timezone
from peewee import SqliteDatabase

import app as app_module
from app.database import db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event


integration_db = SqliteDatabase("file:testdb?mode=memory&cache=shared", uri=True)

@pytest.fixture(autouse=True)
def setup_integration_db(monkeypatch):
    import sqlite3
    pin_conn = sqlite3.connect("file:testdb?mode=memory&cache=shared", uri=True)
    
    def test_init_db(app):
        db.initialize(integration_db)
        
        @app.before_request
        def _db_connect():
            integration_db.connect(reuse_if_open=True)

        @app.teardown_appcontext
        def _db_close(exc):
            if not integration_db.is_closed():
                integration_db.close()
                pass
                
    # Prevent create_app from initializing real DB by patching the imported reference in app/__init__.py
    monkeypatch.setattr("app.init_db", test_init_db)
    
    # Initialize peewee with test sqlite db
    db.initialize(integration_db)
    integration_db.connect(reuse_if_open=True)
    integration_db.create_tables([User, Url, Event])
    
    yield
    
    integration_db.drop_tables([User, Url, Event])
    integration_db.close()
    pin_conn.close()


@pytest.fixture()
def client():
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "broken"}


def test_list_urls_returns_json(client):
    u = User.create(username="testuser", email="test@example.com", created_at=datetime.now(timezone.utc))
    Url.create(
        user=u,
        short_code="abc123",
        original_url="https://example.com",
        title="Example",
        is_active=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )

    response = client.get("/urls")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["short_code"] == "abc123"
    assert data[0]["original_url"] == "https://example.com"
    assert data[0]["is_active"] is True


def test_list_urls_filters_by_user_id(client):
    u1 = User.create(username="user1", email="u1@example.com", created_at=datetime.now(timezone.utc))
    u2 = User.create(username="user2", email="u2@example.com", created_at=datetime.now(timezone.utc))
    Url.create(user=u1, short_code="code1", original_url="https://u1.com", title="U1", is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    Url.create(user=u2, short_code="code2", original_url="https://u2.com", title="U2", is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))

    response = client.get(f"/urls?user_id={u1.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["short_code"] == "code1"
    assert data[0]["user"] == u1.id


def test_get_url_missing_returns_404(client):
    response = client.get("/urls/99")

    assert response.status_code == 404
    assert response.get_json() == {"error": "url not found"}


def test_get_url_by_id_returns_one_resource(client):
    u = User.create(username="testuser", email="test@example.com", created_at=datetime.now(timezone.utc))
    url_obj = Url.create(
        user=u,
        short_code="xyz789",
        original_url="https://example.com/xyz",
        title="XYZ",
        is_active=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )

    response = client.get(f"/urls/{url_obj.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == url_obj.id
    assert data["short_code"] == "xyz789"
    assert data["title"] == "XYZ"


def test_create_url_with_valid_payload_returns_201(client):
    u = User.create(username="testuser", email="test@example.com", created_at=datetime.now(timezone.utc))

    payload = {
        "user_id": u.id,
        "original_url": "https://example.com/new",
        "title": "New URL",
    }

    response = client.post("/urls", json=payload)

    assert response.status_code == 201
    body = response.get_json()
    assert body["user"] == u.id
    assert body["original_url"] == "https://example.com/new"
    assert body["title"] == "New URL"
    assert body["is_active"] is True
    assert "short_code" in body
    
    # Verify the record exists in DB
    db_url = Url.get_by_id(body["id"])
    assert db_url.original_url == "https://example.com/new"


def test_create_url_with_missing_fields_returns_400(client):
    response = client.post("/urls", json={"user_id": 2})

    assert response.status_code == 400
    assert response.get_json() == {"error": "user_id and original_url are required"}


def test_create_url_with_non_integer_user_id_returns_400(client):
    response = client.post(
        "/urls",
        json={"user_id": "not-an-int", "original_url": "https://example.com"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "user_id must be an integer"}


def test_create_url_with_empty_original_url_returns_400(client):
    response = client.post(
        "/urls",
        json={"user_id": 2, "original_url": "   "},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "original_url must be a non-empty string"}


def test_create_url_when_user_missing_returns_404(client):
    response = client.post(
        "/urls",
        json={"user_id": 999, "original_url": "https://example.com"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "user not found"}


def test_resolve_short_code_redirects_active_url(client):
    u = User.create(username="testuser", email="test@example.com", created_at=datetime.now(timezone.utc))
    Url.create(
        user=u,
        short_code="redirectme",
        original_url="https://resolved.com",
        title="Resolve Me",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = client.get("/s/redirectme", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "https://resolved.com"


def test_resolve_short_code_missing_returns_404(client):
    response = client.get("/s/notfoundcode")

    assert response.status_code == 404
    assert response.get_json() == {"error": "short code not found"}


def test_resolve_short_code_returns_410_when_inactive(client):
    u = User.create(username="testuser", email="test@example.com", created_at=datetime.now(timezone.utc))
    Url.create(
        user=u,
        short_code="inactivecode",
        original_url="https://example.com",
        title="Inactive",
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = client.get("/s/inactivecode")

    assert response.status_code == 410
    assert response.get_json() == {"error": "link is inactive"}


def test_list_users_returns_json(client):
    User.create(username="alpha", email="alpha@example.com", created_at=datetime(2026, 1, 1))

    response = client.get("/users")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["username"] == "alpha"
    assert data[0]["email"] == "alpha@example.com"


def test_get_user_missing_returns_404(client):
    response = client.get("/users/99")

    assert response.status_code == 404
    assert response.get_json() == {"error": "user not found"}


def test_list_user_urls_returns_only_matching_urls(client):
    u1 = User.create(username="alpha", email="alpha@example.com", created_at=datetime.now(timezone.utc))
    u2 = User.create(username="beta", email="beta@example.com", created_at=datetime.now(timezone.utc))
    
    Url.create(
        user=u1, short_code="code1", original_url="https://u1.com", title="U1", 
        is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    Url.create(
        user=u2, short_code="code2", original_url="https://u2.com", title="U2", 
        is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )

    response = client.get(f"/users/{u1.id}/urls")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["short_code"] == "code1"
    assert data[0]["user"] == u1.id
