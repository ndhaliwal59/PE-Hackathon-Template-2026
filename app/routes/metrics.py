from flask import Blueprint, jsonify
import psutil


metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.get("/metrics")
def metrics():
    process = psutil.Process()
    system_memory = psutil.virtual_memory()

    return jsonify(
        {
            "cpu_percent": process.cpu_percent(interval=0.0),
            "memory_percent": process.memory_percent(),
            "system_memory": {
                "total_bytes": system_memory.total,
                "used_bytes": system_memory.used,
                "percent": system_memory.percent,
            },
        }
    )