import logging
from time import perf_counter

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from pythonjsonlogger.json import JsonFormatter

from app.database import db, init_db
from app.routes import register_routes


def health_payload():
    return {"status": "ok"}


def configure_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def create_app():
    load_dotenv()

    app = Flask(__name__)

    configure_logging(app)
    init_db(app)

    from app.models import Event, Url, User  # noqa: F401

    with app.app_context():
        db.connect(reuse_if_open=True)
        db.create_tables([User, Url, Event], safe=True)
        if not db.is_closed():
            db.close()

    register_routes(app)

    @app.before_request
    def _start_request_timer():
        g.request_started_at = perf_counter()

    @app.after_request
    def _log_request(response):
        started_at = getattr(g, "request_started_at", None)
        duration_ms = (
            round((perf_counter() - started_at) * 1000, 2)
            if started_at is not None
            else None
        )
        app.logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.route("/health")
    def health():
        return jsonify(health_payload())

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({"error": e.name.lower()}), e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception("Unhandled exception occurred")
        return jsonify({"error": "internal server error"}), 500

    return app
