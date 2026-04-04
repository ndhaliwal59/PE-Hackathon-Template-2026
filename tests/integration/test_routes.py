import io
import json

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
    assert response.get_json() == {"status": "ok"}


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
    assert data[0]["user_id"] == u1.id


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
    assert body["user_id"] == u.id
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
    assert data[0]["user_id"] == u1.id


def test_method_not_allowed_returns_405(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert response.get_json() == {"error": "method not allowed"}


def test_internal_error_returns_500(client, monkeypatch):
    import app.routes.urls as urls_routes
    def fake_select(*args, **kwargs):
        raise RuntimeError("simulated crash")
    
    monkeypatch.setattr(urls_routes.Url, "select", fake_select)
    response = client.get("/urls")
    assert response.status_code == 500
    assert response.get_json() == {"error": "internal server error"}


def test_unhandled_route_returns_404(client):
    response = client.get("/this_route_does_not_exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_malformed_json_returns_400(client):
    response = client.post("/urls", data='{"bad": "json', content_type="application/json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "user_id and original_url are required"}


def test_bulk_users_csv_returns_count(client):
    csv_content = (
        "username,email,created_at\n"
        "bulk_a,bulk_a@example.com,2026-01-01 00:00:00\n"
        "bulk_b,bulk_b@example.com,2026-01-02 00:00:00\n"
    )
    data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "users.csv")}
    response = client.post("/users/bulk", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.get_json() == {"count": 2}


def test_post_user_returns_201(client):
    response = client.post(
        "/users",
        json={"username": "newu", "email": "newu@example.com"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["username"] == "newu"
    assert body["email"] == "newu@example.com"
    assert "id" in body
    assert "created_at" in body


def test_post_user_invalid_username_type_returns_422(client):
    response = client.post(
        "/users",
        json={"username": 12345, "email": "x@example.com"},
    )
    assert response.status_code == 422
    assert "errors" in response.get_json()


def test_put_user_updates_username(client):
    u = User.create(username="old", email="old@example.com", created_at=datetime.now(timezone.utc))
    response = client.put(f"/users/{u.id}", json={"username": "newname"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["username"] == "newname"
    assert body["email"] == "old@example.com"


def test_put_user_missing_returns_404(client):
    response = client.put("/users/99999", json={"username": "nope"})
    assert response.status_code == 404


def test_list_users_with_pagination_envelope(client):
    User.create(username="p1", email="p1@example.com", created_at=datetime(2026, 1, 1))
    User.create(username="p2", email="p2@example.com", created_at=datetime(2026, 1, 2))

    response = client.get("/users?page=1&per_page=1")
    assert response.status_code == 200
    data = response.get_json()
    assert "users" in data
    assert len(data["users"]) == 1
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["per_page"] == 1


def test_put_url_updates_title_and_active(client):
    u = User.create(username="u", email="u@example.com", created_at=datetime.now(timezone.utc))
    url_obj = Url.create(
        user=u,
        short_code="putcode",
        original_url="https://example.com/x",
        title="Old",
        is_active=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    response = client.put(
        f"/urls/{url_obj.id}",
        json={"title": "Updated Title", "is_active": False},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "Updated Title"
    assert body["is_active"] is False
    assert body["short_code"] == "putcode"


def test_put_url_missing_returns_404(client):
    response = client.put("/urls/99999", json={"title": "x"})
    assert response.status_code == 404


def test_list_events_returns_array(client):
    u = User.create(username="eu", email="eu@example.com", created_at=datetime.now(timezone.utc))
    url_obj = Url.create(
        user=u,
        short_code="evc",
        original_url="https://example.com/e",
        title="E",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    Event.create(
        id=1,
        url=url_obj,
        user=u,
        event_type="created",
        occurred_at=datetime(2026, 1, 1, 12, 0, 0),
        details=json.dumps({"short_code": "evc", "original_url": "https://example.com/e"}),
    )
    response = client.get("/events")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["url_id"] == url_obj.id
    assert data[0]["user_id"] == u.id
    assert data[0]["event_type"] == "created"
    assert data[0]["details"]["short_code"] == "evc"


def test_create_url_inserts_created_event(client):
    u = User.create(username="evu", email="evu@example.com", created_at=datetime.now(timezone.utc))
    response = client.post(
        "/urls",
        json={"user_id": u.id, "original_url": "https://example.com/newev", "title": "T"},
    )
    assert response.status_code == 201
    url_id = response.get_json()["id"]
    ev = Event.get(Event.url_id == url_id)
    assert ev.event_type == "created"
    details = json.loads(ev.details)
    assert details["original_url"] == "https://example.com/newev"
