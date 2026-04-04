from types import SimpleNamespace

import pytest
from peewee import DoesNotExist

import app as app_module
import app.routes.urls as urls_routes
import app.routes.users as users_routes


class FakeQuery(list):
    def order_by(self, *args, **kwargs):
        return self

    def where(self, *args, **kwargs):
        return self


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(app_module, "init_db", lambda _app: None)
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_list_urls_returns_json(client, monkeypatch):
    fake_urls = [
        SimpleNamespace(
            id=1,
            user_id=2,
            short_code="abc123",
            original_url="https://example.com",
            title="Example",
            is_active=True,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
    ]
    monkeypatch.setattr(urls_routes.Url, "select", lambda: FakeQuery(fake_urls))
    monkeypatch.setattr(urls_routes, "model_to_dict", lambda obj, recurse=False: dict(obj.__dict__))

    response = client.get("/urls")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "user_id": 2,
            "short_code": "abc123",
            "original_url": "https://example.com",
            "title": "Example",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
    ]


def test_get_url_missing_returns_404(client, monkeypatch):
    monkeypatch.setattr(urls_routes.Url, "get_by_id", lambda url_id: (_ for _ in ()).throw(DoesNotExist()))

    response = client.get("/urls/99")

    assert response.status_code == 404
    assert response.get_json() == {"error": "url not found"}


def test_resolve_short_code_redirects_active_url(client, monkeypatch):
    monkeypatch.setattr(
        urls_routes.Url,
        "get",
        lambda *args, **kwargs: SimpleNamespace(original_url="https://example.com", is_active=True),
    )

    response = client.get("/s/abc123", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com"


def test_resolve_short_code_returns_410_when_inactive(client, monkeypatch):
    monkeypatch.setattr(
        urls_routes.Url,
        "get",
        lambda *args, **kwargs: SimpleNamespace(original_url="https://example.com", is_active=False),
    )

    response = client.get("/s/abc123")

    assert response.status_code == 410
    assert response.get_json() == {"error": "link is inactive"}


def test_list_users_returns_json(client, monkeypatch):
    fake_users = [
        SimpleNamespace(id=1, username="alpha", email="alpha@example.com", created_at="2026-01-01T00:00:00")
    ]
    monkeypatch.setattr(users_routes.User, "select", lambda: FakeQuery(fake_users))
    monkeypatch.setattr(users_routes, "model_to_dict", lambda obj, recurse=False: dict(obj.__dict__))

    response = client.get("/users")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "username": "alpha",
            "email": "alpha@example.com",
            "created_at": "2026-01-01T00:00:00",
        }
    ]


def test_get_user_missing_returns_404(client, monkeypatch):
    monkeypatch.setattr(users_routes.User, "get_by_id", lambda user_id: (_ for _ in ()).throw(DoesNotExist()))

    response = client.get("/users/99")

    assert response.status_code == 404
    assert response.get_json() == {"error": "user not found"}


def test_list_user_urls_returns_only_matching_urls(client, monkeypatch):
    monkeypatch.setattr(users_routes.User, "get_by_id", lambda user_id: SimpleNamespace(id=user_id))
    fake_urls = [SimpleNamespace(id=1, user_id=7, short_code="abc123")]
    monkeypatch.setattr(users_routes.Url, "select", lambda: FakeQuery(fake_urls))
    monkeypatch.setattr(users_routes, "model_to_dict", lambda obj, recurse=False: dict(obj.__dict__))

    response = client.get("/users/7/urls")

    assert response.status_code == 200
    assert response.get_json() == [{"id": 1, "user_id": 7, "short_code": "abc123"}]