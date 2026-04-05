import app.cache as cache_module


class FakeRedisClient:
    def __init__(self):
        self.values = {}
        self.set_calls = []

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.set_calls.append((key, ttl, value))
        self.values[key] = value


def reset_cache_state(monkeypatch):
    monkeypatch.setattr(cache_module, "_client_initialized", False)
    monkeypatch.setattr(cache_module, "_client", None)


def test_get_short_entry_bypasses_when_redis_url_missing(monkeypatch):
    reset_cache_state(monkeypatch)
    monkeypatch.delenv("REDIS_URL", raising=False)

    cache_state, payload = cache_module.get_short_entry("abc123")

    assert cache_state == "BYPASS"
    assert payload is None


def test_get_short_entry_returns_miss_and_hit(monkeypatch):
    reset_cache_state(monkeypatch)
    fake_client = FakeRedisClient()
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr(cache_module.redis.Redis, "from_url", lambda *args, **kwargs: fake_client)

    cache_state, payload = cache_module.get_short_entry("abc123")
    assert cache_state == "MISS"
    assert payload is None

    fake_client.values["url:short:abc123"] = '{"original_url":"https://example.com","is_active":true}'
    cache_state, payload = cache_module.get_short_entry("abc123")
    assert cache_state == "HIT"
    assert payload == {"original_url": "https://example.com", "is_active": True}


def test_get_short_entry_returns_missing_hit(monkeypatch):
    reset_cache_state(monkeypatch)
    fake_client = FakeRedisClient()
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr(cache_module.redis.Redis, "from_url", lambda *args, **kwargs: fake_client)
    fake_client.values["url:short:missing"] = '{"missing":true}'

    cache_state, payload = cache_module.get_short_entry("missing")

    assert cache_state == "HIT"
    assert payload == {"missing": True}


def test_get_short_entry_bypasses_on_redis_error(monkeypatch):
    reset_cache_state(monkeypatch)

    class ErrorClient(FakeRedisClient):
        def get(self, key):
            raise cache_module.redis.RedisError("boom")

    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr(cache_module.redis.Redis, "from_url", lambda *args, **kwargs: ErrorClient())

    cache_state, payload = cache_module.get_short_entry("abc123")

    assert cache_state == "BYPASS"
    assert payload is None


def test_set_short_entry_writes_expected_payloads(monkeypatch):
    reset_cache_state(monkeypatch)
    fake_client = FakeRedisClient()
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr(cache_module.redis.Redis, "from_url", lambda *args, **kwargs: fake_client)

    cache_module.set_short_entry("abc123", missing=True)
    cache_module.set_short_entry("def456", original_url="https://example.com", is_active=False)
    cache_module.set_short_entry("skipme")

    assert fake_client.set_calls[0][0] == "url:short:abc123"
    assert fake_client.set_calls[1][0] == "url:short:def456"
    assert len(fake_client.set_calls) == 2


def test_set_short_entry_bypasses_on_redis_error(monkeypatch):
    reset_cache_state(monkeypatch)

    class ErrorClient(FakeRedisClient):
        def setex(self, key, ttl, value):
            raise cache_module.redis.RedisError("boom")

    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr(cache_module.redis.Redis, "from_url", lambda *args, **kwargs: ErrorClient())

    cache_module.set_short_entry("abc123", original_url="https://example.com")
