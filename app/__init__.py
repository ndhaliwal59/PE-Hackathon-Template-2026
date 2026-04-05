import logging
from time import perf_counter

import psutil
from dotenv import load_dotenv
from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pythonjsonlogger.json import JsonFormatter

from app.database import db, init_db
from app.routes import register_routes

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "status_group"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["method"],
)
app_process_cpu_percent = Gauge(
    "app_process_cpu_percent",
    "Process CPU percent (psutil.Process, same semantics as JSON /metrics)",
)
app_process_memory_percent = Gauge(
    "app_process_memory_percent",
    "Process RSS memory as percentage of total system memory (psutil.Process)",
)
app_process_memory_rss_bytes = Gauge(
    "app_process_memory_rss_bytes",
    "Process RSS in bytes (psutil.Process)",
)


def health_payload():
    return {"status": "ok"}


def request_log_level(status_code):
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


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
        app.logger.log(
            request_log_level(response.status_code),
            "request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        if request.path != "/prometheus/metrics":
            status_group = f"{response.status_code // 100}xx"
            http_requests_total.labels(
                method=request.method, status_group=status_group
            ).inc()
            if started_at is not None:
                http_request_duration_seconds.labels(
                    method=request.method
                ).observe(perf_counter() - started_at)
        return response

    @app.get("/prometheus/metrics")
    def prometheus_metrics():
        proc = psutil.Process()
        app_process_cpu_percent.set(proc.cpu_percent(interval=0.1))
        mem = proc.memory_info()
        app_process_memory_rss_bytes.set(mem.rss)
        app_process_memory_percent.set(proc.memory_percent())
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

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
