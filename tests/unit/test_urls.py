import app.routes.urls as urls_module


def test_allocate_short_code_skips_taken_code(monkeypatch):
    characters = iter(list("ABCDEF") + list("GHIJKL"))
    attempts = iter([True, False])

    monkeypatch.setattr(urls_module.secrets, "choice", lambda alphabet: next(characters))

    class FakeExistsQuery:
        def exists(self):
            return next(attempts)

    class FakeSelectQuery:
        def where(self, *args, **kwargs):
            return FakeExistsQuery()

    monkeypatch.setattr(urls_module.Url, "select", lambda: FakeSelectQuery())

    assert urls_module._allocate_short_code() == "GHIJKL"