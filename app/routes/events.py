import json
from datetime import datetime

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, fn

from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.serializers import event_to_json

events_bp = Blueprint("events", __name__)


@events_bp.get("/events")
def list_events():
    q = Event.select().order_by(Event.id)
    url_id = request.args.get("url_id", type=int)
    if url_id is not None:
        q = q.where(Event.url_id == url_id)
    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        q = q.where(Event.user_id == user_id)
    event_type = request.args.get("event_type")
    if event_type is not None:
        q = q.where(Event.event_type == event_type)
    return jsonify([event_to_json(e) for e in q])


@events_bp.post("/events")
def create_event():
    data = request.get_json(silent=True) or {}
    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")

    if url_id is None or user_id is None or event_type is None:
        return jsonify(error="url_id, user_id, and event_type are required"), 400

    try:
        url_id = int(url_id)
    except (TypeError, ValueError):
        return jsonify(error="url_id must be an integer"), 400
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify(error="user_id must be an integer"), 400
    if not isinstance(event_type, str) or not event_type.strip():
        return jsonify(error="event_type must be a non-empty string"), 400

    try:
        Url.get_by_id(url_id)
    except DoesNotExist:
        return jsonify(error="url not found"), 404
    try:
        User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify(error="user not found"), 404

    details = data.get("details")
    if isinstance(details, dict):
        details = json.dumps(details, separators=(",", ":"))
    elif details is None:
        details = ""
    else:
        return jsonify(error="details must be a JSON object"), 400

    next_id = (Event.select(fn.MAX(Event.id)).scalar() or 0) + 1
    event = Event.create(
        id=next_id,
        url=url_id,
        user=user_id,
        event_type=event_type,
        occurred_at=datetime.now(),
        details=details,
    )
    return jsonify(event_to_json(event)), 201
