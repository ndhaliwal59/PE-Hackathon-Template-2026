import csv
import io
from datetime import datetime

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, fn
from werkzeug.datastructures import FileStorage

from app.database import db
from app.models.url import Url
from app.models.user import User
from app.serializers import url_to_json, user_to_json

users_bp = Blueprint("users", __name__)

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_user_datetime(value: str) -> datetime:
    return datetime.strptime(value.strip(), _DATETIME_FORMAT)


def _parse_user_csv_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "username": row["username"].strip(),
        "email": row["email"].strip(),
        "created_at": _parse_user_datetime(row["created_at"]),
    }


def _validation_error(message: str, *, field: str | None = None) -> tuple[dict, int]:
    if field:
        body = {"errors": {field: message}}
    else:
        body = {"errors": {"_schema": message}}
    return body, 422


@users_bp.get("/users")
def list_users():
    q = User.select().order_by(User.id)
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    if page is not None or per_page is not None:
        page = page if page is not None and page > 0 else 1
        per_page = per_page if per_page is not None and per_page > 0 else 20
        total = q.count()
        offset = (page - 1) * per_page
        rows = list(q.offset(offset).limit(per_page))
        return jsonify(
            {
                "users": [user_to_json(u) for u in rows],
                "page": page,
                "per_page": per_page,
                "total": total,
            }
        )
    return jsonify([user_to_json(u) for u in q])


@users_bp.post("/users/bulk")
def bulk_import_users():
    file_storage: FileStorage | None = request.files.get("file")
    if file_storage is None or file_storage.filename == "":
        for key, fs in request.files.items():
            if fs and fs.filename:
                file_storage = fs
                break
    if file_storage is None or file_storage.filename == "":
        return jsonify(error="missing CSV file"), 400

    raw = file_storage.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify(error="file must be UTF-8 text"), 400

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = {h.strip() for h in (reader.fieldnames or []) if h and h.strip()}
    if not fieldnames or not {"username", "email", "created_at"}.issubset(fieldnames):
        return jsonify(error="CSV must include username, email, created_at columns"), 400

    rows_in: list[dict[str, str]] = list(reader)
    if not rows_in:
        return jsonify({"count": 0}), 200

    has_id = "id" in fieldnames
    prepared: list[dict[str, object]] = []
    with db.atomic():
        next_id = (User.select(fn.MAX(User.id)).scalar() or 0) + 1
        for row in rows_in:
            row = {k.strip(): (v or "").strip() if v else "" for k, v in row.items()}
            base = _parse_user_csv_row(row)
            if has_id and row.get("id"):
                base["id"] = int(row["id"])
            else:
                base["id"] = next_id
                next_id += 1
            prepared.append(base)
        User.insert_many(prepared).execute()

    return jsonify({"count": len(prepared)}), 200


def _validate_create_user_payload(data: object) -> tuple[dict[str, str] | None, tuple | None]:
    if not isinstance(data, dict):
        return None, _validation_error("body must be a JSON object")
    username = data.get("username")
    email = data.get("email")
    if not isinstance(username, str) or not username.strip():
        return None, _validation_error("username must be a non-empty string", field="username")
    if not isinstance(email, str) or not email.strip():
        return None, _validation_error("email must be a non-empty string", field="email")
    return {"username": username.strip(), "email": email.strip()}, None


@users_bp.post("/users")
def create_user():
    data = request.get_json(silent=True)
    valid, err = _validate_create_user_payload(data)
    if err:
        return jsonify(err[0]), err[1]
    assert valid is not None
    now = datetime.now()
    next_id = (User.select(fn.MAX(User.id)).scalar() or 0) + 1
    user = User.create(id=next_id, created_at=now, **valid)
    return jsonify(user_to_json(user)), 201


@users_bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404
    return jsonify(user_to_json(user))


@users_bp.put("/users/<int:user_id>")
def update_user(user_id: int):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"errors": {"_schema": "body must be a JSON object"}}), 422
    if "username" in data:
        u = data["username"]
        if not isinstance(u, str) or not u.strip():
            return jsonify({"errors": {"username": "must be a non-empty string"}}), 422
        user.username = u.strip()
    if "email" in data:
        e = data["email"]
        if not isinstance(e, str) or not e.strip():
            return jsonify({"errors": {"email": "must be a non-empty string"}}), 422
        user.email = e.strip()
    user.save()
    return jsonify(user_to_json(user))


@users_bp.get("/users/<int:user_id>/urls")
def list_user_urls(user_id: int):
    try:
        User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404
    urls = Url.select().where(Url.user_id == user_id).order_by(Url.id)
    return jsonify([url_to_json(u) for u in urls])
