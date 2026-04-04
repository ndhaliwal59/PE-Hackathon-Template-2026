from dotenv import load_dotenv
from flask import Flask, jsonify

from app.database import init_db
from app.routes import register_routes


def health_payload():
    return {"status": "ok"}


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(health_payload())

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "internal server error"}), 500

    return app
