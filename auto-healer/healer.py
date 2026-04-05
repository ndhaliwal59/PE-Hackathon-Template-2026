"""Auto-healer webhook server.

Receives Alertmanager webhook POSTs and dispatches remediation actions
based on the alert name. See docs/RUNBOOK.md for the manual equivalents.
"""

from __future__ import annotations

import logging
import time
from threading import Lock

from flask import Flask, jsonify, request
from pythonjsonlogger.json import JsonFormatter

from remediation import heal_service_down

app = Flask(__name__)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
app.logger.handlers.clear()
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.propagate = False

COOLDOWN_SECONDS = 60
_last_action: dict[str, float] = {}
_cooldown_lock = Lock()

HANDLERS: dict[str, callable] = {
    "ServiceDown": heal_service_down,
}


def _in_cooldown(alert_name: str) -> bool:
    with _cooldown_lock:
        last = _last_action.get(alert_name, 0)
        if time.monotonic() - last < COOLDOWN_SECONDS:
            return True
        _last_action[alert_name] = time.monotonic()
        return False


@app.post("/webhook")
def webhook():
    payload = request.get_json(silent=True)
    if not payload or "alerts" not in payload:
        return jsonify({"error": "invalid payload"}), 400

    results = []
    for alert in payload["alerts"]:
        status = alert.get("status", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "unknown")

        if status != "firing":
            app.logger.info(
                "alert resolved externally",
                extra={"alertname": alert_name, "status": status},
            )
            results.append({"alertname": alert_name, "action": "none", "reason": "not firing"})
            continue

        handler_fn = HANDLERS.get(alert_name)
        if handler_fn is None:
            app.logger.warning(
                "no handler for alert",
                extra={"alertname": alert_name},
            )
            results.append({"alertname": alert_name, "action": "none", "reason": "no handler"})
            continue

        if _in_cooldown(alert_name):
            app.logger.info(
                "skipping remediation (cooldown)",
                extra={"alertname": alert_name, "cooldown_seconds": COOLDOWN_SECONDS},
            )
            results.append({"alertname": alert_name, "action": "none", "reason": "cooldown"})
            continue

        app.logger.info("starting remediation", extra={"alertname": alert_name})
        try:
            detail = handler_fn()
            app.logger.info(
                "remediation completed",
                extra={"alertname": alert_name, "detail": detail},
            )
            results.append({"alertname": alert_name, "action": "remediated", "detail": detail})
        except Exception:
            app.logger.exception("remediation failed", extra={"alertname": alert_name})
            results.append({"alertname": alert_name, "action": "failed"})

    return jsonify({"results": results}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
