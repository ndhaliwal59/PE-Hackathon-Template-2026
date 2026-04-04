import secrets
import string
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request
from peewee import DoesNotExist, fn
from playhouse.shortcuts import model_to_dict

from app.cache import get_short_entry, set_short_entry
from app.models.url import Url
from app.models.user import User

urls_bp = Blueprint("urls", __name__)

_ALPHANUM = string.ascii_letters + string.digits


def _allocate_short_code() -> str:
    for _ in range(50):
        code = "".join(secrets.choice(_ALPHANUM) for _ in range(6))
        if not Url.select().where(Url.short_code == code).exists():
            return code
    raise RuntimeError("could not allocate short code")


@urls_bp.get("/urls")
def list_urls():
    q = Url.select().order_by(Url.id)
    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        q = q.where(Url.user_id == user_id)
    return jsonify([model_to_dict(u, recurse=False) for u in q])


@urls_bp.get("/urls/<int:url_id>")
def get_url(url_id: int):
    try:
        url = Url.get_by_id(url_id)
    except DoesNotExist:
        return jsonify(error="url not found"), 404
    return jsonify(model_to_dict(url, recurse=False))


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
    set_short_entry(
        short_code,
        original_url=url.original_url,
        is_active=url.is_active,
    )
    return jsonify(model_to_dict(url, recurse=False)), 201


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
    resp = redirect(url.original_url, code=302)
    resp.headers["X-Cache"] = label
    return resp
