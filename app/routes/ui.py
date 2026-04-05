from pathlib import Path

from flask import Blueprint, send_from_directory

ui_bp = Blueprint("ui", __name__)

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@ui_bp.get("/ui")
@ui_bp.get("/ui/")
def serve_ui():
    return send_from_directory(_FRONTEND_DIR, "index.html")
