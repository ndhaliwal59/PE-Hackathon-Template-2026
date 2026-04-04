from flask import Blueprint, jsonify
import psutil


metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.get("/metrics")
def metrics():
    process = psutil.Process()
    return jsonify(
        {
            "cpu_percent": process.cpu_percent(interval=0.0),
            "memory_percent": process.memory_percent(),
        }
    )