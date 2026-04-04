import app as app_module


def test_health_payload_returns_ok_json():
    assert app_module.health_payload() == {"status": "ok"}