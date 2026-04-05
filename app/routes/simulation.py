"""Incident drill routes. Registered only when INCIDENT_SIMULATION_ENABLED is set.

Do not enable in production-facing deployments.
"""

from __future__ import annotations

import os
import threading

from flask import Blueprint, jsonify

simulation_bp = Blueprint("simulation", __name__, url_prefix="/simulation")

_burner_lock = threading.Lock()
_burner_stop = threading.Event()
_burner_thread: threading.Thread | None = None


def simulation_enabled() -> bool:
    v = os.environ.get("INCIDENT_SIMULATION_ENABLED", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _cpu_burn_loop() -> None:
    while not _burner_stop.is_set():
        for _ in range(2000):
            if _burner_stop.is_set():
                return


@simulation_bp.get("/http-500")
def simulated_http_500():
    return jsonify({"error": "simulated server error"}), 500


@simulation_bp.post("/cpu-burn/start")
def cpu_burn_start():
    global _burner_thread
    with _burner_lock:
        if _burner_thread is None or not _burner_thread.is_alive():
            _burner_stop.clear()
            _burner_thread = threading.Thread(target=_cpu_burn_loop, daemon=True)
            _burner_thread.start()
    return jsonify({"status": "cpu burn started"}), 200


@simulation_bp.post("/cpu-burn/stop")
def cpu_burn_stop():
    _burner_stop.set()
    return jsonify({"status": "cpu burn stop requested"}), 200
