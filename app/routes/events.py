from flask import Blueprint, jsonify

from app.models.event import Event
from app.serializers import event_to_json

events_bp = Blueprint("events", __name__)


@events_bp.get("/events")
def list_events():
    events = Event.select().order_by(Event.id)
    return jsonify([event_to_json(e) for e in events])
