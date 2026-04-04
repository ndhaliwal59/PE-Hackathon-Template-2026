import json
import secrets
import string
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request
from peewee import DoesNotExist, fn

from app.cache import get_short_entry, set_short_entry
from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.serializers import url_to_json

urls_bp = Blueprint("urls", __name__)

_ALPHANUM = string.ascii_letters + string.digits


def _allocate_short_code() -> str:
    for _ in range(50):
        code = "".join(secrets.choice(_ALPHANUM) for _ in range(6))
        if not Url.select().where(Url.short_code == code).exists():
            return code
    raise RuntimeError("could not allocate short code")


def _record_click_event(url: Url) -> None:
    try:
        next_eid = (Event.select(fn.MAX(Event.id)).scalar() or 0) + 1
        Event.create(
            id=next_eid,
            url=url.id,
            user=url.user_id,
            event_type="click",
            occurred_at=datetime.now(),
            details=json.dumps({"short_code": url.short_code}, separators=(",", ":")),
        )
    except Exception:
        pass


def _record_url_created_event(url: Url) -> None:
    next_eid = (Event.select(fn.MAX(Event.id)).scalar() or 0) + 1
    details = json.dumps(
        {"short_code": url.short_code, "original_url": url.original_url},
        separators=(",", ":"),
    )
    Event.create(
        id=next_eid,
        url=url,
        user=url.user_id,
        event_type="created",
        occurred_at=datetime.now(),
        details=details,
    )


@urls_bp.get("/urls")
def list_urls():
    q = Url.select().order_by(Url.id)
    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        q = q.where(Url.user_id == user_id)
    is_active = request.args.get("is_active")
    if is_active is not None:
        q = q.where(Url.is_active == (is_active.lower() in ("true", "1", "yes")))
    return jsonify([url_to_json(u) for u in q])


@urls_bp.get("/urls/<int:url_id>")
def get_url(url_id: int):
    try:
        url = Url.get_by_id(url_id)
    except DoesNotExist:
        return jsonify(error="url not found"), 404
    return jsonify(url_to_json(url))


@urls_bp.post("/urls")
def create_url():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    original_url = data.get("original_url")
    title = data.get("title") or ""

    if user_id is None or original_url is None:
        return jsonify(error="user_id and original_url are required"), 400
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify(error="user_id must be an integer"), 400
    if not isinstance(original_url, str) or not original_url.strip():
        return jsonify(error="original_url must be a non-empty string"), 400

    try:
        User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404

    now = datetime.now()
    with db.atomic():
        next_id = (Url.select(fn.MAX(Url.id)).scalar() or 0) + 1
        short_code = _allocate_short_code()
        url = Url.create(
            id=next_id,
            user_id=user_id,
            short_code=short_code,
            original_url=original_url.strip(),
            title=title.strip() if isinstance(title, str) else "",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        _record_url_created_event(url)
    set_short_entry(
        short_code,
        original_url=url.original_url,
        is_active=url.is_active,
    )
    return jsonify(url_to_json(url)), 201


@urls_bp.put("/urls/<int:url_id>")
def update_url(url_id: int):
    try:
        url = Url.get_by_id(url_id)
    except DoesNotExist:
        return jsonify(error="url not found"), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"errors": {"_schema": "body must be a JSON object"}}), 422
    if "title" in data:
        t = data["title"]
        if not isinstance(t, str):
            return jsonify({"errors": {"title": "must be a string"}}), 422
        url.title = t.strip()
    if "is_active" in data:
        v = data["is_active"]
        if not isinstance(v, bool):
            return jsonify({"errors": {"is_active": "must be a boolean"}}), 422
        url.is_active = v
    url.updated_at = datetime.now()
    url.save()
    set_short_entry(
        url.short_code,
        original_url=url.original_url,
        is_active=url.is_active,
    )
    return jsonify(url_to_json(url))


@urls_bp.delete("/urls/<int:url_id>")
def delete_url(url_id: int):
    try:
        url = Url.get_by_id(url_id)
    except DoesNotExist:
        return jsonify(error="url not found"), 404
    url.delete_instance(recursive=True)
    return "", 204


@urls_bp.get("/urls/<short_code>/redirect")
def redirect_by_short_code(short_code: str):
    return resolve_short_code(short_code)


@urls_bp.get("/s/<short_code>")
def resolve_short_code(short_code: str):
    cache_state, cached = get_short_entry(short_code)
    if cache_state == "HIT" and cached is not None:
        if cached.get("missing"):
            resp = jsonify(error="short code not found")
            resp.status_code = 404
            resp.headers["X-Cache"] = "HIT"
            return resp
        if not cached["is_active"]:
            resp = jsonify(error="link is inactive")
            resp.status_code = 410
            resp.headers["X-Cache"] = "HIT"
            return resp
        try:
            url_obj = Url.get(Url.short_code == short_code)
            _record_click_event(url_obj)
        except DoesNotExist:
            pass
        resp = redirect(cached["original_url"], code=302)
        resp.headers["X-Cache"] = "HIT"
        return resp

    label = "MISS" if cache_state == "MISS" else "BYPASS"
    try:
        url = Url.get(Url.short_code == short_code)
    except DoesNotExist:
        set_short_entry(short_code, missing=True)
        resp = jsonify(error="short code not found")
        resp.status_code = 404
        resp.headers["X-Cache"] = label
        return resp
    if not url.is_active:
        set_short_entry(
            short_code,
            original_url=url.original_url,
            is_active=False,
        )
        resp = jsonify(error="link is inactive")
        resp.status_code = 410
        resp.headers["X-Cache"] = label
        return resp
    set_short_entry(
        short_code,
        original_url=url.original_url,
        is_active=True,
    )
    _record_click_event(url)
    resp = redirect(url.original_url, code=302)
    resp.headers["X-Cache"] = label
    return resp
